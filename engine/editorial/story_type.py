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
            "STORY — The beginning",
            "TURN — The moment it took its form",
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
            "COLD OPEN — State B: what exists now",
            "QUESTION — But how was it different before?",
            "STATE A — What existed before the transformation",
            "FORCES OF CHANGE — What drove the transformation",
            "CAUSAL CHAIN — The mechanics of transformation",
            "HUMAN CONSEQUENCE — Who was affected and how",
            "REVELATION — What the transformation reveals",
            "REFLECTION — What stays the same through change?"
        ],
        "short_pipeline": [
            "HOOK — Show the 'after' state",
            "QUESTION — But what came before?",
            "STORY — The transformation",
            "TURN — The pivot moment",
            "REVELATION — What it reveals",
            "REFLECTION"
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
            "THE SURFACE — What people assume or see",
            "THE SYSTEM — The hidden mechanism at work",
            "EVIDENCE — Data and facts supporting the hidden system",
            "CONSEQUENCES — Who benefits, who doesn't",
            "REVELATION — The hidden system changes your understanding",
            "REFLECTION — Now that you see it, what will you do?"
        ],
        "short_pipeline": [
            "HOOK — Ordinary thing",
            "QUESTION — But something's odd",
            "STORY — The hidden system",
            "TURN — The reveal",
            "REVELATION",
            "REFLECTION"
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
            "COLD OPEN — The assumption everyone holds",
            "QUESTION — But what if the opposite is true?",
            "THE ASSUMPTION — What people believe",
            "THE REALITY — What actually happens",
            "WHY THE GAP EXISTS — Structural explanation",
            "EVIDENCE — Data that confirms the gap",
            "REVELATION — The gap reveals something important",
            "REFLECTION — What should we believe instead?"
        ],
        "short_pipeline": [
            "HOOK — Common assumption",
            "QUESTION — But wait",
            "STORY — The contradiction",
            "TURN — The real reason",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The situation people face",
            "QUESTION — Why must this choice be made?",
            "OPTION A — First path and its costs",
            "OPTION B — Second path and its costs",
            "THE SYSTEM — Why this trade-off exists at all",
            "HUMAN CONSEQUENCE — The emotional and physical reality",
            "REVELATION — What the trade-off reveals about our world",
            "REFLECTION — Is there a third path?"
        ],
        "short_pipeline": [
            "HOOK — The impossible choice",
            "QUESTION — Why must we choose?",
            "STORY — The trade-off",
            "TURN — The real reason it exists",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The obvious primary change",
            "FIRST-ORDER EFFECT — What everyone expects",
            "QUESTION — But what happens next?",
            "SECOND-ORDER EFFECT — The unexpected consequence",
            "THIRD-ORDER (optional) — How far it ripples",
            "EVIDENCE — Examples and data",
            "REVELATION — The full chain no one traced before",
            "REFLECTION — What else might ripple from changes we're making today?"
        ],
        "short_pipeline": [
            "HOOK — Obvious change",
            "QUESTION — But what happens next?",
            "STORY — The cascade",
            "TURN — The unexpected destination",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The place as it appears today",
            "QUESTION — But why is it like this?",
            "HISTORICAL FORCES — What shaped this place",
            "ECONOMIC FORCES — Who had interest in forming it",
            "HUMAN PATTERNS — Who lives/works here and why",
            "THE PLACE TODAY — What the forces created",
            "REVELATION — What this place reveals about broader systems",
            "REFLECTION — What might change this place next?"
        ],
        "short_pipeline": [
            "HOOK — The place",
            "QUESTION — Why does it look like this?",
            "STORY — The forces that shaped it",
            "TURN — The hidden architect",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The current form",
            "QUESTION — How did it come to be this way?",
            "EARLY FORM — The earliest known state",
            "EVOLUTION STAGES — Key transitions through time",
            "DRIVING FORCES — What drove each change",
            "CURRENT STATE — Where we are now",
            "REVELATION — The pattern across evolution",
            "REFLECTION — Where might it evolve next?"
        ],
        "short_pipeline": [
            "HOOK — Current form",
            "QUESTION — But how did it start?",
            "STORY — The evolution",
            "TURN — The defining transformation",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The current trend or force",
            "QUESTION — If this continues, what happens?",
            "CURRENT TRAJECTORY — Evidence of the trend",
            "FIRST-ORDER PROJECTION — What happens directly",
            "SECOND-ORDER PROJECTION — Unexpected consequences",
            "HUMAN CONSEQUENCE — Who will be affected",
            "REVELATION — The future that's already forming",
            "REFLECTION — What could change this trajectory?"
        ],
        "short_pipeline": [
            "HOOK — The force shaping the future",
            "QUESTION — Where does this lead?",
            "STORY — The projection",
            "TURN — The unexpected destination",
            "REVELATION",
            "REFLECTION"
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
            "OBSERVATION — The widely held belief or frame",
            "QUESTION — But what if we're thinking about it wrong?",
            "THE FRAME — How people currently see it",
            "THE ALTERNATIVE FRAME — A different way to see it",
            "EVIDENCE — Why the new frame is more accurate",
            "IMPLICATIONS — What changes if we accept the new frame",
            "REVELATION — The reframe's broader meaning",
            "REFLECTION — Now that you see it differently..."
        ],
        "short_pipeline": [
            "HOOK — Common belief",
            "QUESTION — But what if we're wrong?",
            "STORY — The alternative frame",
            "TURN — Why the old frame was limiting",
            "REVELATION",
            "REFLECTION"
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
