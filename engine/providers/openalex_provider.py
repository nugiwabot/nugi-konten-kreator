"""
engine/providers/openalex_provider.py
=====================================
Academic / Specialist Research Provider using OpenAlex REST API.
Zero-key, polite user-agent pool. Tier S2 (Specialist Academic).
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

from engine.providers.research_base import ResearchProvider
from engine.providers.evidence_model import EvidenceItem, Source, SourceTier, SourceType

logger = logging.getLogger(__name__)


class OpenAlexProvider(ResearchProvider):
    """
    Queries OpenAlex for scholarly literature, peer-reviewed works,
    and institutional research on urbanism, economics, housing, AI, and society.
    """
    PROVIDER_NAME: str = "openalex"
    API_URL: str = "https://api.openalex.org/works"

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
                "search": query,
                "per_page": max_results,
                "mailto": self.mailto,
            }
            url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"NugiContentIntelligence/1.0 (mailto:{self.mailto})"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                for idx, work in enumerate(results):
                    work_id = work.get("id", f"openalex_{idx}")
                    title = work.get("title") or "Scholarly Paper"
                    pub_year = str(work.get("publication_year", ""))
                    doi = work.get("doi") or f"https://openalex.org/{work_id.split('/')[-1]}"
                    
                    # Authors
                    authorships = work.get("authorships", [])
                    authors = [a.get("author", {}).get("display_name", "") for a in authorships[:3]]
                    author_str = ", ".join(filter(None, authors)) or "Scholarly Authors"

                    # Primary source host venue
                    primary_loc = work.get("primary_location") or {}
                    source_obj = primary_loc.get("source") or {}
                    host_venue = source_obj.get("display_name", "Academic Journal / Repository")

                    # Abstract reconstruction from inverted index if present
                    abstract_index = work.get("abstract_inverted_index")
                    abstract = ""
                    if abstract_index:
                        try:
                            word_positions = []
                            for word, positions in abstract_index.items():
                                for pos in positions:
                                    word_positions.append((pos, word))
                            word_positions.sort(key=lambda x: x[0])
                            abstract = " ".join(w[1] for w in word_positions[:120])
                        except Exception:
                            abstract = ""

                    summary_text = abstract or title

                    # Concept metrics
                    concepts = [c.get("display_name", "") for c in work.get("concepts", [])[:4]]
                    cited_by = work.get("cited_by_count", 0)

                    source_entity = Source(
                        url=doi,
                        publisher=f"{host_venue} (OpenAlex)",
                        tier=SourceTier.S2,
                        source_type=SourceType.ACADEMIC,
                        title=title,
                        published_at=pub_year,
                        reliability="HIGH",
                        is_primary=True,
                        author=author_str,
                        metadata={
                            "cited_by_count": cited_by,
                            "concepts": concepts,
                            "openalex_id": work_id,
                            "evidence_role": "ABSTRACT_RESEARCH_DISCOVERY",
                            "abstract_is_not_a_quote": True,
                        }
                    )

                    evidence = EvidenceItem(
                        id=f"openalex_{work_id.split('/')[-1]}",
                        claim_text=(
                            f"Retrieved abstract snippet: {abstract[:300]}"
                            if abstract else f"Bibliographic record: {title}"
                        ),
                        source=source_entity,
                        # Abstract reconstruction is provider-supplied text, but it
                        # is not a verified verbatim quotation from the publication.
                        exact_quote="",
                        retrieved_snippet=abstract,
                        source_description=(
                            "OpenAlex metadata and abstract reconstructed from its inverted index."
                            if abstract else "OpenAlex bibliographic metadata only; no abstract text was returned."
                        ),
                        summary=summary_text,
                        # Citation counts measure scholarly attention, not the
                        # research topic, so they are retained only in source
                        # metadata and never exposed as topical statistics.
                        data_points=[],
                        confidence=0.92,
                        is_supporting=bool(abstract),
                    )
                    items.append(evidence)

        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}. No OpenAlex evidence was retrieved.")
            return []

        return items
