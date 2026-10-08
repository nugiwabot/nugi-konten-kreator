#!/usr/bin/env python3
"""Cloud research workbench: extract accessible article text with provenance.

This is a bounded convenience extraction step, not a paywall bypass or a fact
verification engine. Feed snippets are never mislabeled as full article text.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_BYTES = 1_500_000
MAX_TEXT_CHARS = 45_000
TIMEOUT = 12
USER_AGENT = "NugiContentResearch/1.0 (+https://github.com/nugiwabot/nugi-konten-kreator)"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "button"}


class ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.in_article = False
        self.article_depth = 0
        self.skip_depth = 0
        self.meta: dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name") or attrs_dict.get("itemprop")
            value = attrs_dict.get("content", "")
            if key and value:
                self.meta[key.lower()] = value[:2000]
        if tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            self.canonical = attrs_dict.get("href", "")
        if tag == "title":
            self.in_title = True
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in {"article", "main"}:
            self.in_article = True
            self.article_depth += 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"} and self.skip_depth == 0:
            self.parts.append("\n")
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in {"article", "main"} and self.article_depth:
            self.article_depth -= 1
            if self.article_depth == 0:
                self.in_article = False
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            self.parts.append("\n")
        if tag in self.stack:
            # Close to the nearest matching open tag; malformed HTML is common.
            idx = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:idx]

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self.skip_depth == 0:
            self.parts.append(text + " ")

    def text(self) -> str:
        raw = html.unescape(" ".join(self.parts))
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)[:MAX_TEXT_CHARS]


def safe_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def fetch_page(url: str) -> tuple[str, str, str]:
    if not safe_http_url(url):
        raise ValueError("invalid_or_unsafe_url")
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.5,*/*;q=0.1",
    })
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        final_url = response.geturl()
        if not safe_http_url(final_url):
            raise ValueError("unsafe_redirect_target")
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ValueError("unsupported_content_type:" + (content_type or "unknown"))
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("page_exceeds_size_limit")
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        source = body.decode(charset, errors="replace")
    except LookupError:
        source = body.decode("utf-8", errors="replace")
    parser = ArticleTextParser()
    parser.feed(source)
    text = parser.text()
    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or ( " ".join(parser.title_parts) )
    ).strip()
    published = (
        parser.meta.get("article:published_time")
        or parser.meta.get("datepublished")
        or parser.meta.get("date")
        or parser.meta.get("pubdate")
        or ""
    )
    if len(text) < 350:
        raise ValueError("insufficient_extractable_text")
    return title[:500], text, published[:120]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery-json", required=True)
    parser.add_argument("--output-dir", default="cloud-output/research")
    args = parser.parse_args()
    root = Path(args.output_dir)
    articles_dir = root / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(Path(args.discovery_json).read_text(encoding="utf-8"))
    candidates = payload.get("result", {}).get("candidates", [])
    generated_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    report: list[str] = [
        "# Nugi Cloud Research Report", "",
        f"- Generated at (UTC): {generated_at}",
        f"- Candidates received: {len(candidates)}",
        "- Scope: bounded HTML text extraction from discovered URLs; not a fact-checking verdict.",
        "",
        "> Extraction availability depends on each publisher. Paywalls, login pages, robots/access controls, PDFs, and unsupported pages may not yield full text. Do not treat failed or partial extraction as full article text.",
        "",
    ]
    for i, item in enumerate(candidates, start=1):
        title = str(item.get("suggested_title") or item.get("source_headline") or f"Candidate {i}")
        url = str(item.get("source_url") or "")
        record: dict[str, Any] = {
            "id": f"article-{i:03d}",
            "candidate_title": title,
            "source_headline": item.get("source_headline", ""),
            "source_url": url,
            "publisher_or_feed": item.get("source_names", []),
            "published_at_from_discovery": item.get("published_at", ""),
            "retrieved_at": generated_at,
            "epistemic_role": "discovery_only",
            "extraction_status": "NOT_ATTEMPTED",
            "extraction_method": "bounded_html_parser",
            "content_type": "unknown",
            "article_title": "",
            "article_published_at": "",
            "text_chars": 0,
            "text": "",
            "error": "",
        }
        if not url:
            record["extraction_status"] = "NO_SOURCE_URL"
            record["error"] = "No canonical source URL was supplied by discovery."
        else:
            try:
                article_title, text, published = fetch_page(url)
                record.update({
                    "extraction_status": "EXTRACTED_TEXT",
                    "content_type": "text/html",
                    "article_title": article_title,
                    "article_published_at": published,
                    "text_chars": len(text),
                    "text": text,
                })
                article_path = articles_dir / f"article-{i:03d}.md"
                article_path.write_text(
                    f"# {article_title or title}\n\n"
                    f"- Original URL: {url}\n"
                    f"- Retrieved at (UTC): {generated_at}\n"
                    f"- Publisher date: {published or 'Not found'}\n"
                    f"- Extraction status: EXTRACTED_TEXT (heuristic extraction; completeness not guaranteed)\n\n"
                    f"## Extracted text\n\n{text}\n",
                    encoding="utf-8",
                )
                record["article_file"] = str(article_path.as_posix())
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                record["extraction_status"] = "EXTRACTION_FAILED"
                record["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"
        records.append(record)
        report.extend([
            f"## {i}. {title}", "",
            f"- Discovery source: {url or 'No URL'}",
            f"- Published date from discovery: {item.get('published_at') or 'Unknown'}",
            f"- Extraction status: **{record['extraction_status']}**",
        ])
        if record["extraction_status"] == "EXTRACTED_TEXT":
            report.extend([
                f"- Extracted title: {record['article_title'] or 'Not found'}",
                f"- Article date from page metadata: {record['article_published_at'] or 'Not found'}",
                f"- Extracted characters: {record['text_chars']}",
                "", "### Extracted content", "", record["text"][:8000],
            ])
        elif record["error"]:
            report.append(f"- Note: {record['error']}")
        report.append("")
        time.sleep(0.25)

    successful = sum(1 for row in records if row["extraction_status"] == "EXTRACTED_TEXT")
    summary = {
        "generated_at": generated_at,
        "candidate_count": len(records),
        "extracted_text_count": successful,
        "failed_or_unavailable_count": len(records) - successful,
        "extraction_is_heuristic_not_completeness_guaranteed": True,
        "full_text_verification_performed": False,
        "records": [{k: v for k, v in row.items() if k != "text"} for row in records],
    }
    (root / "research-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (root / "sources.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "extraction-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Research extraction complete: {successful}/{len(records)} pages yielded extractable text.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
