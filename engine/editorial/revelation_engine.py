"""
Revelation Engine v1
Generates the editorial REVELATION for a given story — the moment of insight that
changes how the audience understands the world.

Revelations must be:
1. SPECIFIC — tied to actual facts, not vague wisdom
2. ORIGINAL — a conclusion the audience couldn't reach just from headlines
3. HUMAN — connected to lived experience, not just abstract systems
4. ACTIONABLE or REFLECTIVE — gives the audience something to think about

Revelations must NOT be:
- Generic wisdom ("Technology changes everything")
- Motivational platitudes ("We must adapt")
- Forced positivity ("There is hope")
- AI clichés ("In this fast-paced digital world...")
"""
import re
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Revelation quality checkers
# ---------------------------------------------------------------------------
GENERIC_REVELATION_PATTERNS = [
    r"teknologi\s+mengubah\s+segalanya",
    r"kita\s+harus\s+beradaptasi",
    r"masa\s+depan\s+ada\s+di\s+tangan",
    r"jangan\s+takut\s+(berubah|beradaptasi)",
    r"perubahan\s+(selalu|adalah)\s+(baik|keniscayaan|tak terelakkan)",
    r"di\s+era\s+digital\s+yang\s+serba\s+cepat",
    r"mari\s+(kita|bersama)\s+beradaptasi",
    r"kesimpulannya\s+adalah",
    r"pada\s+akhirnya",
    r"pelajaran\s+yang\s+bisa\s+diambil"
]

FORBIDDEN_REVELATION_PHRASES = [
    "di era digital yang serba cepat",
    "menyelami samudera peluang",
    "revolusi tak terelakkan",
    "teknologi mengubah segalanya",
    "kita harus beradaptasi",
    "pada akhirnya semua tergantung",
    "kesimpulannya",
    "jadi kesimpulannya",
    "poin utama dari video ini",
    "jangan lupa untuk"
]

# Revelation archetypes by story type
REVELATION_ARCHETYPES = {
    "origin": {
        "prompt_template": (
            "The origin of {topic} reveals that what we consider 'natural' or 'obvious' about "
            "{anchor_concept} was actually the result of {specific_historical_force} "
            "operating at a specific moment in time — which means {implication_for_today}."
        ),
        "quality_markers": [
            "specific historical force",
            "clear implication for present",
            "not what people assumed"
        ]
    },
    "contradiction": {
        "prompt_template": (
            "The real reason {assumption} fails to explain {phenomenon} is that "
            "{hidden_system} benefits from keeping people thinking {wrong_belief}. "
            "When you understand this, {implication}."
        ),
        "quality_markers": [
            "names a specific beneficiary",
            "explains the mechanism",
            "clear implication"
        ]
    },
    "hidden_system": {
        "prompt_template": (
            "Behind {ordinary_phenomenon}, there is a {specific_system} that "
            "{mechanism}. This is why {consequence_for_ordinary_people}, "
            "even though they may never see the system itself."
        ),
        "quality_markers": [
            "names the system",
            "explains its mechanism",
            "shows consequence for ordinary people"
        ]
    },
    "human_dilemma": {
        "prompt_template": (
            "The trade-off people face with {topic} is not really a personal failure — "
            "it's a structural outcome of {specific_system} that forces {specific_group} "
            "to choose between {option_a} and {option_b}. "
            "This reveals that the 'choice' is not really a choice."
        ),
        "quality_markers": [
            "names the structural cause",
            "specific group affected",
            "reframes personal failure as structural"
        ]
    },
    "place": {
        "prompt_template": (
            "Why {place} looks/works/lives like this is not an accident — "
            "it is the spatial outcome of {specific_historical_economic_force}. "
            "What the place reveals is {deeper_truth_about_human_systems}."
        ),
        "quality_markers": [
            "specific force named",
            "spatial consequence explained",
            "reveals broader truth"
        ]
    },
    "future": {
        "prompt_template": (
            "If {current_trend} continues, by {timeframe} we will see {specific_projection} "
            "not because of technology alone, but because of {underlying_structural_force}. "
            "The revealing part is: {unexpected_implication}."
        ),
        "quality_markers": [
            "specific timeframe",
            "names underlying force (not just 'technology')",
            "unexpected implication"
        ]
    },
    "transformation": {
        "prompt_template": (
            "{current_state} did not emerge naturally — it was the result of "
            "{specific_force} at {historical_moment}, which transformed {before_state} "
            "into {after_state}. This transformation reveals {deeper_truth}."
        ),
        "quality_markers": [
            "specific force named",
            "historical moment",
            "before/after contrast"
        ]
    },
    "evolution": {
        "prompt_template": (
            "Looking at the full evolution of {topic}, the recurring pattern is "
            "{pattern_across_time}. This suggests that despite surface-level change, "
            "{what_stays_constant} remains unchanged — because {structural_reason}."
        ),
        "quality_markers": [
            "recurring pattern named",
            "what stays constant",
            "structural explanation"
        ]
    },
    "second_order": {
        "prompt_template": (
            "The first-order effect of {change} is obvious. But the second-order effect — "
            "{unexpected_consequence} — is what actually matters for {affected_group}. "
            "This happens because {mechanism}, which most people never trace back to {change}."
        ),
        "quality_markers": [
            "unexpected consequence",
            "affected group named",
            "mechanism explained"
        ]
    },
    "reframe": {
        "prompt_template": (
            "When we stop thinking of {topic} as {old_frame} and instead think of it as "
            "{new_frame}, everything changes. Suddenly, {implication_a} and {implication_b} "
            "make sense in a way they didn't before."
        ),
        "quality_markers": [
            "old frame vs new frame clearly stated",
            "specific implications of new frame"
        ]
    }
}

# ---------------------------------------------------------------------------
# Causal chain patterns for evidence-based revelation generation
# ---------------------------------------------------------------------------
CAUSAL_CONNECTORS = [
    "menyebabkan", "mengakibatkan", "berdampak pada", "mendorong",
    "memaksa", "menghasilkan", "berujung pada", "menciptakan",
    "merupakan hasil dari", "adalah konsekuensi dari",
    "inilah kenapa", "inilah mengapa", "inilah alasan", "karena",
    "alasan kenapa", "alasan mengapa", "sehingga", "karena itulah",
    "yang membuat", "menjelaskan mengapa", "menjelaskan kenapa"
]


def check_revelation_quality(revelation_text: str) -> Dict[str, Any]:
    """
    Evaluates the quality of a revelation text.
    
    Returns:
        dict with: passed, issues, quality_score (0-10)
    """
    text = revelation_text.lower()
    issues = []

    # Check for forbidden phrases
    for phrase in FORBIDDEN_REVELATION_PHRASES:
        if phrase in text:
            issues.append(f"Forbidden phrase: '{phrase}'")

    # Check for generic patterns
    for pattern in GENERIC_REVELATION_PATTERNS:
        if re.search(pattern, text):
            issues.append(f"Generic revelation pattern detected")
            break

    # Check minimum length (revelations should be substantive)
    if len(revelation_text.strip()) < 50:
        issues.append("Revelation too short — must be substantive, not a one-liner cliché")

    # Check for specificity markers (presence of specific terms)
    specificity_markers = [
        r"\d{4}",           # year
        r"\d+\s*%",         # percentage
        r"\d+[\.,]\d+",     # specific number
        r"(rupiah|rp|idr)", # currency
        r"(bps|bi|bank\s+indonesia|kementerian)", # institutions
    ]
    has_specificity = any(re.search(p, text, re.IGNORECASE) for p in specificity_markers)

    # Check for causal language
    has_causality = any(conn in text for conn in CAUSAL_CONNECTORS)

    # Score
    quality_score = 7  # baseline
    if issues:
        quality_score -= len(issues) * 2
    if has_specificity:
        quality_score += 1
    if has_causality:
        quality_score += 1
    quality_score = max(0, min(10, quality_score))

    passed = quality_score >= 6 and len(issues) == 0

    return {
        "passed": passed,
        "quality_score": quality_score,
        "issues": issues,
        "has_specificity": has_specificity,
        "has_causality": has_causality,
        "recommendation": (
            "Revelation passes quality check." if passed else
            f"Revelation needs improvement: {'; '.join(issues)}"
        )
    }


def generate_revelation_template(
    story_type: str,
    topic: str,
    anchor_concept: str = "",
    key_evidence: str = "",
    causal_chain: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Returns a revelation template and guidance for a given story type.
    
    Does NOT generate the final text (that requires LLM) — instead provides
    the structure and quality requirements for the revelation.
    
    Args:
        story_type: The story type classification
        topic: The topic text
        anchor_concept: The human–place anchor concept
        key_evidence: Key evidence or finding
        causal_chain: Optional causal chain from Human–Place engine
        
    Returns:
        dict with: template, quality_markers, causal_chain, guidance
    """
    archetype = REVELATION_ARCHETYPES.get(story_type, REVELATION_ARCHETYPES["hidden_system"])

    causal_chain_text = ""
    if causal_chain:
        causal_chain_text = " → ".join(causal_chain)

    guidance = {
        "do": [
            "Name a specific force, institution, or mechanism",
            "Tie the revelation to a concrete consequence for real people",
            "Show something the audience COULDN'T have concluded from headlines alone",
            "Connect to the Human–Place anchor: " + (anchor_concept or "how humans live")
        ],
        "dont": [
            "Generic wisdom: 'Technology changes everything'",
            "Motivational platitudes: 'We must adapt'",
            "AI clichés or robotic phrases",
            "Conclusions that apply to literally any topic"
        ],
        "examples_of_good_revelations": [
            "Harga tanah naik bukan karena permintaan biasa — tapi karena regulasi yang membuat pasokan tanah legal menjadi langka secara artifisial.",
            "AI tidak menghapus pekerjaan, tapi secara perlahan mengubah LOKASI pekerjaan — dan itu yang akan mengubah peta nilai properti kota.",
            "Kerinduan manusia akan rumah sendiri bukan tentang investasi — tapi tentang satu-satunya ruang di dunia yang tidak bisa diambil oleh algoritma."
        ]
    }

    return {
        "story_type": story_type,
        "template": archetype["prompt_template"],
        "quality_markers": archetype["quality_markers"],
        "causal_chain": causal_chain_text,
        "guidance": guidance,
        "topic": topic,
        "anchor_concept": anchor_concept
    }


def evaluate_revelation(revelation_text: str, story_type: str) -> Dict[str, Any]:
    """
    Full evaluation of a revelation text for a specific story type.
    Combines quality check with story-type-specific assessment.
    """
    quality = check_revelation_quality(revelation_text)
    archetype = REVELATION_ARCHETYPES.get(story_type, {})
    quality_markers = archetype.get("quality_markers", [])

    text = revelation_text.lower()

    # Check how many quality markers are addressed
    markers_addressed = 0
    marker_notes = []
    for marker in quality_markers:
        # Basic heuristic: assume addressed if text length > 80 chars and no forbidden phrases
        if len(revelation_text) > 80 and not quality["issues"]:
            markers_addressed += 1
            marker_notes.append(f"[?] {marker} — needs human verification")
        else:
            marker_notes.append(f"[!] {marker} — likely NOT addressed")

    return {
        **quality,
        "story_type": story_type,
        "quality_markers_required": quality_markers,
        "quality_markers_notes": marker_notes,
        "markers_addressed": markers_addressed,
        "final_verdict": "APPROVED" if quality["passed"] else "NEEDS REVISION"
    }
