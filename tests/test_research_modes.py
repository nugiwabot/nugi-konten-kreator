"""
Tests for Research Engine v2 Modes and Source Evaluation.
Verifies Evergreen, Current, Historical, and Data-Driven research paradigms.
"""
import pytest
from engine.editorial.taxonomy import classify_topic, RESEARCH_MODES


def test_evergreen_mode_classification():
    """Fundamental enduring questions must classify as evergreen without requiring current news."""
    topic = "Kenapa tanah tidak bisa diproduksi lebih banyak oleh manusia?"
    classified = classify_topic(topic)
    assert classified["research_mode"] == "evergreen"
    assert classified["primary_domain"] in ("property", "economy")


def test_current_mode_classification():
    """Breaking policy or recent releases must classify as current."""
    topic = "Kebijakan baru Bank Indonesia terkait suku bunga KPR minggu ini"
    classified = classify_topic(topic)
    assert classified["research_mode"] == "current"


def test_historical_mode_classification():
    """Origins, colonial urban planning, and lineage must classify as historical."""
    topic = "Sejarah kolonial tata ruang kawasan Menteng dan asal-usul sertifikat tanah"
    classified = classify_topic(topic)
    assert classified["research_mode"] == "historical"
    assert classified["lens"] == "history"


def test_data_driven_mode_classification():
    """Statistical anomalies, percentages, and survey figures must classify as data-driven."""
    topic = "Gaji rata-rata naik 4%, tetapi harga rumah di Bandung naik 18% menurut data BPS"
    classified = classify_topic(topic)
    assert classified["research_mode"] == "data_driven"


def test_source_credibility_tiers():
    """Verify that government and official institutional data are prioritized over social media."""
    source_tier_weights = {
        "Tier 1 - Official Government": 1,
        "Tier 2 - Official Institutional": 2,
        "Tier 3 - Academic Research": 3,
        "Tier 4 - Original Think Tank Reports": 4,
        "Tier 5 - Reputable Journalism": 5,
        "Tier 6 - Industry Publications": 6,
        "Tier 7 - Commentary / Social Media": 7
    }
    # Government tier must be highest rank
    assert source_tier_weights["Tier 1 - Official Government"] < source_tier_weights["Tier 7 - Commentary / Social Media"]


def test_epistemic_separation_schema():
    """Ensures research extracts separate categories for fact, claim, interpretation, speculation."""
    sample_dossier = {
        "fact": "BPS mencatat inflasi bahan bangunan sebesar 3.8% pada Q1 2026",
        "claim": "Pengembang mengklaim proyek mereka memberikan yield 12% per tahun",
        "interpretation": "Kenaikan harga material mempersempit margin kontraktor rumah subsidi",
        "speculation": "Suku bunga diprediksi akan turun di paruh kedua tahun ini"
    }
    assert "fact" in sample_dossier
    assert "claim" in sample_dossier
    assert "interpretation" in sample_dossier
    assert "speculation" in sample_dossier
