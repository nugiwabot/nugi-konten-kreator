"""
tests/test_evidence_lineage.py
==============================
Regression tests for Evidence Lineage Tracking and S0-S7 Priority in Research Dossiers.
"""

import pytest
from engine.providers.evidence_model import (
    Source, SourceTier, SourceType, EvidenceItem, Claim, classify_source_tier
)
from engine.pipeline.research_dossier import DossierGenerator


def test_evidence_lineage_prevents_syndicated_inflation():
    """
    Syndicated republication of the same root report should not count
    as multiple independent corroborations.
    """
    root_url = "https://bps.go.id/publikasi/backlog-2024.pdf"
    
    # Three different media articles all citing the same BPS report
    s_media1 = Source(url="https://kompas.com/artikel1", publisher="Kompas", tier=SourceTier.S4)
    s_media2 = Source(url="https://tempo.co/artikel2", publisher="Tempo", tier=SourceTier.S4)
    s_media3 = Source(url="https://bisnis.com/artikel3", publisher="Bisnis Indonesia", tier=SourceTier.S4)

    ev1 = EvidenceItem(
        id="ev_1",
        claim_text="Backlog mencapai 9.9 juta",
        source=s_media1,
        lineage_root=root_url,
        is_derivative=True,
    )
    ev2 = EvidenceItem(
        id="ev_2",
        claim_text="Defisit perumahan 9.9 juta unit",
        source=s_media2,
        lineage_root=root_url,
        is_derivative=True,
    )
    ev3 = EvidenceItem(
        id="ev_3",
        claim_text="9.9 juta keluarga belum punya rumah",
        source=s_media3,
        lineage_root=root_url,
        is_derivative=True,
    )

    claim = Claim(
        id="c_syndicated",
        text="Backlog perumahan mencapai 9.9 juta unit",
        supporting_evidence=[ev1, ev2, ev3]
    )

    claim.evaluate_status()
    # All 3 share the same lineage_root, so independent_sources_count must be 1, not 3
    assert claim.independent_sources_count == 1
    assert claim.lineage_roots == [root_url]


def test_independent_evidence_lineages_verify_claim():
    """Two distinct independent lineages without S1 still corroborate to VERIFIED."""
    ev_study_a = EvidenceItem(
        id="ev_a",
        claim_text="Laju komuter meningkat 25%",
        source=Source(url="https://reuters.com/investigation", publisher="Reuters", tier=SourceTier.S3),
        lineage_root="https://reuters.com/investigation",
    )
    ev_study_b = EvidenceItem(
        id="ev_b",
        claim_text="Survei independen komuter Jakarta mencatat lonjakan 25%",
        source=Source(url="https://bloomberg.com/report", publisher="Bloomberg", tier=SourceTier.S3),
        lineage_root="https://bloomberg.com/report",
    )

    claim = Claim(
        id="c_independent",
        text="Laju perjalanan komuter Bodetabek melonjak 25%",
        supporting_evidence=[ev_study_a, ev_study_b]
    )
    claim.evaluate_status()
    assert claim.independent_sources_count == 2
    assert claim.status == "VERIFIED"
    assert claim.confidence_score >= 0.80


def test_copied_headlines_from_different_domains_do_not_add_corroboration():
    headline = "Housing backlog rises as young households struggle"
    first = EvidenceItem(
        id="news_a", claim_text="The same wire story", source=Source(
            url="https://outlet-a.example/story", publisher="Outlet A", tier=SourceTier.S3, title=headline,
        ), retrieved_snippet="Same story text.",
    )
    second = EvidenceItem(
        id="news_b", claim_text="The same wire story republished", source=Source(
            url="https://outlet-b.example/story", publisher="Outlet B", tier=SourceTier.S3, title=headline,
        ), retrieved_snippet="Same story text.",
    )
    claim = Claim(id="copied", text="Housing backlog rises", supporting_evidence=[first, second])
    claim.evaluate_status()
    assert claim.independent_sources_count == 1
    assert claim.status == "PROBABLE"


def test_dossier_generator_enforces_s0_s7_hierarchy():
    """
    DossierGenerator must sort all evidence so primary/authoritative sources (S0-S2)
    precede secondary/generic web results (S3-S7).
    """
    class FixedProvider:
        def __init__(self, items):
            self.items = items

        def search_evidence(self, query, max_results=5):
            return self.items[:max_results]

    class EmptyWeb:
        def search(self, query, recency=None, max_results=5):
            return []

    primary = EvidenceItem(
        id="bps_fixture",
        claim_text="Official survey recorded a measured housing indicator.",
        source=Source(
            url="https://bps.go.id/release/example",
            publisher="BPS",
            tier=SourceTier.S1,
            source_type=SourceType.STATISTICS,
            is_primary=True,
        ),
        retrieved_snippet="Official survey recorded a measured housing indicator.",
        is_supporting=True,
        confidence=0.95,
        lineage_root="https://bps.go.id/release/example",
    )
    secondary = EvidenceItem(
        id="media_fixture",
        claim_text="A secondary report describes a related trend.",
        source=Source(url="https://example.org/report", publisher="Example Media", tier=SourceTier.S4),
        retrieved_snippet="A secondary report describes a related trend.",
        is_supporting=True,
        lineage_root="https://example.org/report",
    )
    gen = DossierGenerator(
        bps_provider=FixedProvider([primary]),
        openalex_provider=FixedProvider([]),
        crossref_provider=FixedProvider([]),
        gdelt_provider=FixedProvider([secondary]),
        pubmed_provider=FixedProvider([]),
        europe_pmc_provider=FixedProvider([]),
        web_provider=EmptyWeb(),
    )
    dossier = gen.build_dossier("krisis hunian komuter", max_evidence_per_source=2)

    # Check evidence sorting: tier ranks must be monotonically non-decreasing
    tier_ranks = [e.source.tier.rank for e in dossier.evidence_items]
    assert tier_ranks == sorted(tier_ranks), f"Evidence items not strictly sorted by S0-S7: {tier_ranks}"

    # Authoritative sources must be present
    assert len(dossier.primary_sources) >= 1
    # Verify claims have lineage tracking
    for c in dossier.claims:
        assert hasattr(c, "independent_sources_count")
        assert hasattr(c, "lineage_roots")
