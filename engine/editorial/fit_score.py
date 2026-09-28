"""
Editorial Fit Score Engine v2
Calculates the 100-point editorial fit score across the 6 weighted dimensions.
"""
from typing import Dict, Any, Optional
from engine.editorial.property_bridge import evaluate_property_anchor

DIMENSION_WEIGHTS = {
    "human_relevance": 25,
    "property_anchor": 20,
    "why_depth": 20,
    "evidence_potential": 15,
    "novelty": 10,
    "story_potential": 10
}

MIN_PASSING_SCORE = 75
MIN_PROPERTY_ANCHOR = 10
MIN_EVIDENCE_POTENTIAL = 8


def calculate_editorial_fit(idea: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes the 100-point Internal Editorial Fit Score.
    
    Expected input keys (or heuristic fallbacks):
    - title / human_question
    - contradiction
    - core_revelation / deeper_why
    - sources / evidence_needed
    - property_connection / anchor
    """
    title = str(idea.get("title", ""))
    text_corpus = (
        title + " " +
        str(idea.get("human_question", "")) + " " +
        str(idea.get("contradiction", "")) + " " +
        str(idea.get("core_revelation", idea.get("core_insight", ""))) + " " +
        str(idea.get("deeper_why", "")) + " " +
        str(idea.get("property_connection", ""))
    ).lower()

    # 1. Human Relevance (Max 25)
    # Evaluates direct connection to human life, emotions, family, work, money
    hr_score = 15  # baseline
    if any(k in text_corpus for k in ["hidup", "manusia", "gaji", "keluarga", "kerja", "tidur", "cemas", "rasa aman"]):
        hr_score += 6
    if any(k in text_corpus for k in ["anak muda", "generasi", "pekerja", "rumah tangga"]):
        hr_score += 4
    hr_score = min(25, hr_score)

    # 2. Property / Life Anchor (Max 20)
    anchor_eval = evaluate_property_anchor(title, text_corpus)
    anchor_score = anchor_eval["score"]

    # 3. WHY Depth (Max 20)
    # Checks depth from Level 3 to Level 5
    why_score = 10  # baseline
    if idea.get("deeper_why") or "akar" in text_corpus or "sistem" in text_corpus or "struktur" in text_corpus:
        why_score += 6
    if "psikologi" in text_corpus or "insentif" in text_corpus or "kebiasaan" in text_corpus or "purba" in text_corpus:
        why_score += 4
    why_score = min(20, why_score)

    # 4. Evidence Potential (Max 15)
    sources = idea.get("sources", idea.get("source_candidates", []))
    ev_score = 8  # baseline
    if sources and len(sources) >= 1:
        ev_score += 4
    if any(k in str(sources).lower() for k in ["bps", "bank indonesia", "world bank", "stanford", "jurnal", "laporan"]):
        ev_score += 3
    ev_score = min(15, ev_score)

    # 5. Novelty / Uniqueness (Max 10)
    nov_score = 6  # baseline
    if idea.get("contradiction") or "padahal" in text_corpus or "bukan" in text_corpus:
        nov_score += 4
    nov_score = min(10, nov_score)

    # 6. Story Potential (Max 10)
    story_score = 6  # baseline
    if idea.get("story_structure") or idea.get("suggested_story_direction"):
        story_score += 4
    story_score = min(10, story_score)

    # Total Score
    total_score = hr_score + anchor_score + why_score + ev_score + nov_score + story_score

    # Determine Gate Status
    reasons = []
    passed = True

    if anchor_score < MIN_PROPERTY_ANCHOR:
        passed = False
        reasons.append(f"Property / Life Anchor ({anchor_score}/20) di bawah ambang minimal {MIN_PROPERTY_ANCHOR}/20.")

    if ev_score < MIN_EVIDENCE_POTENTIAL:
        passed = False
        reasons.append(f"Evidence Potential ({ev_score}/15) di bawah ambang minimal {MIN_EVIDENCE_POTENTIAL}/15. Wajib riset sebelum naskah.")

    if total_score < MIN_PASSING_SCORE:
        passed = False
        reasons.append(f"Total Fit Score ({total_score}/100) di bawah ambang kelayakan {MIN_PASSING_SCORE}/100.")

    if passed:
        verdict = "APPROVED"
    elif total_score >= 60 and anchor_score >= MIN_PROPERTY_ANCHOR:
        verdict = "REVISE"
    else:
        verdict = "REJECTED"

    return {
        "total_score": total_score,
        "verdict": verdict,
        "passed": passed,
        "breakdown": {
            "human_relevance": {"score": hr_score, "max": 25},
            "property_anchor": {"score": anchor_score, "max": 20},
            "why_depth": {"score": why_score, "max": 20},
            "evidence_potential": {"score": ev_score, "max": 15},
            "novelty": {"score": nov_score, "max": 10},
            "story_potential": {"score": story_score, "max": 10}
        },
        "reasons": reasons,
        "anchor_details": anchor_eval
    }
