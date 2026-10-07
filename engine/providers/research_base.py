"""
engine/providers/research_base.py
=================================
Abstract ResearchProvider base class.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from engine.providers.evidence_model import EvidenceItem


class ResearchProvider:
    """
    Abstract interface for specialized research providers.
    All providers normalize results into List[EvidenceItem].
    """
    PROVIDER_NAME: str = "base"

    def search_evidence(
        self,
        query: str,
        max_results: int = 5
    ) -> List[EvidenceItem]:
        """Search and extract structured evidence items for a given query."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if provider endpoint is currently reachable."""
        return True
