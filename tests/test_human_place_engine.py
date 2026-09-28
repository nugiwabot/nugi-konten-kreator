"""
Tests for Human–Place Engine v3.
Verifies the 10-criterion Human–Place Anchor Test.

CHANGES FROM property_bridge tests:
- No longer requires explicit property/land/housing keywords
- Tests for psychological, historical, urban, and technological Human–Place connections
- Property connections are tested as valid but not mandatory
"""
import pytest
from engine.editorial.human_place_engine import (
    find_human_place_bridge,
    evaluate_human_place_anchor,
    evaluate_human_place_criteria,
    HUMAN_PLACE_CRITERIA,
    CANONICAL_HUMAN_PLACE_BRIDGES,
    # Backward compat
    find_property_bridge,
    evaluate_property_anchor
)


# ===========================================================================
# Canonical bridges (direct)
# ===========================================================================

def test_ai_agents_human_place_bridge():
    """AI agents must bridge to reorganization of human living geography."""
    bridge = find_human_place_bridge("AI agents dan otomatisasi tugas administrasi perkantoran")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert len(bridge["chain"]) >= 3
    assert bridge.get("place_relation") in [
        "technology_changes_living_space", "home_work_movement"
    ]


def test_fertility_decline_human_place_bridge():
    """Fertility decline must bridge to household typology and housing market."""
    bridge = find_human_place_bridge("Penurunan angka kelahiran dan krisis demografi keluarga muda")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert len(bridge["chain"]) >= 3


def test_remote_work_human_place_bridge():
    """Remote work must bridge to home, commuting, and urban geography."""
    bridge = find_human_place_bridge("Tren remote work dan WFH permanen bagi engineer")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert bridge.get("place_relation") == "home_work_movement"


def test_electric_vehicles_human_place_bridge():
    """EV adoption must bridge to home infrastructure requirements."""
    bridge = find_human_place_bridge("Adopsi kendaraan listrik dan mobil listrik di pemukiman")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False


def test_transit_traffic_human_place_bridge():
    """Traffic and MRT must bridge to urban mobility and land value."""
    bridge = find_human_place_bridge("Kemacetan jalan tol dan ekspansi jalur MRT stasiun baru")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert bridge.get("place_relation") == "home_work_movement"


# ===========================================================================
# New: Human–Place bridges WITHOUT explicit property keywords
# ===========================================================================

def test_historical_city_formation_bridge():
    """Colonial history must bridge to how cities and spaces were formed."""
    bridge = find_human_place_bridge("Bagaimana Batavia colonial membentuk pusat Jakarta modern")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False


def test_psychology_home_bridge():
    """Psychological need for security must bridge to home/place relationship."""
    bridge = find_human_place_bridge(
        "Kenapa manusia begitu cemas ketika tidak memiliki tempat tinggal tetap"
    )
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert bridge.get("place_relation") in ["psychology_and_home", "where_humans_live"]


def test_urbanization_bridge():
    """Urban growth and city formation topics must pass."""
    bridge = find_human_place_bridge(
        "Kenapa kota-kota di Indonesia selalu tumbuh melebar ke pinggiran"
    )
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False


def test_nomadic_to_settled_origin_story():
    """Evolution from nomadic to settled life must pass — no property keyword needed."""
    bridge = find_human_place_bridge(
        "Kapan manusia pertama kali mulai menetap dan tidak lagi nomaden"
    )
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False


def test_economics_land_access_bridge():
    """Economic access to space must bridge to Human–Place anchor."""
    bridge = find_human_place_bridge(
        "Kenapa harga tanah naik jauh lebih cepat dari kenaikan gaji rata-rata"
    )
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False


# ===========================================================================
# Hard rejections (cosmetic/spam/sales)
# ===========================================================================

def test_cosmetic_bridge_rejected():
    """Cosmetic AI tools list with forced property mention must be rejected."""
    bridge = find_human_place_bridge("5 tools gratis dan trik cepat kaya beli rumah tanpa modal")
    assert bridge["valid"] is False
    assert bridge["is_cosmetic"] is True


def test_property_listing_rejected():
    """Direct property sales listing must be rejected as spam."""
    bridge = find_human_place_bridge("Dijual rumah murah tipe 36/72 cicilan hanya 2 juta per bulan")
    assert bridge["valid"] is False
    assert bridge["is_cosmetic"] is True


def test_completely_unrelated_rejected():
    """Topic with zero Human–Place connection must be rejected."""
    bridge = find_human_place_bridge(
        "Cara menginstall driver VGA NVIDIA di Linux Ubuntu"
    )
    assert bridge["valid"] is False


# ===========================================================================
# Anchor evaluation (10-criterion test)
# ===========================================================================

def test_anchor_evaluation_strong_pass():
    """Strong Human–Place topic must score high on anchor test."""
    result = evaluate_human_place_anchor(
        "Kenapa manusia rela berutang 20 tahun demi memiliki sepetak rumah?",
        "Rasa aman, psikologi, kepemilikan, hunian, keluarga"
    )
    assert result["passed"] is True
    assert result["score"] >= 12


def test_anchor_evaluation_weak_fail():
    """Topic with no HP connection must fail anchor test."""
    result = evaluate_human_place_anchor(
        "Tutorial cara compile Rust dari source",
        "cargo build release flags"
    )
    assert result["passed"] is False
    assert result["score"] == 0


def test_anchor_evaluation_multiple_criteria():
    """Multi-criterion HP topics should match multiple criteria."""
    criteria = evaluate_human_place_criteria(
        "kemacetan kota transportasi komuter rumah kantor mobilitas urban"
    )
    assert len(criteria) >= 2
    criterion_names = [c["name"] for c in criteria]
    # Should match both mobility and urban criteria
    assert any(n in criterion_names for n in [
        "home_work_movement", "how_cities_are_shaped", "where_humans_live"
    ])


# ===========================================================================
# Backward compatibility
# ===========================================================================

def test_backward_compat_find_property_bridge():
    """find_property_bridge alias must still work."""
    bridge = find_property_bridge("AI agents dan remote work pergeseran hunian")
    assert bridge["valid"] is True
    assert "chain" in bridge
    # Also has old 'anchor' field for compat
    assert "anchor" in bridge


def test_backward_compat_evaluate_property_anchor():
    """evaluate_property_anchor alias must still work."""
    result = evaluate_property_anchor("Kenapa harga rumah selalu naik?")
    assert "passed" in result
    assert "score" in result
    assert "verdict" in result


# ===========================================================================
# Data structure integrity
# ===========================================================================

def test_human_place_criteria_structure():
    """All 10 criteria must have required fields."""
    assert len(HUMAN_PLACE_CRITERIA) == 10
    for criterion in HUMAN_PLACE_CRITERIA:
        assert "id" in criterion
        assert "name" in criterion
        assert "description" in criterion
        assert "keywords" in criterion
        assert len(criterion["keywords"]) >= 5


def test_canonical_bridges_structure():
    """All canonical bridges must have required fields."""
    assert len(CANONICAL_HUMAN_PLACE_BRIDGES) >= 5
    for bridge in CANONICAL_HUMAN_PLACE_BRIDGES:
        assert "id" in bridge
        assert "pattern" in bridge
        assert "chain" in bridge
        assert len(bridge["chain"]) >= 3
        assert "place_relation" in bridge
