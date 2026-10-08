"""
Tests for Normalized Evidence Model and S0–S7 Source Hierarchy.
"""
import pytest
from engine.providers.evidence_model import (
    SourceTier, SourceType, Source, EvidenceItem, Claim, DataPoint, classify_source_tier
)


def test_source_tier_ranking_and_labels():
    assert SourceTier.S0.rank == 0
    assert SourceTier.S1.rank == 1
    assert SourceTier.S7.rank == 7
    assert SourceTier.S1.default_reliability == "HIGH"
    assert SourceTier.S4.default_reliability == "MEDIUM_HIGH"
    assert SourceTier.S7.default_reliability == "LOW_NEEDS_VERIFICATION"


def test_classify_source_tier_domains():
    # S0 Archive
    res_s0 = classify_source_tier("https://archive.org/details/test_newsreel")
    assert res_s0["tier"] == SourceTier.S0
    assert res_s0["is_primary"] is True

    # S1 Gov & Regulators
    res_s1 = classify_source_tier("https://www.bps.go.id/report/2026")
    assert res_s1["tier"] == SourceTier.S1
    assert res_s1["is_primary"] is True

    # S2 Academic
    res_s2 = classify_source_tier("https://openalex.org/W1234567")
    assert res_s2["tier"] == SourceTier.S2
    assert res_s2["is_primary"] is True

    # S3 Wire Service
    res_s3 = classify_source_tier("https://www.reuters.com/markets/asia")
    assert res_s3["tier"] == SourceTier.S3
    assert res_s3["reliability"] == "HIGH"

    # S4 Reputable Media
    res_s4 = classify_source_tier("https://www.kompas.com/properti/read/123")
    assert res_s4["tier"] == SourceTier.S4
    assert res_s4["reliability"] == "MEDIUM_HIGH"

    # S5 Industry
    res_s5 = classify_source_tier("https://www.inman.com/real-estate-trends")
    assert res_s5["tier"] == SourceTier.S5

    # S6 Social
    res_s6 = classify_source_tier("https://twitter.com/nugi/status/999")
    assert res_s6["tier"] == SourceTier.S6
    assert res_s6["reliability"] == "LOW_NEEDS_VERIFICATION"


def test_claim_status_evaluation():
    # One authoritative source supports the claim but does not independently corroborate it.
    s_bps = Source(
        url="https://bps.go.id",
        publisher="BPS",
        tier=SourceTier.S1,
        is_primary=True
    )
    ev_bps = EvidenceItem(
        id="ev_1",
        claim_text="Backlog rumah 9.9 juta",
        source=s_bps,
        summary="Data sensus resmi perumahan"
    )
    claim1 = Claim(
        id="c1",
        text="Defisit perumahan nasional mencapai 9.9 juta unit",
        supporting_evidence=[ev_bps]
    )
    assert claim1.evaluate_status() == "PROBABLE"
    assert claim1.confidence_score < 0.85

    # Claim with contradictory evidence -> DISPUTED
    ev_contradict = EvidenceItem(
        id="ev_contra",
        claim_text="Defisit hanya 2 juta",
        source=Source(url="https://blog.com", publisher="Blog", tier=SourceTier.S6),
        is_supporting=False
    )
    claim1.contradicting_evidence.append(ev_contradict)
    assert claim1.evaluate_status() == "DISPUTED"
