"""
Tests for Revelation Engine v1.
Verifies revelation quality checking and template generation.
"""
import pytest
from engine.editorial.revelation_engine import (
    check_revelation_quality,
    generate_revelation_template,
    evaluate_revelation,
    FORBIDDEN_REVELATION_PHRASES,
    REVELATION_ARCHETYPES
)


# ===========================================================================
# Quality check: forbidden phrases must fail
# ===========================================================================

def test_generic_wisdom_fails():
    """Generic wisdom revelations must fail quality check."""
    bad_revelation = "Teknologi mengubah segalanya, dan kita harus beradaptasi dengan perubahan ini."
    result = check_revelation_quality(bad_revelation)
    assert result["passed"] is False
    assert len(result["issues"]) > 0


def test_di_era_digital_fails():
    """AI cliché 'di era digital yang serba cepat' must be rejected."""
    bad_revelation = "Di era digital yang serba cepat ini, kita harus bergerak lebih cepat."
    result = check_revelation_quality(bad_revelation)
    assert result["passed"] is False
    assert any("di era digital" in issue.lower() for issue in result["issues"])


def test_too_short_fails():
    """Short one-liner revelations must fail (insufficient substance)."""
    too_short = "Rumah itu penting."
    result = check_revelation_quality(too_short)
    assert result["passed"] is False


def test_kesimpulannya_fails():
    """Mechanical conclusion phrases must be detected."""
    bad = "Kesimpulannya adalah kita harus lebih bijak dalam membeli rumah."
    result = check_revelation_quality(bad)
    assert result["passed"] is False


# ===========================================================================
# Quality check: good revelations must pass
# ===========================================================================

def test_specific_causal_revelation_passes():
    """Specific, causal, evidence-based revelations must pass."""
    good_revelation = (
        "Harga tanah naik bukan karena permintaan alami — tapi karena regulasi perizinan "
        "yang menyempitkan pasokan lahan legal secara artifisial. Selama sistem insentif "
        "pajak tanah mendorong spekulasi ketimbang pengembangan, disparitas ini akan "
        "terus melebar. BPS 2025 menunjukkan 67% kenaikan harga tanah terjadi di kawasan "
        "yang berdekatan dengan proyek infrastruktur pemerintah — bukan di kawasan permintaan organik."
    )
    result = check_revelation_quality(good_revelation)
    assert result["passed"] is True
    assert result["quality_score"] >= 7
    assert result["has_specificity"] is True


def test_human_psychological_revelation_passes():
    """Psychologically-grounded revelations with human specificity must pass."""
    good_revelation = (
        "Kerinduan manusia akan rumah sendiri bukan tentang investasi properti — "
        "melainkan tentang satu-satunya ruang di dunia yang tidak bisa diambil "
        "oleh algoritma, pecat oleh perusahaan, atau dihapus oleh pembaruan sistem. "
        "Inilah kenapa generasi Z yang fasih digital justru memiliki kerinduan "
        "terdalam terhadap tanah fisik."
    )
    result = check_revelation_quality(good_revelation)
    assert result["passed"] is True
    assert result["has_causality"] is True


# ===========================================================================
# Template generation
# ===========================================================================

def test_template_generated_for_all_story_types():
    """All story types must have a revelation template."""
    for story_type in REVELATION_ARCHETYPES:
        template = generate_revelation_template(
            story_type=story_type,
            topic="Test topic",
            anchor_concept="housing"
        )
        assert "template" in template
        assert "quality_markers" in template
        assert "guidance" in template
        assert len(template["guidance"]["do"]) >= 2
        assert len(template["guidance"]["dont"]) >= 2


def test_template_has_examples_of_good_revelations():
    """Templates must include concrete examples of good revelations."""
    template = generate_revelation_template(
        story_type="contradiction",
        topic="AI vs harga rumah",
        anchor_concept="housing"
    )
    examples = template["guidance"].get("examples_of_good_revelations", [])
    assert len(examples) >= 1


def test_causal_chain_included_in_template():
    """Causal chain should be included if provided."""
    causal_chain = [
        "AI Agents",
        "Fleksibilitas Lokasi Kerja",
        "Pergeseran Kebutuhan Hunian",
        "Reorganisasi Geografi Kota"
    ]
    template = generate_revelation_template(
        story_type="future",
        topic="AI dan geografi kota",
        anchor_concept="mobility",
        causal_chain=causal_chain
    )
    chain_text = template.get("causal_chain", "")
    assert "AI Agents" in chain_text
    assert "→" in chain_text


# ===========================================================================
# Evaluation
# ===========================================================================

def test_evaluate_revelation_bad():
    """Evaluation of bad revelation must return NEEDS REVISION."""
    bad = "Teknologi mengubah segalanya. Kita harus beradaptasi."
    result = evaluate_revelation(bad, story_type="future")
    assert result["final_verdict"] == "NEEDS REVISION"


def test_evaluate_revelation_good():
    """Evaluation of good revelation must return APPROVED."""
    good = (
        "Jika AI terus menggantikan pekerjaan kognitif di kantor, "
        "maka pada 2030 kota-kota satelit dalam radius 60 km dari Jakarta "
        "akan mengalami kenaikan nilai lahan 3x lebih cepat dari pusat kota — "
        "bukan karena infrastruktur, tapi karena kebutuhan ruang hidup yang lebih besar "
        "dari pekerja yang tidak perlu lagi komuter setiap hari. "
        "Survei McKinsey 2024 sudah menunjukkan tanda-tanda pertama pergeseran ini."
    )
    result = evaluate_revelation(good, story_type="future")
    assert result["final_verdict"] == "APPROVED"


# ===========================================================================
# Data integrity
# ===========================================================================

def test_all_forbidden_phrases_are_strings():
    """All forbidden phrases must be strings."""
    for phrase in FORBIDDEN_REVELATION_PHRASES:
        assert isinstance(phrase, str)
        assert len(phrase) >= 5


def test_revelation_archetypes_structure():
    """All archetypes must have required fields."""
    for story_type, archetype in REVELATION_ARCHETYPES.items():
        assert "prompt_template" in archetype, f"Missing prompt_template for {story_type}"
        assert "quality_markers" in archetype, f"Missing quality_markers for {story_type}"
        assert len(archetype["quality_markers"]) >= 2
