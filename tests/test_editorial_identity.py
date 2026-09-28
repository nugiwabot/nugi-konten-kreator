"""
Tests for Editorial Identity, Anchor Tests, and 12 Hard Rejection Rules.
Verifies Brand Fit according to Implementation Plan v2.
"""
import pytest
from engine.editorial.taxonomy import classify_topic, PRIMARY_DOMAINS
from engine.editorial.property_bridge import evaluate_property_anchor, find_property_bridge
from engine.editorial.fit_score import calculate_editorial_fit
from engine.editorial.quality_gate import check_quality_gates, check_hard_rejections


def test_generic_ai_topic_rejected():
    """Generic AI tools list must be rejected outright."""
    bad_idea = {
        "title": "5 AI Tools Gratis yang Wajib Kamu Coba Minggu Ini",
        "human_question": "Mau kerja lebih cepat?",
        "sources": ["twitter"]
    }
    violations = check_hard_rejections(bad_idea)
    assert len(violations) > 0
    assert any("Generic AI Tools" in v["rule"] for v in violations)

    gate = check_quality_gates(bad_idea)
    assert gate["passed"] is False


def test_property_listing_rejected():
    """Property sales brochures and listings must be rejected."""
    listing_idea = {
        "title": "Dijual Rumah Murah Tipe 36/72 Cicilan Hanya 2 Juta Per Bulan",
        "human_question": "Cari rumah murah?",
        "sources": ["brosur developer"]
    }
    violations = check_hard_rejections(listing_idea)
    assert len(violations) > 0
    assert any("Property Listing" in v["rule"] for v in violations)

    gate = check_quality_gates(listing_idea)
    assert gate["passed"] is False


def test_valid_property_topic_accepted():
    """Fundamental property questions with human relevance must pass."""
    valid_property_idea = {
        "title": "Kenapa manusia rela berutang 20 tahun demi memiliki sepetak rumah?",
        "human_question": "Mengapa kita terobsesi dengan sertifikat kepemilikan tanah?",
        "contradiction": "Menyewa lebih murah secara hitungan finansial, tetapi manusia tetap memilih beban KPR puluhan tahun",
        "core_revelation": "Rumah bukan instrumen investasi semata, melainkan perlindungan psikologis purba akan rasa aman",
        "deeper_why": "Struktur perbankan dan ketiadaan jaminan sosial hari tua memaksa tanah menjadi satu-satunya benteng pertahanan",
        "property_connection": "Kebutuhan hunian -> psikologi teritorial -> komitmen utang jangka panjang",
        "sources": ["BPS 2026", "Bank Indonesia SHPR", "Survei Kemenkeu"]
    }
    gate = check_quality_gates(valid_property_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75
    assert gate["fit_verdict"] == "APPROVED"


def test_valid_ai_property_bridge_accepted():
    """AI topics with causal link to office geography and housing must pass."""
    valid_ai_bridge_idea = {
        "title": "Kalau AI membuat pekerjaan bisa dilakukan dari mana saja, kenapa rumah di pusat kota tetap mahal?",
        "human_question": "Apakah komputasi awan benar-benar membebaskan tempat tinggal kita?",
        "contradiction": "Pekerjaan kognitif pindah ke cloud, namun manusia tetap berdesakan di megapolitan",
        "core_revelation": "Aglomerasi fisik menciptakan serendipity dan jejaring modal sosial yang tidak dapat ditiru algoritma",
        "deeper_why": "Nilai pusat kota bukan pada gedung kantornya, melainkan konsentrasi kekuasaan dan akses relasi manusia",
        "property_connection": "AI agents -> restrukturisasi kantor -> geografi komuter -> disparitas harga tanah",
        "sources": ["Stanford AI Index", "BPS Data Komuter", "Knight Frank"]
    }
    gate = check_quality_gates(valid_ai_bridge_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75
    assert gate["fit_verdict"] == "APPROVED"


def test_valid_city_property_topic_accepted():
    """City dynamics and mobility topics with property anchor must pass."""
    city_idea = {
        "title": "Kenapa kota-kota besar di Indonesia selalu tumbuh melebar ke pinggiran?",
        "human_question": "Kenapa sawah dan kebun di pinggiran kota selalu berubah jadi perumahan?",
        "contradiction": "Pemerintah mendorong hunian vertikal, tapi masyarakat tetap membeli rumah tapak 40 km dari pusat kota",
        "core_revelation": "Regulasi tata ruang dan kelangkaan transportasi massal menciptakan urban sprawl yang tak terbendung",
        "deeper_why": "Insentif pengembang swasta mengunci pasokan lahan murah di pinggiran untuk margin maksimal",
        "property_connection": "Pertumbuhan kota -> tata ruang -> konversi lahan pertanian -> perumahan tapak",
        "sources": ["Bappenas Urban Sprawl Report", "ATR/BPN Tata Ruang"]
    }
    gate = check_quality_gates(city_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75


def test_unrelated_topic_rejected():
    """Topics with zero physical/space/life anchor must fail anchor test."""
    unrelated_idea = {
        "title": "Cara Menginstall Driver VGA NVIDIA di Linux Ubuntu",
        "human_question": "Bagaimana cara compile kernel?",
        "contradiction": "Driver open source vs proprietary",
        "sources": ["Ubuntu forums"]
    }
    anchor_eval = evaluate_property_anchor(unrelated_idea["title"], "tutorial teknis gpu")
    assert anchor_eval["passed"] is False
    assert anchor_eval["score"] == 0

    fit = calculate_editorial_fit(unrelated_idea)
    assert fit["passed"] is False
    assert fit["verdict"] in ("REJECTED", "REVISE")
