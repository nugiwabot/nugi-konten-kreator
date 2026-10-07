"""
Tests for BPS Authoritative Statistics Provider.
"""
import pytest
from engine.providers.bps_provider import BPSDataProvider
from engine.providers.evidence_model import SourceTier, SourceType


def test_bps_housing_backlog_evidence():
    provider = BPSDataProvider()
    items = provider.search_evidence("backlog perumahan dan kpr", max_results=2)
    assert len(items) > 0
    backlog_item = items[0]
    assert backlog_item.source.tier == SourceTier.S1
    assert backlog_item.source.source_type == SourceType.STATISTICS
    assert "9.9" in backlog_item.claim_text or "Susenas" in backlog_item.exact_quote
    assert len(backlog_item.data_points) >= 1
    assert backlog_item.confidence >= 0.95


def test_bps_commuter_evidence():
    provider = BPSDataProvider()
    items = provider.search_evidence("komuter jabodetabek dan stasiun", max_results=2)
    assert len(items) > 0
    commuter_item = items[0]
    assert "komuter" in commuter_item.claim_text.lower() or "komuter" in commuter_item.summary.lower()
    assert commuter_item.source.is_primary is True
