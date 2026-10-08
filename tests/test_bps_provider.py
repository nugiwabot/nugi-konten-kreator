"""Fail-closed tests for the BPS adapter until live retrieval is implemented."""

from engine.providers.bps_provider import BPSDataProvider


def test_bps_adapter_does_not_claim_static_values_as_live_evidence():
    assert BPSDataProvider().search_evidence("backlog perumahan", max_results=2) == []
