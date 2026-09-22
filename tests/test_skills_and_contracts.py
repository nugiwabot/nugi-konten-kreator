import pytest


def validate_idea_contract(idea: dict) -> bool:
    """Validates that a generated idea complies with the Nugi Content Brain standard schema."""
    required_fields = [
        "title",
        "current_event",
        "why_interesting",
        "human_question",
        "contradiction",
        "core_insight",
        "potential_emotion",
        "conversation_potential",
        "shareability_rationale",
        "suggested_story_direction",
        "sources"
    ]
    for field in required_fields:
        if field not in idea or not str(idea[field]).strip():
            return False
    return True


def validate_script_structure(script: str) -> bool:
    """Validates that a talking-head script adheres to the mandatory 6-stage progression."""
    stages = ["HOOK", "TENSION", "CONTEXT", "REVELATION", "OPEN QUESTION"]
    for stage in stages:
        if stage not in script.upper():
            return False
    return True


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
    
    # Missing contradiction should fail contract
    invalid_idea = dict(sample_valid_idea)
    del invalid_idea["contradiction"]
    assert validate_idea_contract(invalid_idea) is False


def test_script_structure_validation():
    valid_script = """
    [00:00 - 00:05] HOOK: Pernah sadar nggak...
    [00:05 - 00:18] TENSION: Ada sesuatu yang aneh...
    [00:18 - 00:40] CONTEXT & REALITY: Data terbaru menunjukkan...
    [00:40 - 00:65] THE REVELATION: Jadi masalah sebenarnya bukan X tapi Y...
    [00:65 - 00:75] OPEN QUESTION: Kalau begitu pertanyaannya untuk kita...
    """
    assert validate_script_structure(valid_script) is True
    
    # Script missing open question should fail
    invalid_script = "HOOK: Hai guys... CONTEXT: Ini berita baru... REVELATION: Selesai."
    assert validate_script_structure(invalid_script) is False
