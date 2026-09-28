"""
Story Type Engine v1
Classifies topics into narrative archetypes and selects appropriate narrative devices.

CONTRADICTION is NOT mandatory. Each story type has its own natural structure.
The engine selects the most appropriate narrative device (not always contradiction).

10 Story Types:
1. ORIGIN — How did this begin?
2. TRANSFORMATION — How did A become B?
3. HIDDEN_SYSTEM — What system operates behind the ordinary?
4. CONTRADICTION — Why is reality different from assumption?
5. HUMAN_DILEMMA — Why must a person trade one thing for another?
6. SECOND_ORDER — What unexpected consequence follows?
7. PLACE — Why does this place look/work/feel like this?
8. EVOLUTION — How did living arrangements change over time?
9. FUTURE — If this trend continues, what happens?
10. REFRAME — What assumption should the audience reconsider?
"""
import re
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Story Type Definitions
# ---------------------------------------------------------------------------
STORY_TYPES = {
    "origin": {
        "name": "ORIGIN STORY",
        "description": "How did this begin? Traces the birth of a system, habit, or place.",
        "narrative_device": "mystery_reveal",
        "pipeline": [
            "OBSERVATION — What exists today that seems obvious?",
            "QUESTION — But when and why did it start?",
            "HISTORICAL CONTEXT — The world before this existed",
            "TURNING POINT — The moment it began",
            "CAUSAL CHAIN — How it became what we know today",
            "REVELATION — What the origin reveals about us now",
            "REFLECTION — Open question about inheritance"
        ],
        "short_pipeline": [
            "HOOK — Present the thing that exists",
            "QUESTION — But nobody asks why it started",
            "HISTORICAL CONTEXT — The world before this existed",
            "TURNING POINT — The moment it took its form",
            "REVELATION — What the origin tells us about now",
            "REFLECTION — Open question"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "pertama kali", "asal-usul", "kapan", "bagaimana pertama", "lahir",
            "mulai", "awal", "ditemukan", "zaman dahulu", "purba"
        ],
        "detection_patterns": [
            r"kapan\s+\w+\s+pertama", r"bagaimana\s+\w+\s+pertama",
            r"asal.?usul", r"seperti\s+apa\s+\w+\s+sebelum"
        ]
    },
    "transformation": {
        "name": "TRANSFORMATION STORY",
        "description": "How did A become B? Documents a profound change from one state to another.",
        "narrative_device": "before_after",
        "pipeline": [
            "OBSERVATION — What exists now in its transformed state",
            "BEFORE STATE — What existed before the transformation",
            "FORCES OF CHANGE — What drove the transformation",
            "TRANSFORMATION — The mechanics and turning point of change",
            "HUMAN CONSEQUENCE — Who was affected and how daily life shifted",
            "REVELATION — What the transformation reveals about broader systems",
            "REFLECTION — What stays the same through change?"
        ],
        "short_pipeline": [
            "HOOK — Show the 'after' state",
            "BEFORE STATE — What existed before the change",
            "FORCES OF CHANGE — What shifted",
            "TRANSFORMATION — The pivot moment",
            "REVELATION — What it reveals",
            "REFLECTION — Open reflection"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "berubah", "mengubah", "transformasi", "pergeseran", "evolusi",
            "dulu", "sekarang", "menjadi", "transisi", "perubahan"
        ],
        "detection_patterns": [
            r"bagaimana\s+\w+\s+berubah", r"mengubah\s+bentuk",
            r"dari\s+\w+\s+menjadi", r"dari\s+dulu\s+hingga"
        ]
    },
    "hidden_system": {
        "name": "HIDDEN SYSTEM STORY",
        "description": "What system operates behind something ordinary? Exposes the invisible mechanism.",
        "narrative_device": "expose_mechanism",
        "pipeline": [
            "OBSERVATION — Ordinary phenomenon everyone experiences",
            "QUESTION — But what's actually happening underneath?",
            "SURFACE — What people assume or see on the surface",
            "HIDDEN MECHANISM — The invisible system at work",
            "EVIDENCE — Data and facts supporting the hidden system",
            "CONSEQUENCES — Who benefits, who bears the cost",
            "REVELATION — The hidden system changes your understanding",
            "REFLECTION — Now that you see it, what does it mean for how we live?"
        ],
        "short_pipeline": [
            "HOOK — Ordinary thing everyone sees",
            "QUESTION — But what's really happening?",
            "HIDDEN MECHANISM — The unseen machine",
            "CONSEQUENCES — Who it affects",
            "REVELATION — The epiphany",
            "REFLECTION — Closing question"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "sistem", "tersembunyi", "sebenarnya", "di balik", "kenapa",
            "mekanisme", "struktur", "insentif", "mengapa selalu"
        ]
    },
    "contradiction": {
        "name": "CONTRADICTION STORY",
        "description": "Why is reality different from what people assume? The gap between expectation and truth.",
        "narrative_device": "contradiction",
        "pipeline": [
            "ASSUMPTION — The common belief or expectation everyone holds",
            "QUESTION — But what if reality contradicts the assumption?",
            "REALITY — What actually happens in the data and field",
            "WHY THE GAP EXISTS — Structural and psychological explanation",
            "EVIDENCE — Rigorous facts and data confirming the contradiction",
            "REVELATION — What this contradiction reveals about our world",
            "REFLECTION — What should we understand instead?"
        ],
        "short_pipeline": [
            "HOOK — Common assumption",
            "CONTRADICTION — Reality check and gap",
            "WHY THE GAP EXISTS — The real structural reason",
            "REVELATION — The perspective shift",
            "REFLECTION — Closing thought"
        ],
        "contradiction_required": True,
        "detection_keywords": [
            "padahal", "justru", "ternyata", "paradoks", "kontradiksi",
            "aneh", "seharusnya", "tapi malah", "kenapa justru", "tapi",
            "tetapi", "namun", "meskipun", "walaupun"
        ],
        "detection_patterns": [
            r"kenapa\s+\w+\s+justru", r"padahal\s+seharusnya",
            r"ternyata\s+\w+\s+justru", r"tapi\s+(masih|justru|malah|terasa)",
            r"\b(tapi|namun|tetapi)\b"
        ]
    },
    "human_dilemma": {
        "name": "HUMAN DILEMMA",
        "description": "Why must a person trade one thing for another? Explores the real trade-offs of life.",
        "narrative_device": "trade_off",
        "pipeline": [
            "SITUATION — The real-world situation people face",
            "CHOICE A — First path and its perceived benefits and costs",
            "CHOICE B — Second path and its perceived benefits and costs",
            "TRADE-OFF — The impossible compromise between the two",
            "SYSTEMIC CAUSE — Why this dilemma exists at a structural level",
            "HUMAN CONSEQUENCE — The emotional, physical, and financial toll",
            "REVELATION — What the dilemma reveals about how society is organized",
            "REFLECTION — Is there an unexamined third path?"
        ],
        "short_pipeline": [
            "HOOK — The impossible choice",
            "TRADE-OFF — Choice A vs Choice B",
            "SYSTEMIC CAUSE — Why we must choose",
            "REVELATION — What the trade-off means",
            "REFLECTION — Closing thought"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "rela", "terpaksa", "trade-off", "pilih", "pilihan", "barter",
            "mengorbakan", "kenapa orang rela", "kenapa memilih"
        ]
    },
    "second_order": {
        "name": "SECOND-ORDER STORY",
        "description": "What unexpected consequence follows from an obvious change?",
        "narrative_device": "cascade_effect",
        "pipeline": [
            "INITIAL CHANGE — The primary change or intervention",
            "FIRST-ORDER EFFECT — The immediate and obvious consequence",
            "QUESTION — But what unexpected ripples follow next?",
            "SECOND-ORDER EFFECT — The unintended or hidden downstream consequence",
            "EVIDENCE — Data and historical examples confirming the ripple effect",
            "REVELATION — The full causal chain connecting the initial act to distant impact",
            "REFLECTION — What second-order effects are being created by decisions today?"
        ],
        "short_pipeline": [
            "HOOK — Obvious change",
            "FIRST-ORDER EFFECT — What everyone expects",
            "SECOND-ORDER EFFECT — The unexpected ripple",
            "REVELATION — The full chain revealed",
            "REFLECTION — Closing question"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "dampak", "konsekuensi", "akhirnya", "ujungnya", "kalau", "jika",
            "maka", "lalu", "kemudian menyebabkan", "efek domino"
        ]
    },
    "place": {
        "name": "PLACE STORY",
        "description": "Why does this place look/work/live like this? A deep dive into a specific place.",
        "narrative_device": "spatial_mystery",
        "pipeline": [
            "OBSERVATION OF PLACE — The place as it appears and functions today",
            "QUESTION — But why did this place take this specific form?",
            "SPATIAL CONTEXT — How geography and spatial relationships define it",
            "HISTORICAL/STRUCTURAL CAUSE — The forces, policies, and history that shaped it",
            "EVIDENCE — Historical records, maps, and socioeconomic data",
            "REVELATION — What this place reveals about human settlement and power",
            "REFLECTION — What might reshape this place next?"
        ],
        "short_pipeline": [
            "HOOK — The place as it stands today",
            "QUESTION — Why did it form this way?",
            "SPATIAL CONTEXT — Geography and history",
            "STRUCTURAL CAUSE — The forces that shaped it",
            "REVELATION — What this place reveals",
            "REFLECTION — Closing thought"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "kota", "kawasan", "daerah", "wilayah", "kenapa kota", "kenapa di",
            "kenapa pusat", "kenapa daerah", "tempat ini", "kampung"
        ]
    },
    "evolution": {
        "name": "EVOLUTION STORY",
        "description": "How did human living arrangements change over time?",
        "narrative_device": "timeline_progression",
        "pipeline": [
            "PRESENT STATE — How human living arrangements look today",
            "EARLIER STATE — The earliest known baseline and living pattern",
            "TIMELINE — Key evolutionary stages across generations",
            "FORCES OF CHANGE — Technology, ecology, and economy driving each transition",
            "HUMAN CONSEQUENCE — How each evolutionary leap changed human behavior",
            "REVELATION — The enduring pattern underlying all human adaptation",
            "REFLECTION — What is the next evolutionary step in how we live?"
        ],
        "short_pipeline": [
            "HOOK — Current living form",
            "EARLIER STATE — Where we started",
            "TIMELINE — Key transition moments",
            "FORCES OF CHANGE — What pushed the evolution",
            "REVELATION — The enduring pattern",
            "REFLECTION — Where it evolves next"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "evolusi", "perkembangan", "berevolusi", "sepanjang sejarah",
            "dari zaman", "bagaimana manusia", "bentuk", "perubahan"
        ]
    },
    "future": {
        "name": "FUTURE STORY",
        "description": "If this trend continues, what happens to where/how humans live?",
        "narrative_device": "projection",
        "pipeline": [
            "CURRENT CONDITION — The baseline state of where and how we live",
            "EMERGING CHANGE — The signal, technology, or demographic shift emerging now",
            "SCENARIO — The plausible trajectory if this force accelerates",
            "SECOND-ORDER CONSEQUENCES — Unexpected impacts on communities, spaces, and work",
            "EVIDENCE/ASSUMPTIONS — Empirical trends and critical assumptions behind the projection",
            "REVELATION — The future living pattern that is already quietly taking root",
            "REFLECTION — What agency do we have to shape this outcome?"
        ],
        "short_pipeline": [
            "HOOK — Current condition and emerging signal",
            "EMERGING CHANGE — The force gaining momentum",
            "SCENARIO — Plausible projection",
            "SECOND-ORDER CONSEQUENCES — Impact on human life",
            "REVELATION — The emerging future",
            "REFLECTION — What choice do we make today?"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "masa depan", "akan", "proyeksi", "prediksi", "skenario",
            "apakah ai", "kalau ai", "jika terus", "ke depan"
        ]
    },
    "reframe": {
        "name": "REFRAME STORY",
        "description": "What common assumption should the audience reconsider?",
        "narrative_device": "assumption_challenge",
        "pipeline": [
            "COMMON ASSUMPTION — The widespread mental model or conventional wisdom",
            "QUESTION — But what if that framing blinds us to the real problem?",
            "EVIDENCE — Empirical facts that cannot be explained by the common assumption",
            "ALTERNATIVE INTERPRETATION — The new lens that makes sense of the anomalies",
            "DEEPER WHY — Structural incentives and psychological roots of the old myth",
            "REVELATION — How seeing through the new lens transforms understanding",
            "REFLECTION — How does our everyday behavior change once the frame is broken?"
        ],
        "short_pipeline": [
            "HOOK — Common assumption",
            "QUESTION — Why that assumption is flawed",
            "ALTERNATIVE INTERPRETATION — The fresh lens",
            "DEEPER WHY — Root reason for the old belief",
            "REVELATION — The breakthrough insight",
            "REFLECTION — Actionable reflection"
        ],
        "contradiction_required": False,
        "detection_keywords": [
            "sebenarnya", "bukan", "bukan sekadar", "cara pandang", "perspektif",
            "kerangka", "anggapan", "paradigma", "makna"
        ]
    }
}

# Narrative devices mapping (for metadata)
NARRATIVE_DEVICES = {
    "mystery_reveal": "Builds mystery then reveals origin",
    "before_after": "Contrasts before and after states",
    "expose_mechanism": "Reveals hidden system/mechanism",
    "contradiction": "Exposes gap between belief and reality",
    "trade_off": "Explores impossible choices and their cost",
    "cascade_effect": "Traces chain of unexpected consequences",
    "spatial_mystery": "Explores why a place is what it is",
    "timeline_progression": "Documents evolution through time",
    "projection": "Projects current forces into future",
    "assumption_challenge": "Challenges taken-for-granted beliefs"
}


def classify_story_type(
    topic: str,
    context: str = "",
    intents: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Classifies a topic into the most appropriate story type(s).
    
    Args:
        topic: The topic or query text
        context: Optional additional context
        intents: Optional pre-computed intent classifications (from intent_classifier)
        
    Returns:
        dict with: primary_type, secondary_types, narrative_device, 
                   pipeline, contradiction_required, all_matches
    """
    text = (topic + " " + context).lower()
    matched_types = []

    for type_name, definition in STORY_TYPES.items():
        hit_count = 0
        
        # Check keywords
        keywords_hit = [kw for kw in definition.get("detection_keywords", []) if kw in text]
        hit_count += len(keywords_hit)
        
        # Check patterns
        patterns_hit = []
        for pattern in definition.get("detection_patterns", []):
            if re.search(pattern, text):
                patterns_hit.append(pattern)
                hit_count += 2

        # Intent-based boosting
        if intents:
            intent_boosts = {
                "historical": ["origin", "evolution", "transformation"],
                "origin": ["origin"],
                "future": ["future", "second_order"],
                "economic": ["hidden_system", "contradiction"],
                "psychological": ["human_dilemma", "reframe"],
                "urban": ["place", "transformation"],
                "geographic": ["place"],
                "behavioral": ["human_dilemma", "reframe"],
                "technological": ["future", "second_order", "transformation"]
            }
            for intent in intents:
                if intent in intent_boosts:
                    for boosted_type in intent_boosts[intent]:
                        if type_name == boosted_type:
                            hit_count += 3  # strong boost from intent signal

        if hit_count > 0:
            matched_types.append({
                "type": type_name,
                "name": definition["name"],
                "hit_count": hit_count,
                "contradiction_required": definition["contradiction_required"],
                "narrative_device": definition["narrative_device"]
            })

    # Sort by hit count
    matched_types.sort(key=lambda x: x["hit_count"], reverse=True)

    # Default to explanatory/hidden_system if nothing matched
    if not matched_types:
        primary = "hidden_system"
    else:
        primary = matched_types[0]["type"]

    primary_def = STORY_TYPES[primary]
    secondary_types = [m["type"] for m in matched_types[1:3]]

    return {
        "primary_type": primary,
        "primary_type_name": primary_def["name"],
        "narrative_device": primary_def["narrative_device"],
        "narrative_device_description": NARRATIVE_DEVICES.get(primary_def["narrative_device"], ""),
        "pipeline": primary_def["pipeline"],
        "short_pipeline": primary_def["short_pipeline"],
        "contradiction_required": primary_def["contradiction_required"],
        "secondary_types": secondary_types,
        "all_matches": matched_types,
        "description": primary_def["description"]
    }


def get_narrative_device(story_type: str) -> str:
    """Returns the narrative device for a given story type."""
    definition = STORY_TYPES.get(story_type, {})
    return definition.get("narrative_device", "expose_mechanism")


def is_contradiction_required(story_type: str) -> bool:
    """Returns whether contradiction is required for a given story type."""
    definition = STORY_TYPES.get(story_type, {})
    return definition.get("contradiction_required", False)


def get_script_structure(story_type: str, format_mode: str = "long") -> Dict[str, Any]:
    """
    Returns the dynamic script structure determined by Story Type and Narrative Device.
    
    Guarantees:
    - Story Type is the source of truth.
    - Contradiction stage is NOT forced for non-contradiction story types.
    - Contradiction stage appears only when naturally selected (contradiction story type).
    
    Args:
        story_type: Archetype key (origin, transformation, hidden_system, contradiction, etc.)
        format_mode: 'long' (video essay, 6-12 min) or 'short' (reels/shorts, 60-90s)
        
    Returns:
        dict containing story_type, narrative_device, stages, stage_names, contradiction_required,
        has_contradiction_stage, and description.
    """
    st_lower = str(story_type or "hidden_system").lower().strip()
    if st_lower not in STORY_TYPES:
        st_lower = "hidden_system"

    definition = STORY_TYPES[st_lower]
    stages = definition["pipeline"] if format_mode == "long" else definition["short_pipeline"]
    stage_names = [s.split(" — ")[0].strip() for s in stages]
    has_contradiction = any("CONTRADICTION" in s.upper() for s in stage_names) or definition["contradiction_required"]

    return {
        "story_type": st_lower,
        "story_type_name": definition["name"],
        "narrative_device": definition["narrative_device"],
        "narrative_device_description": NARRATIVE_DEVICES.get(definition["narrative_device"], ""),
        "format_mode": format_mode,
        "contradiction_required": definition["contradiction_required"],
        "has_contradiction_stage": has_contradiction,
        "stages": stages,
        "stage_names": stage_names,
        "description": definition["description"]
    }


def list_story_types() -> List[Dict[str, str]]:
    """Returns a summary of all story types."""
    return [
        {
            "type": name,
            "name": defn["name"],
            "description": defn["description"],
            "narrative_device": defn["narrative_device"]
        }
        for name, defn in STORY_TYPES.items()
    ]
