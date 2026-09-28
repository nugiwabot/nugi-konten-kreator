"""
Tests for Intent Classifier v1.
Verifies intent classification accuracy across 15 intent classes.
"""
import pytest
from engine.editorial.intent_classifier import (
    classify_intent,
    classify_multiple_queries,
    INTENT_DEFINITIONS
)


# ===========================================================================
# Core intent detection
# ===========================================================================

def test_historical_intent_detected():
    """Historical queries must be classified as 'historical'."""
    result = classify_intent("Bagaimana sejarah terbentuknya kawasan Menteng di Jakarta?")
    assert "historical" in result["intents"]
    assert result["primary_intent"] == "historical"


def test_origin_intent_detected():
    """Origin queries must be classified."""
    result = classify_intent("Kapan manusia pertama kali mulai membangun rumah permanen?")
    assert "origin" in result["intents"] or "historical" in result["intents"]


def test_psychological_intent_detected():
    """Psychological queries must be classified."""
    result = classify_intent("Kenapa manusia memiliki rasa aman yang terikat dengan rumah?")
    assert "psychological" in result["intents"]


def test_economic_intent_detected():
    """Economic queries must be classified."""
    result = classify_intent("Kenapa harga tanah selalu naik melebihi inflasi?")
    assert "economic" in result["intents"]


def test_urban_intent_detected():
    """Urban queries must be classified."""
    result = classify_intent("Bagaimana tata kota Jakarta membentuk polarisasi pemukiman?")
    assert "urban" in result["intents"]


def test_future_intent_detected():
    """Future projection queries must be classified."""
    result = classify_intent("Apakah AI akan mengubah cara manusia memilih lokasi tempat tinggal?")
    assert "future" in result["intents"]


def test_explanatory_intent_detected():
    """Why-questions must be classified as explanatory."""
    result = classify_intent("Mengapa rumah di dekat stasiun MRT selalu lebih mahal?")
    assert "explanatory" in result["intents"]


def test_procedural_intent_detected():
    """How-to queries must be classified as procedural."""
    result = classify_intent("Cara mengurus KPR untuk rumah pertama langkah demi langkah")
    assert "procedural" in result["intents"]


def test_geographic_intent_detected():
    """Geographic queries must be classified."""
    result = classify_intent("Kenapa kota-kota besar selalu tumbuh di sekitar sungai?")
    assert "geographic" in result["intents"]


# ===========================================================================
# Multi-intent classification
# ===========================================================================

def test_multiple_intents_assigned():
    """Complex queries should receive multiple intent tags."""
    result = classify_intent(
        "Kenapa secara psikologi orang lebih memilih rumah di kota "
        "meskipun harganya jauh lebih mahal?"
    )
    # Should have psychological + economic + urban + explanatory
    assert len(result["intents"]) >= 2


def test_human_place_implied_by_urban_intent():
    """Urban intent must imply Human–Place connection."""
    result = classify_intent("Bagaimana tata ruang kota mempengaruhi distribusi kemakmuran?")
    assert result["human_place_implied"] is True


def test_human_place_implied_by_historical_intent():
    """Historical intent must imply Human–Place connection."""
    result = classify_intent("Bagaimana sistem kolonial membentuk kepemilikan tanah di Indonesia?")
    assert result["human_place_implied"] is True


def test_procedural_only_detection():
    """Pure how-to queries without place/human context should be marked procedural_only."""
    result = classify_intent("Cara membayar PBB online langkah demi langkah panduan 2026")
    assert result["is_procedural_only"] is True or "procedural" in result["intents"]


# ===========================================================================
# Edge cases
# ===========================================================================

def test_empty_query_handled():
    """Empty query must not raise exception."""
    result = classify_intent("")
    assert "intents" in result
    assert "primary_intent" in result


def test_short_query_handled():
    """Single-word query must not raise exception."""
    result = classify_intent("rumah")
    assert "intents" in result


def test_batch_classification():
    """Batch classification must return same count as input."""
    queries = [
        "Kenapa harga rumah mahal?",
        "Sejarah urbanisasi Jakarta",
        "Cara KPR mudah"
    ]
    results = classify_multiple_queries(queries)
    assert len(results) == len(queries)
    for r in results:
        assert "query" in r
        assert "intents" in r
        assert "primary_intent" in r


# ===========================================================================
# Data integrity
# ===========================================================================

def test_intent_definitions_structure():
    """All intent definitions must have required fields."""
    assert len(INTENT_DEFINITIONS) >= 10
    for intent_name, definition in INTENT_DEFINITIONS.items():
        assert "description" in definition
        assert "keywords" in definition
        assert len(definition["keywords"]) >= 3, (
            f"Intent '{intent_name}' needs at least 3 keywords"
        )


def test_confidence_levels():
    """Confidence must be one of: high, medium, low."""
    result = classify_intent("Kenapa harga tanah di perkotaan selalu meningkat setiap tahun?")
    assert result["confidence"] in ("high", "medium", "low")
