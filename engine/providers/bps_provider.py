"""BPS research provider.

This adapter intentionally returns no evidence until a live BPS retrieval is
implemented. Previously it labelled hard-coded values and generated prose as
official BPS evidence, which could produce false verification.
"""

from __future__ import annotations

import logging
from typing import List

from engine.providers.evidence_model import EvidenceItem
from engine.providers.research_base import ResearchProvider

logger = logging.getLogger(__name__)


class BPSDataProvider(ResearchProvider):
    """Unavailable live adapter: no static values are represented as evidence."""

    PROVIDER_NAME = "bps"

    def search_evidence(self, query: str, max_results: int = 5) -> List[EvidenceItem]:
        logger.info("BPS live retrieval is not configured; returning no BPS evidence.")
        return []
