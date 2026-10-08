"""
engine/providers/gdelt_provider.py
==================================
Global News & Event Intelligence Provider using GDELT 2.0 DOC API.
Zero-key global media monitoring and event discovery.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

from engine.providers.research_base import ResearchProvider
from engine.providers.evidence_model import (
    EvidenceItem, Source, SourceTier, SourceType, classify_source_tier
)

logger = logging.getLogger(__name__)


class GDELTProvider(ResearchProvider):
    """
    Queries GDELT 2.0 DOC API for global news tracking, narrative discovery,
    and cross-border coverage of economic, urban, and societal phenomena.
    """
    PROVIDER_NAME: str = "gdelt"
    API_URL: str = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout: int = 10):
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
                "mode": "artlist",
                "maxrecords": max_results,
                "format": "json"
            }
            url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; NugiContentIntelligence/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                articles = data.get("articles", [])
                
                for idx, art in enumerate(articles):
                    art_url = art.get("url", "")
                    domain = art.get("domain", "")
                    title = art.get("title", "")
                    seendate = art.get("seendate", "")
                    
                    cls = classify_source_tier(art_url, domain)
                    
                    source = Source(
                        url=art_url,
                        publisher=domain or "GDELT Monitored Media",
                        tier=cls["tier"],
                        source_type=cls["source_type"],
                        title=title,
                        published_at=seendate[:8] if seendate else "",
                        reliability=cls["reliability"],
                        is_primary=cls["is_primary"],
                        metadata={"evidence_role": "DISCOVERY_ONLY", "article_text_fetched": False},
                    )
                    
                    evidence = EvidenceItem(
                        id=f"gdelt_{idx}",
                        claim_text=f"Laporan media global ({domain}): {title}",
                        source=source,
                        # GDELT's article-list response does not contain article text.
                        exact_quote="",
                        source_description=f"GDELT article-list metadata for {domain}: {title}",
                        summary=title,
                        confidence=0.80 if cls["tier"].rank <= 4 else 0.60,
                        # An article-list title is discovery metadata, not the
                        # article body or evidence for its underlying claims.
                        is_supporting=False,
                        lineage_root=art_url
                    )
                    items.append(evidence)

        except Exception as e:
            logger.warning(f"GDELT search failed: {e}. No GDELT evidence was retrieved.")
            return []

        return items
