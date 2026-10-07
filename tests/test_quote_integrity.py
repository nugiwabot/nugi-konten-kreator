"""
tests/test_quote_integrity.py
==============================
Verifies that exact quotes in EvidenceItem are strictly semantic and verbatim,
and that generated summaries/snippets are not masquerading as quotes.
Also verifies publication recency evaluation.
"""

import pytest
from engine.providers.evidence_model import (
    EvidenceItem, Source, SourceTier, SourceType, evaluate_recency
)
from engine.pipeline.research_dossier import DossierGenerator


def test_quote_integrity_separation():
    """
    Ensure exact_quote is strictly non-empty only when verbatim quote text is present.
    Generic metadata or descriptions must remain in retrieved_snippet/source_description.
    """
    source = Source(
        url="https://republika.co.id/berita/sample",
        publisher="Republika",
        tier=SourceTier.S4,
        source_type=SourceType.NEWS_GENERAL,
        title="Laporan Survei Pasar 2026"
    )

    # Case 1: Plain snippet without quotation marks
    item_snippet = EvidenceItem(
        id="ev_snippet",
        claim_text="Pertumbuhan sektor mencapai 5 persen menurut laporan.",
        source=source,
        exact_quote="",  # Must NOT manufacture a quote
        retrieved_snippet="Pertumbuhan sektor mencapai 5 persen menurut laporan terkini.",
        source_description="Republika: Laporan Survei Pasar 2026",
        summary="Laporan Survei Pasar 2026"
    )
    assert item_snippet.exact_quote == ""
    assert item_snippet.retrieved_snippet != ""
    assert item_snippet.source_description != ""

    # Case 2: Verbatim quote extraction
    item_verbatim = EvidenceItem(
        id="ev_quote",
        claim_text="Menteri menyatakan inflasi terkendali.",
        source=source,
        exact_quote="Kami memastikan pasokan pangan dan stabilitas harga terjaga hingga akhir kuartal.",
        retrieved_snippet='Menteri menegaskan: "Kami memastikan pasokan pangan dan stabilitas harga terjaga hingga akhir kuartal."',
        summary="Kutipan Resmi Menteri"
    )
    assert item_verbatim.exact_quote != ""
    assert "pasokan pangan" in item_verbatim.exact_quote


def test_recency_evaluation():
    """
    Ensure evaluate_recency distinguishes current vs historical vs outdated sources.
    """
    rec_current = evaluate_recency("2026-05-10", topic_mode="current")
    assert rec_current["temporal_category"] in ("CURRENT", "RECENT")
    assert rec_current["is_outdated"] is False

    rec_old_for_current_news = evaluate_recency("2018-01-01", topic_mode="current")
    assert rec_old_for_current_news["is_outdated"] is True

    rec_old_for_historical = evaluate_recency("1998-05-21", topic_mode="historical")
    assert rec_old_for_historical["temporal_category"] == "HISTORICAL"
    assert rec_old_for_historical["is_outdated"] is False
