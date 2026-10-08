"""Discovery-only adapters for PubMed and Europe PMC.

Abstracts and bibliographic metadata help find research. They are not treated
as verbatim quotations or claim evidence until the cited source is reviewed.
"""

from __future__ import annotations

import html
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional

from engine.config import NCBI_EMAIL, NCBI_TOOL, PUBMED_API_KEY
from engine.providers.evidence_model import EvidenceItem, Source, SourceTier, SourceType
from engine.providers.research_base import ResearchProvider

logger = logging.getLogger(__name__)
_USER_AGENT = "NugiContentIntelligence/1.0 (scholarly metadata discovery)"
_MAX_RESPONSE_BYTES = 3 * 1024 * 1024


def _strip_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", value).strip()


class _NCBIClient:
    """Polite E-utilities client with bounded responses and rate limiting."""

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.min_interval = 0.12 if PUBMED_API_KEY else 0.36
        self._last_request = 0.0
        self._cooldown_until = 0.0

    def get(self, endpoint: str, params: dict) -> Optional[bytes]:
        if time.monotonic() < self._cooldown_until:
            return None
        values = dict(params)
        values.setdefault("tool", NCBI_TOOL)
        if NCBI_EMAIL:
            values.setdefault("email", NCBI_EMAIL)
        if PUBMED_API_KEY:
            values.setdefault("api_key", PUBMED_API_KEY)
        query = urllib.parse.urlencode(values)
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{endpoint}?{query}"
        delay = self.min_interval - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/xml"})
        self._last_request = time.monotonic()
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    payload = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(payload) > _MAX_RESPONSE_BYTES:
                    logger.info("PubMed response exceeded size limit")
                    return None
                return payload
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or exc.code in {500, 502, 503, 504}:
                    self._cooldown_until = time.monotonic() + 1.0
                    if attempt == 0 and exc.code in {500, 502, 503, 504}:
                        time.sleep(0.5)
                        continue
                logger.info("PubMed request failed with HTTP %s", exc.code)
                return None
            except Exception as exc:
                logger.info("PubMed request failed: %s", exc)
                return None
        return None


class PubMedProvider(ResearchProvider):
    """Retrieve PubMed search records and abstracts as research discovery."""

    PROVIDER_NAME = "pubmed"

    def __init__(self, client: Optional[_NCBIClient] = None):
        self.client = client or _NCBIClient()
        self._cache = {}

    def search_evidence(self, query: str, max_results: int = 5) -> List[EvidenceItem]:
        if not query.strip():
            return []
        limit = max(1, min(int(max_results), 10))
        cached = self._cache.get(query)
        if cached and cached[0] > time.monotonic():
            return cached[1][:limit]
        search = self.client.get("esearch.fcgi", {"db": "pubmed", "term": query[:300], "retmode": "xml", "retmax": limit})
        if not search:
            return []
        try:
            ids = [node.text or "" for node in ET.fromstring(search).findall(".//IdList/Id") if node.text]
        except ET.ParseError:
            return []
        if not ids:
            return []
        payload = self.client.get("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
        if not payload:
            return []
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []
        results: List[EvidenceItem] = []
        for article in root.findall(".//PubmedArticle")[:limit]:
            pmid = (article.findtext(".//PMID") or "").strip()
            title = _strip_markup(article.findtext(".//ArticleTitle") or "")
            if not pmid or not title:
                continue
            abstract_parts = [_strip_markup(node.text or "") for node in article.findall(".//Abstract/AbstractText")]
            abstract = " ".join(part for part in abstract_parts if part)
            author_names = []
            for author in article.findall(".//Author")[:4]:
                name = " ".join(filter(None, [author.findtext("ForeName"), author.findtext("LastName")]))
                if name:
                    author_names.append(name)
            authors = ", ".join(author_names)
            journal = _strip_markup(article.findtext(".//Journal/Title") or "PubMed indexed journal")
            date = article.findtext(".//PubDate/Year") or article.findtext(".//PubDate/MedlineDate") or ""
            doi = next((node.text or "" for node in article.findall(".//ELocationID") if node.attrib.get("EIdType") == "doi"), "")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if doi:
                url = f"https://doi.org/{doi}"
            source = Source(url=url, publisher=journal, tier=SourceTier.S2,
                            source_type=SourceType.ACADEMIC, title=title,
                            published_at=str(date)[:80], reliability="HIGH", is_primary=False,
                            author=authors, metadata={"provider": "PubMed", "pmid": pmid, "doi": doi,
                                "evidence_role": "RESEARCH_DISCOVERY", "abstract_is_not_a_quote": True})
            results.append(EvidenceItem(
                id=f"pubmed_{pmid}", claim_text=f"PubMed research record: {title}", source=source,
                exact_quote="", retrieved_snippet=abstract[:4000],
                source_description="PubMed abstract/bibliographic discovery record; consult the publisher or repository record before using a claim.",
                summary=title, confidence=0.0, is_supporting=False, lineage_root=url,
            ))
        if results:
            if len(self._cache) >= 64:
                self._cache.pop(next(iter(self._cache)))
            self._cache[query] = (time.monotonic() + 900, results)
        return results


class EuropePMCProvider(ResearchProvider):
    """Search Europe PMC publications and record open-access availability."""

    PROVIDER_NAME = "europe_pmc"
    API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self._cache = {}
        self._last_request = 0.0
        self._cooldown_until = 0.0

    def search_evidence(self, query: str, max_results: int = 5) -> List[EvidenceItem]:
        if not query.strip():
            return []
        limit = max(1, min(int(max_results), 10))
        params = urllib.parse.urlencode({"query": query[:300], "format": "json", "resultType": "core", "pageSize": limit})
        url = f"{self.API_URL}?{params}"
        cached = self._cache.get(url)
        if cached and cached[0] > time.monotonic():
            rows = cached[1]
        else:
            if time.monotonic() < self._cooldown_until:
                return []
            delay = 0.2 - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
            try:
                self._last_request = time.monotonic()
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    payload = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(payload) > _MAX_RESPONSE_BYTES:
                    return []
                import json
                data = json.loads(payload.decode("utf-8", errors="replace"))
                rows = data.get("resultList", {}).get("result", [])
                if len(self._cache) > 128:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[url] = (time.monotonic() + 900, rows)
            except Exception as exc:
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                    self._cooldown_until = time.monotonic() + 2.0
                logger.info("Europe PMC search failed: %s", exc)
                return []
        results: List[EvidenceItem] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            title = _strip_markup(str(row.get("title") or ""))
            if not title:
                continue
            pmid = str(row.get("pmid") or "")
            doi = str(row.get("doi") or "")
            url = f"https://doi.org/{doi}" if doi else (f"https://europepmc.org/article/MED/{pmid}" if pmid else self.API_URL)
            abstract = _strip_markup(str(row.get("abstractText") or ""))
            author = str(row.get("authorString") or "")
            journal = str(row.get("journalTitle") or "Europe PMC record")
            date = str(row.get("firstPublicationDate") or row.get("pubYear") or "")
            oa = str(row.get("isOpenAccess") or "N").upper() == "Y"
            source = Source(url=url, publisher=journal, tier=SourceTier.S2,
                            source_type=SourceType.ACADEMIC, title=title,
                            published_at=date[:80], reliability="HIGH", is_primary=False,
                            author=author[:300], metadata={"provider": "Europe PMC", "pmid": pmid, "doi": doi,
                                "is_open_access": oa, "pmcid": str(row.get("pmcid") or ""),
                                "evidence_role": "RESEARCH_DISCOVERY", "abstract_is_not_a_quote": True,
                                "full_text_fetched": False})
            results.append(EvidenceItem(
                id=f"europepmc_{pmid or doi or len(results)}", claim_text=f"Europe PMC research record: {title}",
                source=source, exact_quote="", retrieved_snippet=abstract[:4000],
                source_description="Europe PMC abstract/bibliographic discovery record; full text was not fetched and the abstract is not a verbatim quotation.",
                summary=title, confidence=0.0, is_supporting=False, lineage_root=url,
            ))
        return results
