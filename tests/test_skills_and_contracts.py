import pytest
from engine.editorial.story_type import get_script_structure


def validate_idea_contract(idea: dict) -> bool:
    """
    Validates that a generated idea complies with the Nugi Content Brain standard schema.
    In v3, contradiction is required ONLY if story_type is 'contradiction'.
    For other story types (origin, evolution, place, etc.), contradiction is optional.
    """
    base_required_fields = [
        "title",
        "current_event",
        "why_interesting",
        "human_question",
        "core_insight",
        "potential_emotion",
        "conversation_potential",
        "shareability_rationale",
        "suggested_story_direction",
        "sources"
    ]
    for field in base_required_fields:
        if field not in idea or not str(idea[field]).strip():
            return False

    story_type = str(idea.get("story_type", "")).lower()
    # Contradiction is required only for contradiction story type
    if story_type == "contradiction":
        if "contradiction" not in idea or not str(idea["contradiction"]).strip():
            return False
    elif not story_type:
        # Backward compatibility for legacy contracts without explicit story_type
        if "contradiction" not in idea or not str(idea["contradiction"]).strip():
            return False

    return True


def validate_script_structure(script: str, story_type: str = "contradiction") -> bool:
    """
    Validates that a script adheres to its Story Type dynamic stage progression.
    Contradiction / tension is required ONLY for contradiction story type.
    """
    script_upper = script.upper()
    if story_type == "contradiction":
        stages = ["HOOK", "TENSION", "CONTEXT", "REVELATION", "OPEN QUESTION"]
        return all(stage in script_upper for stage in stages)
    elif story_type == "origin":
        # Origin story: Hook/Observation, Question, Context/Turning Point, Revelation, Reflection
        stages = ["OBSERVATION", "QUESTION", "REVELATION", "REFLECTION"]
        # Allow HOOK as synonym for OBSERVATION, OPEN QUESTION as synonym for REFLECTION
        has_obs = "OBSERVATION" in script_upper or "HOOK" in script_upper
        has_q = "QUESTION" in script_upper
        has_rev = "REVELATION" in script_upper
        has_ref = "REFLECTION" in script_upper or "OPEN QUESTION" in script_upper
        return has_obs and has_q and has_rev and has_ref
    else:
        # General dynamic check based on get_script_structure
        structure = get_script_structure(story_type, "long")
        # Ensure revelation and reflection/question are present
        has_rev = "REVELATION" in script_upper
        has_ref = "REFLECTION" in script_upper or "OPEN QUESTION" in script_upper
        return has_rev and has_ref


def test_idea_contract_validation():
    sample_valid_idea = {
        "title": "Mengapa AI Tidak Pernah Membunuh Nilai Sebidang Tanah",
        "current_event": "Rilis data pergeseran investasi properti ke luar kota 2026",
        "why_interesting": "Semakin komputasi melayang di awan, kebutuhan fisik tanah makin melonjak",
        "human_question": "Apakah kita sedang menuju dunia tanpa ruang pribadi?",
        "contradiction": "Pekerjaan digital tanpa batas, tapi tubuh fisik tetap butuh pijakan",
        "core_insight": "AI mempercepat pikiran, tetapi tanah menenangkan biologi manusia",
        "potential_emotion": "Awe and calm reflection",
        "conversation_potential": "Memantik diskusi apakah pekerja remote akan eksodus dari Jakarta",
        "shareability_rationale": "High social currency for remote workers and property seekers",
        "suggested_story_direction": "Observasi meja kerja -> data BPS -> pertanyaan penutup",
        "sources": ["BPS 2026", "Stanford AI Report"]
    }
    assert validate_idea_contract(sample_valid_idea) is True

    # Missing contradiction should fail when story_type == "contradiction" (or legacy untyped)
    invalid_contradiction_idea = dict(sample_valid_idea)
    invalid_contradiction_idea["story_type"] = "contradiction"
    del invalid_contradiction_idea["contradiction"]
    assert validate_idea_contract(invalid_contradiction_idea) is False

    # But non-contradiction story type (e.g. origin) does NOT require contradiction
    valid_origin_idea = dict(sample_valid_idea)
    valid_origin_idea["story_type"] = "origin"
    del valid_origin_idea["contradiction"]
    assert validate_idea_contract(valid_origin_idea) is True


def test_script_structure_validation():
    valid_script = """
    [00:00 - 00:05] HOOK: Pernah sadar nggak...
    [00:05 - 00:18] TENSION: Ada sesuatu yang aneh...
    [00:18 - 00:40] CONTEXT & REALITY: Data terbaru menunjukkan...
    [00:40 - 00:65] THE REVELATION: Jadi masalah sebenarnya bukan X tapi Y...
    [00:65 - 00:75] OPEN QUESTION: Kalau begitu pertanyaannya untuk kita...
    """
    assert validate_script_structure(valid_script, story_type="contradiction") is True

    # Script missing open question should fail
    invalid_script = "HOOK: Hai guys... CONTEXT: Ini berita baru... REVELATION: Selesai."
    assert validate_script_structure(invalid_script, story_type="contradiction") is False


def test_origin_script_structure_no_contradiction():
    """Origin script should pass without any tension or contradiction stage."""
    origin_script = """
    [00:00 - 00:05] OBSERVATION: Hampir semua kota besar dibangun di tepi sungai.
    [00:05 - 00:20] QUESTION: Tapi kapan dan kenapa manusia pertama kali memilih menetap di sana?
    [00:20 - 00:45] HISTORICAL CONTEXT: 10.000 tahun lalu di Hilal Subur...
    [00:45 - 00:70] THE REVELATION: Sungai bukan sekadar air minum, melainkan jalan raya purba.
    [00:70 - 00:85] REFLECTION: Jika mobilitas kita kini lewat serat optik, ke mana kota akan bergeser?
    """
    assert validate_script_structure(origin_script, story_type="origin") is True
    # Verify it does not contain TENSION or CONTRADICTION
    assert "TENSION" not in origin_script.upper()
    assert "CONTRADICTION" not in origin_script.upper()
