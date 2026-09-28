"""
Editorial Quality Gate & Hard Rejection Rules Engine v2
"""
import re
from typing import List, Dict, Any, Union

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

HARD_REJECTION_PATTERNS = {
    "generic_ai_tools": [
        r"5 ai tools (gratis|terbaik)",
        r"10 tools ai",
        r"tools ai wajib kamu coba",
        r"prompt rahasia chatgpt"
    ],
    "property_listing_sales": [
        r"dijual (rumah|cluster|ruko) murah",
        r"tipe \d+/\d+ cicilan hanya",
        r"promo developer (dp|diskon)",
        r"hubungi marketing gallery",
        r"booking fee hanya",
        r"siap huni sertifikat hak milik"
    ],
    "forced_cta": [
        r"follow akun ini",
        r"jangan lupa like dan subscribe",
        r"klik link di bio",
        r"ketik (['\"])?mau(['\"])? di komentar",
        r"share ke teman kamu biar pintar"
    ]
}


def check_anti_patterns(text: str) -> List[str]:
    """Scans text for forbidden anti-patterns and returns any detected violations."""
    lower_text = text.lower()
    violations = []
    for pattern in FORBIDDEN_ANTI_PATTERNS:
        if pattern in lower_text:
            violations.append(pattern)
    return violations


def check_hard_rejections(content: Union[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Checks for violations against the 12 Hard Rejection Rules.
    """
    if isinstance(content, dict):
        text = " ".join(str(v) for v in content.values()).lower()
    else:
        text = str(content).lower()

    violations = []

    # 1. Generic AI tools list
    for p in HARD_REJECTION_PATTERNS["generic_ai_tools"]:
        if re.search(p, text):
            violations.append({
                "rule": "RULE 1: Generic AI Tools List",
                "pattern": p,
                "reason": "Topik berisi daftar alat AI generik tanpa relevansi eksistensial / ruang fisik"
            })

    # 2. Property listing / Sales copy
    for p in HARD_REJECTION_PATTERNS["property_listing_sales"]:
        if re.search(p, text):
            violations.append({
                "rule": "RULE 2 & 3: Property Listing / Sales Copy",
                "pattern": p,
                "reason": "Konten menyerupai brosur penjualan properti atau promosi cicilan komersial"
            })

    # 3. Forced Call-to-Action
    for p in HARD_REJECTION_PATTERNS["forced_cta"]:
        if re.search(p, text):
            violations.append({
                "rule": "RULE 8: Forced Call-To-Action",
                "pattern": p,
                "reason": "Menggunakan ajakan bertindak dangkal / memaksa follow / komentar artifisial"
            })

    # 4. Anti-patterns
    anti_hits = check_anti_patterns(text)
    for hit in anti_hits:
        violations.append({
            "rule": "FORBIDDEN ANTI-PATTERN",
            "pattern": hit,
            "reason": f"Ditemukan frasa klise robotik terlarang: '{hit}'"
        })

    return violations


def check_quality_gates(idea: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 8 Quality Gates verification for a given content idea.
    """
    violations = check_hard_rejections(idea)
    from engine.editorial.fit_score import calculate_editorial_fit
    fit_result = calculate_editorial_fit(idea)

    passed = (len(violations) == 0) and fit_result["passed"]

    return {
        "passed": passed,
        "fit_score": fit_result["total_score"],
        "fit_verdict": fit_result["verdict"],
        "hard_rejection_violations": violations,
        "fit_details": fit_result
    }
