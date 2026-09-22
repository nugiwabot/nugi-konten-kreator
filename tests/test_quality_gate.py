import pytest


FORBIDDEN_ANTI_PATTERNS = [
    "di era digital yang serba cepat",
    "menyelami samudera",
    "revolusi tak terelakkan",
    "ketik mau di komentar",
    "ketik 'mau'",
    "jangan lupa follow",
    "follow untuk tips",
    "klik link di bio",
    "pasti cuan 100%",
    "dijamin kaya mendadak"
]


def check_anti_patterns(text: str) -> list:
    """Scans text for forbidden anti-patterns and returns any detected violations."""
    lower_text = text.lower()
    violations = []
    for pattern in FORBIDDEN_ANTI_PATTERNS:
        if pattern in lower_text:
            violations.append(pattern)
    return violations


def test_anti_pattern_detection():
    bad_script = "Halo semuanya, di era digital yang serba cepat ini kita harus adaptif. Jangan lupa follow akun ini ya!"
    violations = check_anti_patterns(bad_script)
    assert len(violations) == 2
    assert "di era digital yang serba cepat" in violations
    assert "jangan lupa follow" in violations


def test_clean_nugi_voice():
    good_script = """
    Pernah sadar nggak, kenapa semakin canggih AI di kantor kita, jam kerja kita justru rasanya makin berantakan?
    Secara logika, kalau mesin menyelesaikan tugas 2 jam jadi 2 menit, kita harusnya punya waktu luang lebih banyak.
    Tapi survei minggu ini membuktikan sebaliknya.
    Masalah sebenarnya bukan pada mesinnya, melainkan bagaimana kita mengukur nilai diri kita sendiri.
    Menurut Anda, apa satu hal yang Anda miliki yang tidak akan pernah bisa digantikan oleh algoritma?
    """
    violations = check_anti_patterns(good_script)
    assert len(violations) == 0
