"""
Tests for Property Bridge Engine v2.
Verifies causal chains from general topics to space, property, housing, and cities.
"""
import pytest
from engine.editorial.property_bridge import find_property_bridge, evaluate_property_anchor


def test_ai_agents_causal_bridge():
    """AI agents topic must bridge to office demand, geography, and housing."""
    bridge = find_property_bridge("AI agents dan otomatisasi tugas administrasi perkantoran")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert len(bridge["chain"]) >= 3
    assert bridge["anchor"] == "housing"
    assert any("Pengurangan Kebutuhan Meja Kantor" in step for step in bridge["chain"])


def test_fertility_decline_causal_bridge():
    """Fertility decline must bridge to household size, typology, and property market."""
    bridge = find_property_bridge("Penurunan angka kelahiran dan krisis demografi keluarga muda")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert len(bridge["chain"]) >= 4
    assert any("Household Size" in step for step in bridge["chain"])


def test_remote_work_causal_bridge():
    """Remote work must bridge to commuting, home office specs, and suburban demand."""
    bridge = find_property_bridge("Tren remote work dan WFH permanen bagi engineer")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert bridge["anchor"] == "work"
    assert any("Desentralisasi" in step or "Komuter" in step for step in bridge["chain"])


def test_electric_vehicles_causal_bridge():
    """EV transition must bridge to home charging, electrical limits, and parking space value."""
    bridge = find_property_bridge("Adopsi kendaraan listrik dan mobil listrik di pemukiman")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert any("Home Charging" in step for step in bridge["chain"])


def test_transit_traffic_causal_bridge():
    """Traffic and MRT/LRT expansion must bridge to land value around transit."""
    bridge = find_property_bridge("Kemacetan jalan tol dan ekspansi jalur MRT stasiun baru")
    assert bridge["valid"] is True
    assert bridge["is_cosmetic"] is False
    assert bridge["anchor"] == "mobility"
    assert any("Radius Stasiun Transit" in step or "TOD" in step for step in bridge["chain"])


def test_cosmetic_bridge_rejection():
    """Cosmetic and gimmick bridges must be flagged and rejected."""
    cosmetic_topic = "5 tools gratis dan trik cepat kaya beli rumah tanpa modal"
    bridge = find_property_bridge(cosmetic_topic)
    assert bridge["valid"] is False
    assert bridge["is_cosmetic"] is True

    anchor_eval = evaluate_property_anchor(cosmetic_topic)
    assert anchor_eval["passed"] is False
    assert anchor_eval["score"] == 0
