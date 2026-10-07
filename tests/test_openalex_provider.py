"""
Tests for OpenAlex Academic Research Provider.
"""
import pytest
from engine.providers.openalex_provider import OpenAlexProvider
from engine.providers.evidence_model import SourceTier, SourceType


def test_openalex_offline_fixtures():
    provider = OpenAlexProvider()
    fixtures = provider._get_offline_fixtures("urban housing", max_results=2)
    assert len(fixtures) == 2
    assert fixtures[0].source.tier == SourceTier.S2
    assert fixtures[0].source.source_type == SourceType.ACADEMIC
    assert fixtures[0].source.is_primary is True
    assert "agglomeration" in fixtures[0].claim_text.lower()


def test_openalex_search_evidence():
    provider = OpenAlexProvider()
    # Should safely return structured items even if network drops
    items = provider.search_evidence("urban sprawl and commuting", max_results=2)
    assert len(items) > 0
    assert items[0].source.tier == SourceTier.S2
    assert items[0].confidence > 0.8
