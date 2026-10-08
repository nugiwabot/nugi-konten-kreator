#!/usr/bin/env python3
"""Multi-provider discovery for Nugi Cloud Research.

Uses only the Python standard library. RSS/news snippets are discovery leads,
not verified evidence. Optional providers activate only when configured.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

USER_AGENT = "NugiContentResearch/1.1 (+https://github.com/nugiwabot/nugi-konten-kreator)"
TIMEOUT = 12
MAX_RESPONSE = 2_000_000


def request(url: str, headers: dict[str, str] | None = None) -> bytes:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/rss+xml, application/atom+xml, application/xml, text/xml"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError("response_too_large")
        return data


def get_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(request(url, headers).decode("utf-8", errors="replace"))


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def candidate(title: Any, url: Any, snippet: Any, source: str, published: Any = "") -> dict[str, Any] | None:
    title, url, snippet = clean(title), clean(url), clean(snippet)
    if not title or not url.startswith(("http://", "https://")):
        return None
    try:
        domain = urllib.parse.urlsplit(url).hostname or ""
    except ValueError:
        domain = ""
    return {
        "suggested_title": title[:500],
        "source_headline": title[:500],
        "source_url": url,
        "source_snippet": snippet[:3000],
        "primary_domain": domain.lower(),
        "origin_kind": source,
        "published_at": clean(published)[:120],
        "research_status": "DISCOVERY_LEAD",
        "evidence_status": "UNVERIFIED",
    }


def rss_items(url: str, source: str) -> list[dict[str, Any]]:
    root = ET.fromstring(request(url))
    found: list[dict[str, Any]] = []
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1].lower()
        if tag not in {"item", "entry"}:
            continue
        fields: dict[str, str] = {}
        for child in list(item):
            key = child.tag.rsplit("}", 1)[-1].lower()
            val = clean(" ".join(child.itertext()))
            if key not in fields and val:
                fields[key] = val
            if key == "link" and not val:
                href = next((v for k, v in child.attrib.items() if k.lower() == "href"), "")
                if href:
                    fields["link"] = href
        link = fields.get("link", "")
        if link and link.startswith("/"):
            link = urllib.parse.urljoin(url, link)
        row = candidate(fields.get("title"), link, fields.get("description") or fields.get("summary") or fields.get("content"), source, fields.get("pubdate") or fields.get("published") or fields.get("updated") or fields.get("date"))
        if row:
            found.append(row)
    return found


def query_url(base: str, params: dict[str, str]) -> str:
    return base + ("&" if "?" in base else "?") + urllib.parse.urlencode(params)


def google_news(query: str, language: str, country: str) -> list[dict[str, Any]]:
    gl = country.upper()
    hl = "id" if language.lower().startswith("id") else "en-US"
    ceid = f"{gl}:{'id' if gl == 'ID' else 'en'}"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": hl, "gl": gl, "ceid": ceid})
    return rss_items(url, "google_news_rss")


def gdelt(query: str) -> list[dict[str, Any]]:
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode({
        "query": query, "mode": "ArtList", "format": "json", "sort": "DateDesc", "maxrecords": "25"
    })
    data = get_json(url)
    return [row for item in data.get("articles", []) if (row := candidate(item.get("title"), item.get("url"), item.get("seendate", "") + " " + item.get("domain", ""), "gdelt", item.get("seendate")))]


def openalex(query: str) -> list[dict[str, Any]]:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search": query, "per-page": "15", "sort": "publication_date:desc"})
    data = get_json(url)
    rows = []
    for item in data.get("results", []):
        loc = item.get("primary_location") or {}
        source = loc.get("landing_page_url") or item.get("doi") or item.get("id")
        rows.append(candidate(item.get("title"), source, "OpenAlex work; DOI=" + str(item.get("doi") or "") + "; publication date=" + str(item.get("publication_date") or ""), "openalex", item.get("publication_date")))
    return [x for x in rows if x]


def crossref(query: str) -> list[dict[str, Any]]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query": query, "rows": "15", "sort": "published", "order": "desc"})
    data = get_json(url)
    rows = []
    for item in data.get("message", {}).get("items", []):
        title = (item.get("title") or [""])[0]
        doi = item.get("DOI")
        link = "https://doi.org/" + doi if doi else item.get("URL")
        dateparts = item.get("published", {}).get("date-parts", [[]])
        date = "-".join(str(x) for x in (dateparts[0] if dateparts else []))
        rows.append(candidate(title, link, "Crossref publication metadata; DOI=" + str(doi or ""), "crossref", date))
    return [x for x in rows if x]


def europe_pmc(query: str) -> list[dict[str, Any]]:
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({"query": query, "format": "json", "pageSize": "15", "sort": "FIRST_PDATE_D desc"})
    data = get_json(url)
    rows = []
    for item in data.get("resultList", {}).get("result", []):
        pmcid = item.get("pmcid")
        pmid = item.get("pmid")
        link = ("https://europepmc.org/articles/" + pmcid) if pmcid else (("https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/") if pmid else item.get("doi", ""))
        rows.append(candidate(item.get("title"), link, "Europe PMC metadata; abstract=" + str(item.get("abstractText") or "")[:1800], "europe_pmc", item.get("firstPublicationDate")))
    return [x for x in rows if x]


def searxng(query: str, base: str) -> list[dict[str, Any]]:
    base = base.rstrip("/")
    data = get_json(base + "/search?" + urllib.parse.urlencode({"q": query, "format": "json", "categories": "general,news"}))
    return [row for item in data.get("results", []) if (row := candidate(item.get("title"), item.get("url"), item.get("content"), "searxng", item.get("publishedDate")))]


def brave(query: str, key: str) -> list[dict[str, Any]]:
    url = "https://api.search.brave.com/res/v1/news/search?" + urllib.parse.urlencode({"q": query, "count": "20"})
    data = get_json(url, {"X-Subscription-Token": key})
    return [row for item in data.get("results", []) if (row := candidate(item.get("title"), item.get("url"), item.get("description"), "brave_news_api", item.get("age")))]


def tavily(query: str, key: str) -> list[dict[str, Any]]:
    data = json.loads(request("https://api.tavily.com/search", {"Content-Type": "application/json"})) if False else None
    payload = json.dumps({"api_key": key, "query": query, "topic": "news", "search_depth": "basic", "max_results": 10}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=payload, headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        data = json.loads(response.read(MAX_RESPONSE + 1).decode("utf-8", errors="replace"))
    return [row for item in data.get("results", []) if (row := candidate(item.get("title"), item.get("url"), item.get("content"), "tavily_api", item.get("published_date")))]


def exa(query: str, key: str) -> list[dict[str, Any]]:
    payload = json.dumps({"query": query, "type": "auto", "numResults": 10, "contents": {"text": {"maxCharacters": 1200}}}).encode()
    req = urllib.request.Request("https://api.exa.ai/search", data=payload, headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", "x-api-key": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        data = json.loads(response.read(MAX_RESPONSE + 1).decode("utf-8", errors="replace"))
    return [row for item in data.get("results", []) if (row := candidate(item.get("title"), item.get("url"), item.get("text") or item.get("summary"), "exa_api", item.get("publishedDate")))]


def mediacloud(query: str, key: str) -> list[dict[str, Any]]:
    url = "https://api.mediacloud.org/api/v2/stories_public/list?" + urllib.parse.urlencode({"q": query, "rows": "15"})
    data = get_json(url, {"Authorization": "Bearer " + key})
    items = data if isinstance(data, list) else data.get("stories", [])
    return [row for item in items if (row := candidate(item.get("title"), item.get("url"), item.get("description") or item.get("media_name"), "mediacloud", item.get("publish_date")))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", default="")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output", required=True)
    parser.add_argument("--language", default="id")
    parser.add_argument("--country", default="ID")
    args = parser.parse_args()
    queries = [q.strip() for q in args.queries.split(";") if q.strip()]
    if not queries:
        queries = [
            "artificial intelligence society",
            "human behavior culture history",
            "economy work cities migration",
            "technology environment education",
        ]
    queries = queries[:8]
    all_rows: list[dict[str, Any]] = []
    provider_status: list[dict[str, str]] = []

    def run_provider(name: str, fn: Any, query: str) -> None:
        try:
            rows = fn(query)
            all_rows.extend(rows)
            provider_status.append({"provider": name, "query": query, "status": "ok", "results": str(len(rows))})
        except Exception as exc:
            provider_status.append({"provider": name, "query": query, "status": "error", "error": type(exc).__name__ + ": " + str(exc)[:240]})
            print(f"[WARN] {name} failed for query {query!r}: {type(exc).__name__}: {exc}", file=sys.stderr)

    for query in queries:
        run_provider("google_news_rss", lambda q: google_news(q, args.language, args.country), query)
        run_provider("gdelt", gdelt, query)
        run_provider("openalex", openalex, query)
        run_provider("crossref", crossref, query)
        run_provider("europe_pmc", europe_pmc, query)
        if os.getenv("SEARXNG_BASE_URL", "").strip():
            run_provider("searxng", lambda q: searxng(q, os.environ["SEARXNG_BASE_URL"]), query)
        if os.getenv("BRAVE_SEARCH_API_KEY", "").strip():
            run_provider("brave_news_api", lambda q: brave(q, os.environ["BRAVE_SEARCH_API_KEY"]), query)
        if os.getenv("TAVILY_API_KEY", "").strip():
            run_provider("tavily_api", lambda q: tavily(q, os.environ["TAVILY_API_KEY"]), query)
        if os.getenv("EXA_API_KEY", "").strip():
            run_provider("exa_api", lambda q: exa(q, os.environ["EXA_API_KEY"]), query)
        if os.getenv("MEDIACLOUD_API_TOKEN", "").strip():
            run_provider("mediacloud", lambda q: mediacloud(q, os.environ["MEDIACLOUD_API_TOKEN"]), query)
    for feed in [x.strip() for x in os.getenv("EXTRA_RSS_FEEDS", "").split(";") if x.strip()]:
        run_provider("extra_rss_feed", lambda _q, feed=feed: rss_items(feed, "extra_rss_feed"), "configured feed")

    unique: dict[str, dict[str, Any]] = {}\n    for row in all_rows:
        key = re.sub(r"[?#].*$", "", row["source_url"]).rstrip("/").lower()
        if key and key not in unique:
            unique[key] = row
        elif key and len(row.get("source_snippet", "")) > len(unique[key].get("source_snippet", "")):
            unique[key]["source_snippet"] = row["source_snippet"]
    rows = list(unique.values())
    rows.sort(key=lambda x: (x["origin_kind"] in {"openalex", "crossref", "europe_pmc"}, x.get("published_at", "")), reverse=True)
    rows = rows[:max(1, min(args.count, 100))]
    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 1,
        "operation": "multi_source_discovery",
        "generated_at": generated,
        "research_executed": False,
        "providers": provider_status,
        "provider_summary": {
            name: sum(1 for item in provider_status if item["provider"] == name and item["status"] == "ok")
            for name in sorted({item["provider"] for item in provider_status})
        },
        "result": {"count_returned": len(rows), "signals_considered": len(all_rows), "candidates": rows},
        "notice": "Discovery metadata/snippets are leads, not verified evidence. Scholarly records are metadata/abstracts, not proof by themselves."
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# Nugi Multi-source Discovery", "", f"- Generated at (UTC): {generated}", f"- Unique candidates: {len(rows)}", f"- Raw signals: {len(all_rows)}", "", "> Search results and abstracts are discovery leads, not verified evidence.", "", "## Provider status", ""]
    for item in provider_status:
        md.append(f"- {item['provider']} — {item['query']}: {item['status']} ({item.get('results', item.get('error', ''))})")
    md += ["", "## Candidates", ""]
    for i, row in enumerate(rows, 1):
        md += [f"### {i}. {row['source_headline']}", "", f"- Provider: {row['origin_kind']}", f"- Published: {row.get('published_at') or 'unknown'}", f"- URL: {row['source_url']}", f"- Snippet: {row.get('source_snippet') or 'not provided'}", ""]
    output.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    print(f"Multi-source discovery completed: {len(rows)} unique results from {len(all_rows)} raw signals")
    print(f"JSON: {output}")
    print(f"Markdown: {output.with_suffix('.md')}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
