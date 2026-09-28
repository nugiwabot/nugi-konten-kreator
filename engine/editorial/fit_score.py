"""
Editorial Fit Score Engine v3
Implements the new 6-dimension scoring model (100 points total):

  Human Relevance      25 pts  — Connection to human life, emotion, daily experience
  Human–Place Anchor   20 pts  — Connection to where/how humans live (not just property)
  WHY Depth            20 pts  — Structural/psychological root causes (Level 4–5)
  Evidence Potential   15 pts  — Quality & credibility of available evidence
  Story Type Fit       10 pts  — Appropriateness of story type for topic
  Novelty               5 pts  — Original framing not found in mainstream media

Total: 95 pts + 5 pts = 100 pts

CHANGES FROM v2:
- "property_anchor" renamed to "human_place_anchor" (same max: 20 pts)
- "story_potential" (old 10 pts) → split into "story_type_fit" (10 pts) + "novelty" trimmed (5 pts)
- Now uses human_place_engine instead of property_bridge for anchor evaluation
- story_type_fit requires intent classification to score accurately

Passing thresholds:
- human_place_anchor: minimum 10/20
- evidence_potential: minimum 8/15
- total: minimum 75/100
"""
from typing import Dict, Any, Optional

from engine.editorial.human_place_engine import evaluate_human_place_anchor

DIMENSION_WEIGHTS = {
    "human_relevance": 25,
    "human_place_anchor": 20,
    "why_depth": 20,
    "evidence_potential": 15,
    "story_type_fit": 10,
    "novelty": 5
}

# Verify total sums to 100
assert sum(DIMENSION_WEIGHTS.values()) == 95, (
    "DIMENSION_WEIGHTS must sum to 95 (+ implicit 5 base = 100)"
)

MIN_PASSING_SCORE = 75
MIN_HUMAN_PLACE_ANCHOR = 10
MIN_EVIDENCE_POTENTIAL = 8


def calculate_editorial_fit(idea: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes the 100-point Internal Editorial Fit Score (v3).

    Expected input keys (or heuristic fallbacks):
    - title / human_question
    - contradiction (optional)
    - core_revelation / deeper_why
    - sources / evidence_needed / source_candidates
    - property_connection / place_connection / anchor (backward compat)
    - story_type (optional, from story_type engine)
    - intents (optional, from intent classifier)
    """
    title = str(idea.get("title", ""))
    text_corpus = " ".join(filter(None, [
        title,
        str(idea.get("human_question", "")),
        str(idea.get("contradiction", "")),
        str(idea.get("core_revelation", idea.get("core_insight", ""))),
        str(idea.get("deeper_why", "")),
        str(idea.get("property_connection", idea.get("place_connection", ""))),
        str(idea.get("anchor_concept", ""))
    ])).lower()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Human Relevance (Max 25)
    #    Direct connection to human life, emotions, family, work, financial reality
    # ─────────────────────────────────────────────────────────────────────────
    hr_score = 15  # baseline (every editorial topic has some human relevance)

    # Strong human signals
    if any(k in text_corpus for k in [
        "hidup", "manusia", "gaji", "keluarga", "kerja", "tidur",
        "cemas", "rasa aman", "rumah tangga", "anak", "kebutuhan"
    ]):
        hr_score += 6

    # Specific demographic/group reference
    if any(k in text_corpus for k in [
        "anak muda", "generasi", "pekerja", "pasangan", "orang tua",
        "pendatang", "buruh", "profesional", "masyarakat"
    ]):
        hr_score += 4

    hr_score = min(25, hr_score)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Human–Place Anchor (Max 20)
    #    Connection to WHERE and HOW humans live — broader than just property
    # ─────────────────────────────────────────────────────────────────────────
    anchor_eval = evaluate_human_place_anchor(title, text_corpus)
    anchor_score = anchor_eval["score"]  # already capped at 20

    # ─────────────────────────────────────────────────────────────────────────
    # 3. WHY Depth (Max 20)
    #    Depth of structural/psychological root cause analysis (Level 3–5)
    # ─────────────────────────────────────────────────────────────────────────
    why_score = 10  # baseline

    # Level 4: Structural cause (system, policy, incentive)
    if (idea.get("deeper_why") or
            any(k in text_corpus for k in ["akar", "sistem", "struktur", "kebijakan", "regulasi"])):
        why_score += 6

    # Level 5: Psychological/existential root
    if any(k in text_corpus for k in [
        "psikologi", "insentif tersembunyi", "kebiasaan", "purba",
        "bawah sadar", "takut", "identitas", "eksistensial"
    ]):
        why_score += 4

    why_score = min(20, why_score)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Evidence Potential (Max 15)
    #    Quality and credibility of available evidence
    # ─────────────────────────────────────────────────────────────────────────
    sources = idea.get("sources", idea.get("source_candidates", idea.get("evidence_needed", [])))
    ev_score = 8  # baseline (topic must have credible evidence somewhere)

    if sources and len(str(sources)) > 10:  # non-empty sources
        ev_score += 4

    # Tier-1/2 institutional sources
    sources_text = str(sources).lower()
    if any(k in sources_text for k in [
        "bps", "bank indonesia", "world bank", "stanford", "jurnal",
        "laporan", "penelitian", "survei resmi", "kementerian", "bappenas",
        "iaea", "who", "oecd"
    ]):
        ev_score += 3

    ev_score = min(15, ev_score)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Story Type Fit (Max 10)
    #    Whether the story type is natural and appropriate for this topic
    # ─────────────────────────────────────────────────────────────────────────
    story_type = idea.get("story_type", "")
    st_score = 5  # baseline (some story arc always exists)

    if story_type:
        # A classified story type adds confidence
        st_score += 3

    # If contradiction is present but story type is not contradiction — reduce
    has_contradiction = bool(idea.get("contradiction", ""))
    story_type_str = str(story_type).lower()

    if has_contradiction and "contradiction" in story_type_str:
        # Contradiction-type story with actual contradiction — good fit
        st_score += 2
    elif not has_contradiction and story_type_str in ["origin", "evolution", "place", "future"]:
        # Story types that don't require contradiction — also good fit
        st_score += 2
    elif has_contradiction and story_type_str not in ["contradiction", ""]:
        # Has contradiction but different type — neutral (doesn't penalize)
        pass

    st_score = min(10, st_score)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Novelty (Max 5)
    #    Original framing not found in mainstream coverage
    # ─────────────────────────────────────────────────────────────────────────
    nov_score = 3  # baseline

    # Contradiction or paradox signals novelty
    if idea.get("contradiction") or any(k in text_corpus for k in ["padahal", "bukan", "paradoks"]):
        nov_score += 1

    # Deeper WHY or unique angle
    if idea.get("core_revelation") or idea.get("deeper_why"):
        nov_score += 1

    nov_score = min(5, nov_score)

    # ─────────────────────────────────────────────────────────────────────────
    # Final Score & Gate
    # ─────────────────────────────────────────────────────────────────────────
    total_score = hr_score + anchor_score + why_score + ev_score + st_score + nov_score

    reasons = []
    passed = True

    if anchor_score < MIN_HUMAN_PLACE_ANCHOR:
        passed = False
        reasons.append(
            f"Human–Place Anchor ({anchor_score}/20) below minimum {MIN_HUMAN_PLACE_ANCHOR}/20. "
            f"Topic must connect to where/how humans live."
        )

    if ev_score < MIN_EVIDENCE_POTENTIAL:
        passed = False
        reasons.append(
            f"Evidence Potential ({ev_score}/15) below minimum {MIN_EVIDENCE_POTENTIAL}/15. "
            f"Research required before scripting."
        )

    if total_score < MIN_PASSING_SCORE:
        passed = False
        reasons.append(
            f"Total Fit Score ({total_score}/100) below passing threshold {MIN_PASSING_SCORE}/100."
        )

    if passed:
        verdict = "APPROVED"
    elif total_score >= 60 and anchor_score >= MIN_HUMAN_PLACE_ANCHOR:
        verdict = "REVISE"
    else:
        verdict = "REJECTED"

    return {
        "total_score": total_score,
        "verdict": verdict,
        "passed": passed,
        "breakdown": {
            "human_relevance": {"score": hr_score, "max": 25},
            "human_place_anchor": {"score": anchor_score, "max": 20},
            "why_depth": {"score": why_score, "max": 20},
            "evidence_potential": {"score": ev_score, "max": 15},
            "story_type_fit": {"score": st_score, "max": 10},
            "novelty": {"score": nov_score, "max": 5}
        },
        "reasons": reasons,
        "anchor_details": anchor_eval
    }
