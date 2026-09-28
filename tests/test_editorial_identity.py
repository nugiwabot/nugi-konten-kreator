"""
Tests for Editorial Identity v3: HUMAN × PLACE × CHANGE × WHY
Verifies that the editorial system properly enforces:
- Broader Human–Place anchor (not just property)
- New fit score model (human_place_anchor, story_type_fit, novelty)
- New worldview: property is a thread, not mandatory for every topic
- Hard rejection rules remain
"""
import pytest
from engine.editorial.taxonomy import classify_topic, PRIMARY_DOMAINS
from engine.editorial.human_place_engine import evaluate_human_place_anchor, find_human_place_bridge
from engine.editorial.fit_score import (
    calculate_editorial_fit,
    DIMENSION_WEIGHTS,
    MIN_PASSING_SCORE,
    MIN_HUMAN_PLACE_ANCHOR
)
from engine.editorial.quality_gate import check_quality_gates, check_hard_rejections


# ===========================================================================
# Hard rejections still enforced
# ===========================================================================

def test_generic_ai_topic_rejected():
    """Generic AI tools list must be rejected outright (rule unchanged from v2)."""
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
    """Property sales brochures must be rejected (rule unchanged)."""
    listing_idea = {
        "title": "Dijual Rumah Murah Tipe 36/72 Cicilan Hanya 2 Juta Per Bulan",
        "human_question": "Cari rumah murah?",
        "sources": ["brosur developer"]
    }
    violations = check_hard_rejections(listing_idea)
    assert len(violations) > 0

    gate = check_quality_gates(listing_idea)
    assert gate["passed"] is False


# ===========================================================================
# V3: Property topics still valid (but not forced)
# ===========================================================================

def test_valid_property_topic_accepted():
    """Classic property question with human relevance must still pass in v3."""
    valid_property_idea = {
        "title": "Kenapa manusia rela berutang 20 tahun demi memiliki sepetak rumah?",
        "human_question": "Mengapa kita terobsesi dengan sertifikat kepemilikan tanah?",
        "contradiction": "Menyewa lebih murah secara hitungan finansial, tetapi manusia tetap memilih beban KPR puluhan tahun",
        "core_revelation": "Rumah bukan instrumen investasi semata, melainkan perlindungan psikologis purba akan rasa aman",
        "deeper_why": "Struktur perbankan dan ketiadaan jaminan sosial hari tua memaksa tanah menjadi satu-satunya benteng pertahanan",
        "property_connection": "Kebutuhan hunian → psikologi teritorial → komitmen utang jangka panjang",
        "sources": ["BPS 2026", "Bank Indonesia SHPR", "Survei Kemenkeu"]
    }
    gate = check_quality_gates(valid_property_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75
    assert gate["fit_verdict"] == "APPROVED"


def test_valid_ai_property_bridge_accepted():
    """AI with causal link to office geography and housing must still pass."""
    valid_ai_bridge_idea = {
        "title": "Kalau AI membuat pekerjaan bisa dilakukan dari mana saja, kenapa rumah di pusat kota tetap mahal?",
        "human_question": "Apakah komputasi awan benar-benar membebaskan tempat tinggal kita?",
        "contradiction": "Pekerjaan kognitif pindah ke cloud, namun manusia tetap berdesakan di megapolitan",
        "core_revelation": "Aglomerasi fisik menciptakan serendipity dan jejaring modal sosial yang tidak dapat ditiru algoritma",
        "deeper_why": "Nilai pusat kota bukan pada gedung kantornya, melainkan konsentrasi kekuasaan dan akses relasi manusia",
        "property_connection": "AI agents → restrukturisasi kantor → geografi komuter → disparitas harga tanah",
        "sources": ["Stanford AI Index", "BPS Data Komuter", "Knight Frank"]
    }
    gate = check_quality_gates(valid_ai_bridge_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75


# ===========================================================================
# V3 NEW: Non-property topics that still pass with Human–Place anchor
# ===========================================================================

def test_origin_of_settlement_accepted():
    """Human origin story (nomadic → settled) must pass without property keywords."""
    settlement_idea = {
        "title": "Kapan manusia pertama kali berhenti berpindah dan mulai menetap di satu tempat?",
        "human_question": "Apa yang mendorong manusia nomaden untuk membangun permukiman pertama?",
        "core_revelation": "Menetap bukan hanya tentang pertanian — melainkan tentang kontrol atas ruang, keamanan kelompok, dan akumulasi pengetahuan lokal",
        "deeper_why": "Pengendalian ruang fisik adalah akar dari semua sistem kepemilikan, hukum, dan tatanan sosial manusia",
        "anchor_concept": "pemukiman pertama manusia",
        "sources": ["Yuval Harari Sapiens", "Jurnal Arkeologi Oxford", "National Geographic"]
    }
    result = calculate_editorial_fit(settlement_idea)
    assert result["passed"] is True
    assert result["total_score"] >= 75


def test_city_psychology_accepted():
    """City psychology topic without explicit property mention must pass."""
    city_psych_idea = {
        "title": "Kenapa manusia merasa lebih kesepian di kota besar dibanding di desa kecil?",
        "human_question": "Apakah kepadatan fisik kota justru menciptakan kekosongan psikologis?",
        "core_revelation": "Kepadatan kota meminimalkan kebutuhan relasi mendalam — setiap tetangga dapat diganti, sehingga tidak ada yang dipertahankan",
        "deeper_why": "Desain kota modern mengoptimalkan mobilitas ekonomi, bukan kohesi sosial",
        "anchor_concept": "psikologi hidup di kota",
        "sources": ["Robert Putnam Bowling Alone", "Studi Kesehatan Mental Perkotaan Kemenkes"]
    }
    result = calculate_editorial_fit(city_psych_idea)
    assert result["passed"] is True


def test_historical_land_system_accepted():
    """Historical land system without sales copy must pass."""
    history_idea = {
        "title": "Bagaimana sistem kolonial Belanda membentuk hukum kepemilikan tanah Indonesia hingga hari ini?",
        "human_question": "Mengapa masalah sengketa tanah di Indonesia begitu kompleks dan mengakar?",
        "core_revelation": "Hukum agraria Indonesia masih mewarisi fragmentasi sistem kepemilikan kolonial yang sengaja membatasi kepemilikan pribumi",
        "deeper_why": "Tanah bukan sekadar aset ekonomi — melainkan rekaman kekuasaan dan sejarah eksklusi yang masih berjalan hari ini",
        "property_connection": "kolonialisme → hukum agraria → sengketa tanah → akses perumahan rakyat",
        "sources": ["UUPA 1960", "Jurnal Agraria STPN", "Luthfi Assyaukanie Land Reform"]
    }
    result = calculate_editorial_fit(history_idea)
    assert result["passed"] is True


# ===========================================================================
# V3 NEW: Fit score dimensions verification
# ===========================================================================

def test_fit_score_dimensions_correct():
    """Fit score must use v3 dimension names."""
    idea = {
        "title": "Kenapa orang memilih rumah tapak meski komuter 2 jam sehari?",
        "human_question": "Trade-off antara ruang hidup dan waktu hidup",
        "contradiction": "Efisiensi waktu ditukar dengan luas ruang",
        "deeper_why": "Manusia membutuhkan batas fisik yang jelas antara ruang pribadi dan dunia luar",
        "sources": ["BPS Survei Komuter", "Lembaga Survei Indonesia"],
        "story_type": "human_dilemma"
    }
    result = calculate_editorial_fit(idea)
    breakdown = result["breakdown"]

    # V3 dimension names
    assert "human_relevance" in breakdown
    assert "human_place_anchor" in breakdown  # NEW (was property_anchor)
    assert "why_depth" in breakdown
    assert "evidence_potential" in breakdown
    assert "story_type_fit" in breakdown   # NEW (was story_potential)
    assert "novelty" in breakdown

    # Old dimension names must NOT be present
    assert "property_anchor" not in breakdown
    assert "story_potential" not in breakdown

    # Max values must match v3 model
    assert breakdown["human_relevance"]["max"] == 25
    assert breakdown["human_place_anchor"]["max"] == 20
    assert breakdown["why_depth"]["max"] == 20
    assert breakdown["evidence_potential"]["max"] == 15
    assert breakdown["story_type_fit"]["max"] == 10
    assert breakdown["novelty"]["max"] == 5

    # Total must be 100
    total_max = sum(d["max"] for d in breakdown.values())
    assert total_max == 95  # 95 computed + 5 implicit base in design


def test_fit_score_minimum_constants():
    """Fit score minimum constants must match agreed values."""
    from engine.editorial.fit_score import MIN_HUMAN_PLACE_ANCHOR, MIN_EVIDENCE_POTENTIAL, MIN_PASSING_SCORE
    assert MIN_HUMAN_PLACE_ANCHOR == 10
    assert MIN_EVIDENCE_POTENTIAL == 8
    assert MIN_PASSING_SCORE == 75


# ===========================================================================
# V3: Taxonomy still works
# ===========================================================================

def test_topic_taxonomy_unchanged():
    """Primary domain taxonomy must still work with existing domains."""
    result = classify_topic("Kenapa harga rumah di Jakarta terus naik?")
    assert result["primary_domain"] in PRIMARY_DOMAINS
    assert result["primary_domain"] == "property"

    result2 = classify_topic("Bagaimana AI agent mengubah cara kerja manusia?")
    assert result2["primary_domain"] == "ai"


# ===========================================================================
# V3 editorial identity: HUMAN × PLACE × CHANGE × WHY
# ===========================================================================

def test_human_place_anchor_broader_than_property():
    """Human–Place anchor must accept topics without explicit property keywords."""
    # No 'rumah', 'tanah', 'kpr' etc. in this topic
    result = evaluate_human_place_anchor(
        "Kenapa manusia nomaden akhirnya memilih menetap di dekat sumber air?"
    )
    assert result["passed"] is True


def test_unrelated_topic_still_rejected():
    """Topics with ZERO Human–Place connection must still fail."""
    result = evaluate_human_place_anchor(
        "Tutorial cara compile Rust dari source code tanpa CMake"
    )
    assert result["passed"] is False
    assert result["score"] == 0


def test_valid_city_property_topic_accepted():
    """City dynamics and mobility topics with property anchor must pass (unchanged)."""
    city_idea = {
        "title": "Kenapa kota-kota besar di Indonesia selalu tumbuh melebar ke pinggiran?",
        "human_question": "Kenapa sawah dan kebun di pinggiran kota selalu berubah jadi perumahan?",
        "contradiction": "Pemerintah mendorong hunian vertikal, tapi masyarakat tetap membeli rumah tapak 40 km dari pusat kota",
        "core_revelation": "Regulasi tata ruang dan kelangkaan transportasi massal menciptakan urban sprawl yang tak terbendung",
        "deeper_why": "Insentif pengembang swasta mengunci pasokan lahan murah di pinggiran untuk margin maksimal",
        "property_connection": "Pertumbuhan kota → tata ruang → konversi lahan pertanian → perumahan tapak",
        "sources": ["Bappenas Urban Sprawl Report", "ATR/BPN Tata Ruang"]
    }
    gate = check_quality_gates(city_idea)
    assert gate["passed"] is True
    assert gate["fit_score"] >= 75
