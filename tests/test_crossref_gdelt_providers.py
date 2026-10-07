"""
tests/test_crossref_gdelt_providers.py
======================================
Tests for Crossref and GDELT zero-key research providers.
"""

import pytest
from engine.providers.crossref_provider import CrossrefProvider
from engine.providers.gdelt_provider import GDELTProvider
from engine.providers.evidence_model import SourceTier, SourceType


def test_crossref_provider_fallback_fixtures():
    """Verify Crossref provider returns valid S2 academic evidence."""
    provider = CrossrefProvider()
    fixtures = provider._get_offline_fixtures("housing inequality", max_results=2)
    assert len(fixtures) >= 1
    item = fixtures[0]
    assert item.source.tier == SourceTier.S2
    assert item.source.source_type == SourceType.ACADEMIC
    assert item.confidence >= 0.90
    assert item.lineage_root is not None


def test_crossref_search_evidence_execution():
    """Verify Crossref search_evidence produces valid EvidenceItems."""
    provider = CrossrefProvider(timeout=5)
    results = provider.search_evidence("urban economics", max_results=2)
    assert len(results) >= 1
    for r in results:
        assert r.source.tier == SourceTier.S2
        assert r.source.is_primary is True
        assert r.confidence > 0.8


def test_gdelt_provider_fallback_fixtures():
    """Verify GDELT provider returns valid event intelligence fixtures."""
    provider = GDELTProvider()
    fixtures = provider._get_offline_fixtures("southeast asia housing", max_results=2)
    assert len(fixtures) >= 1
    item = fixtures[0]
    assert item.source.tier in (SourceTier.S3, SourceTier.S4)
    assert item.confidence >= 0.80
    assert item.lineage_root is not None


def test_gdelt_search_evidence_execution():
    """Verify GDELT search_evidence returns well-formed EvidenceItems."""
    provider = GDELTProvider(timeout=5)
    results = provider.search_evidence("jakarta transit", max_results=2)
    assert len(results) >= 1
    for r in results:
        assert r.source.tier.rank <= 7
        assert r.summary != ""
