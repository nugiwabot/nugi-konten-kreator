"""
engine/providers/crossref_provider.py
=====================================
Scholarly Metadata and DOI Verification Provider using Crossref REST API.
Zero-key polite pool access. Tier S2 (Specialist Academic).
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

from engine.providers.research_base import ResearchProvider
from engine.providers.evidence_model import (
    EvidenceItem, Source, SourceTier, SourceType
)

logger = logging.getLogger(__name__)


class CrossrefProvider(ResearchProvider):
    """
    Queries Crossref REST API for verified peer-reviewed publications,
    DOI metadata, journal provenance, and citation metrics.
    """
    PROVIDER_NAME: str = "crossref"
    API_URL: str = "https://api.crossref.org/works"

    def __init__(self, mailto: str = "nugi.research@gmail.com", timeout: int = 10):
        self.mailto = mailto
        self.timeout = timeout

    def search_evidence(
        self,
        query: str,
        max_results: int = 5
    ) -> List[EvidenceItem]:
        items: List[EvidenceItem] = []
        try:
            params = {
                "query": query,
                "rows": max_results,
                "mailto": self.mailto,
            }
            url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"NugiContentIntelligence/1.0 (mailto:{self.mailto})"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                work_items = data.get("message", {}).get("items", [])
                
                for idx, work in enumerate(work_items):
                    titles = work.get("title", [])
                    title = titles[0] if titles else "Scholarly Publication"
                    doi = work.get("DOI", "")
                    doi_url = f"https://doi.org/{doi}" if doi else ""
                    
                    # Authors
                    authors_list = work.get("author", [])
                    author_names = [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in authors_list[:3]
                    ]
                    author_str = ", ".join(filter(None, author_names)) or "Scholarly Author"
                    
                    # Venue
                    container = work.get("container-title", [])
                    journal = container[0] if container else "Academic Journal / Crossref"
                    
                    # Date
                    pub_parts = work.get("published-print", {}).get("date-parts", [[]])[0] or \
                                work.get("published-online", {}).get("date-parts", [[]])[0] or []
                    pub_year = str(pub_parts[0]) if pub_parts else ""
                    
                    # Citation counts
                    citations = work.get("is-referenced-by-count", 0)
                    source = Source(
                        url=doi_url,
                        publisher=journal,
                        tier=SourceTier.S2,
                        source_type=SourceType.ACADEMIC,
                        title=title,
                        published_at=pub_year,
                        reliability="HIGH",
                        is_primary=True,
                        author=author_str,
                        metadata={"doi": doi, "citations": citations}
                    )

                    evidence = EvidenceItem(
                        id=f"crossref_{idx}",
                        claim_text=f"Studi akademik terindeks Crossref '{title}' ({pub_year}) dalam {journal}.",
                        source=source,
                        # Crossref returns bibliographic metadata, not a passage from
                        # the work.  Metadata must never be presented as a quote.
                        exact_quote="",
                        source_description=f"Bibliographic metadata from Crossref: {title} by {author_str} in {journal} ({pub_year}). DOI: {doi}",
                        summary=title,
                        # Citation counts are metadata about the paper, not
                        # evidence for the searched topic.
                        data_points=[],
                        confidence=0.92,
                        # Bibliographic metadata is useful for discovery, but it
                        # does not substantiate a topical claim by itself.
                        is_supporting=False,
                        lineage_root=doi_url or journal
                    )
                    items.append(evidence)

        except Exception as e:
            logger.warning(f"Crossref search failed: {e}. No Crossref evidence was retrieved.")
            return []

        return items
