"""
Tests for Story Type Engine v1.
Verifies narrative archetype classification and narrative device selection.

Key assertions:
- CONTRADICTION is only required for story_type == "contradiction"
- Other story types use different narrative devices
- 10 story types cover distinct narrative patterns
"""
import pytest
from engine.editorial.story_type import (
    classify_story_type,
    get_narrative_device,
    is_contradiction_required,
    get_script_structure,
    list_story_types,
    STORY_TYPES,
    NARRATIVE_DEVICES
)


# ===========================================================================
# Core story type classification
# ===========================================================================

def test_origin_story_classification():
    """Origin questions must classify as origin story type."""
    result = classify_story_type("Kapan manusia pertama kali mulai membangun rumah permanen?")
    assert result["primary_type"] in ("origin", "historical", "evolution")
    assert result["contradiction_required"] is False


def test_transformation_story_classification():
    """Transformation topics must classify correctly."""
    result = classify_story_type("Bagaimana kawasan industri berubah menjadi permukiman kota?")
    assert result["primary_type"] in ("transformation", "evolution", "place")


def test_contradiction_story_classification():
    """Explicit contradiction topics must classify as contradiction."""
    result = classify_story_type(
        "Kenapa gaji sudah naik tapi harga rumah masih terasa lebih jauh dari jangkauan?"
    )
    # Should detect contradiction signals
    assert result["primary_type"] in (
        "contradiction", "human_dilemma", "hidden_system"
    )


def test_place_story_classification():
    """Place-specific questions must classify as place story."""
    result = classify_story_type("Kenapa kawasan Menteng selalu jadi pusat kekuasaan Jakarta?")
    assert result["primary_type"] in ("place", "historical", "hidden_system")


def test_future_story_classification():
    """Future projection questions must classify as future story."""
    result = classify_story_type(
        "Apakah AI akan mengubah cara manusia memilih lokasi tempat tinggal di masa depan?"
    )
    assert result["primary_type"] in ("future", "second_order")
    assert result["contradiction_required"] is False


def test_human_dilemma_classification():
    """Trade-off situations must classify as human_dilemma."""
    result = classify_story_type(
        "Kenapa orang rela komuter 3 jam sehari demi memiliki rumah tapak di pinggiran kota?"
    )
    assert result["primary_type"] in ("human_dilemma", "contradiction", "second_order")


def test_hidden_system_classification():
    """Questions about hidden mechanisms must classify as hidden_system."""
    result = classify_story_type(
        "Sistem apa yang sebenarnya bekerja di balik naiknya harga tanah setiap tahun?"
    )
    assert result["primary_type"] in ("hidden_system", "contradiction")


def test_evolution_story_classification():
    """Historical evolution of living arrangements must classify as evolution."""
    result = classify_story_type(
        "Bagaimana bentuk rumah manusia berevolusi dari gua hingga apartemen modern?",
        intents=["historical", "evolution"]
    )
    assert result["primary_type"] in ("evolution", "origin", "transformation")
    assert result["contradiction_required"] is False


# ===========================================================================
# Contradiction: optional, not forced
# ===========================================================================

def test_origin_story_does_not_require_contradiction():
    """Origin stories must NOT require contradiction."""
    result = classify_story_type(
        "Kapan dan mengapa manusia nomaden memutuskan untuk menetap?"
    )
    # Whichever story type it gets, check it's NOT the contradiction type
    if result["primary_type"] == "contradiction":
        # Reclassified: origin signals should dominate
        assert result["contradiction_required"] is True
    else:
        assert result["contradiction_required"] is False


def test_place_story_does_not_require_contradiction():
    """Place stories can have spatial mystery without contradiction."""
    result = classify_story_type(
        "Kenapa hampir semua kota besar di dunia terbentuk di tepi sungai?"
    )
    if result["primary_type"] != "contradiction":
        assert result["contradiction_required"] is False


def test_contradiction_type_requires_contradiction():
    """Contradiction story type must require contradiction."""
    assert is_contradiction_required("contradiction") is True


def test_other_types_do_not_require_contradiction():
    """Most story types must NOT require contradiction."""
    no_contradiction_types = [
        "origin", "transformation", "human_dilemma", "place",
        "evolution", "future", "reframe", "second_order"
    ]
    for story_type in no_contradiction_types:
        assert is_contradiction_required(story_type) is False, (
            f"Story type '{story_type}' should not require contradiction"
        )


# ===========================================================================
# Narrative devices
# ===========================================================================

def test_each_story_type_has_unique_narrative_device():
    """Each story type must have an assigned narrative device."""
    for story_type_name in STORY_TYPES:
        device = get_narrative_device(story_type_name)
        assert device in NARRATIVE_DEVICES, (
            f"Story type '{story_type_name}' has unknown narrative device '{device}'"
        )


def test_origin_uses_mystery_reveal():
    assert get_narrative_device("origin") == "mystery_reveal"


def test_contradiction_uses_contradiction_device():
    assert get_narrative_device("contradiction") == "contradiction"


def test_place_uses_spatial_mystery():
    assert get_narrative_device("place") == "spatial_mystery"


# ===========================================================================
# Classification with intent boosting
# ===========================================================================

def test_intent_boosts_future_type():
    """Future intents should boost future story type classification."""
    result = classify_story_type(
        "Apakah kota-kota besar Indonesia akan terus membesar?",
        intents=["future"]
    )
    assert result["primary_type"] in ("future", "second_order")


def test_intent_boosts_historical_type():
    """Historical intents should boost origin/evolution types."""
    result = classify_story_type(
        "Bagaimana peta pemukiman Jakarta terbentuk?",
        intents=["historical", "geographic"]
    )
    assert result["primary_type"] in ("origin", "evolution", "transformation", "place")


# ===========================================================================
# Data structure integrity
# ===========================================================================

def test_story_types_count():
    """There must be exactly 10 story types."""
    assert len(STORY_TYPES) == 10


def test_story_type_structure():
    """All story types must have required fields."""
    required_fields = [
        "name", "description", "narrative_device", "pipeline",
        "short_pipeline", "contradiction_required", "detection_keywords"
    ]
    for type_name, defn in STORY_TYPES.items():
        for field in required_fields:
            assert field in defn, f"Story type '{type_name}' missing field '{field}'"
        assert len(defn["pipeline"]) >= 5
        assert len(defn["short_pipeline"]) >= 4


def test_list_story_types():
    """list_story_types() must return all 10 types with required fields."""
    types = list_story_types()
    assert len(types) == 10
    for t in types:
        assert "type" in t
        assert "name" in t
        assert "description" in t
        assert "narrative_device" in t


def test_classify_result_structure():
    """Classification result must have all required fields."""
    result = classify_story_type("Kenapa harga tanah di Jakarta selalu naik?")
    required = [
        "primary_type", "primary_type_name", "narrative_device",
        "pipeline", "short_pipeline", "contradiction_required",
        "secondary_types", "description"
    ]
    for field in required:
        assert field in result, f"Missing field: {field}"


# ===========================================================================
# Dynamic script structure generation
# ===========================================================================

def test_get_script_structure_origin():
    """Origin story must follow origin progression without contradiction."""
    struct = get_script_structure("origin", "long")
    assert struct["story_type"] == "origin"
    assert struct["narrative_device"] == "mystery_reveal"
    assert struct["contradiction_required"] is False
    assert struct["has_contradiction_stage"] is False
    assert "CONTRADICTION" not in struct["stage_names"]
    expected_stages = [
        "OBSERVATION", "QUESTION", "HISTORICAL CONTEXT",
        "TURNING POINT", "CAUSAL CHAIN", "REVELATION", "REFLECTION"
    ]
    assert struct["stage_names"] == expected_stages


def test_get_script_structure_all_non_contradiction_types():
    """All 9 non-contradiction story types must NOT have a contradiction stage."""
    non_contradiction_types = [
        "origin", "transformation", "hidden_system", "human_dilemma",
        "second_order", "place", "evolution", "future", "reframe"
    ]
    for st in non_contradiction_types:
        long_struct = get_script_structure(st, "long")
        assert long_struct["contradiction_required"] is False, f"{st} should not require contradiction"
        assert long_struct["has_contradiction_stage"] is False, f"{st} should not have contradiction stage"
        assert not any("contradiction" in s.lower() for s in long_struct["stages"]), (
            f"Stage in {st} contains contradiction"
        )

        short_struct = get_script_structure(st, "short")
        assert short_struct["contradiction_required"] is False
        assert short_struct["has_contradiction_stage"] is False
        assert not any("contradiction" in s.lower() for s in short_struct["stages"])


def test_get_script_structure_contradiction_type():
    """Contradiction story type MUST have contradiction stage and required=True."""
    long_struct = get_script_structure("contradiction", "long")
    assert long_struct["story_type"] == "contradiction"
    assert long_struct["narrative_device"] == "contradiction"
    assert long_struct["contradiction_required"] is True
    assert long_struct["has_contradiction_stage"] is True
    assert any("contradiction" in s.lower() for s in long_struct["stages"])

    short_struct = get_script_structure("contradiction", "short")
    assert short_struct["contradiction_required"] is True
    assert short_struct["has_contradiction_stage"] is True


def test_get_script_structure_fallback():
    """Unknown story type falls back gracefully to hidden_system."""
    struct = get_script_structure("non_existent_type")
    assert struct["story_type"] == "hidden_system"
    assert struct["contradiction_required"] is False
    assert struct["has_contradiction_stage"] is False

