"""
Search Intent Classifier v1
Classifies search queries/topics into one or more intent classes.

Intent classes control research strategy expansion and story type selection.
Multiple intents can be assigned to a single query.

This classifier uses keyword-based heuristics (deterministic, no server required).
It can be augmented with embedding-based similarity in future versions.
"""
import re
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Intent class definitions with detection keywords
# ---------------------------------------------------------------------------
INTENT_DEFINITIONS = {
    "historical": {
        "description": "Query seeks origin, history, or past state",
        "keywords": [
            "sejarah", "asal-usul", "kapan pertama", "dahulu", "zaman dulu",
            "tempo doeloe", "pertama kali", "peradaban", "zaman batu", "purba",
            "kolonial", "asal mula", "bagaimana dulu", "ditemukan", "terbentuknya"
        ],
        "patterns": [
            r"kapan\s+\w+\s+pertama",
            r"bagaimana\s+\w+\s+pertama\s+muncul",
            r"asal.?usul",
            r"sejak\s+kapan",
            r"sejarah\s+terbentuk",
            r"bagaimana\s+sejarah"
        ]
    },
    "origin": {
        "description": "Query seeks the beginning or creation of something",
        "keywords": [
            "pertama kali", "asal", "mulai", "berawal", "lahir", "muncul",
            "terciptanya", "kapan manusia mulai", "kapan pertama", "bagaimana terbentuk"
        ],
        "patterns": [r"kapan\s+manusia\s+mulai", r"bagaimana\s+\w+\s+(pertama|awal)",
                     r"siapa\s+yang\s+pertama\s+kali"]
    },
    "explanatory": {
        "description": "Query seeks explanation of how something works or why",
        "keywords": [
            "bagaimana", "kenapa", "mengapa", "apa yang", "jelaskan", "karena",
            "bagaimana cara", "bagaimana proses", "mekanisme"
        ],
        "patterns": [r"^bagaimana\s+", r"^kenapa\s+", r"^mengapa\s+"]
    },
    "psychological": {
        "description": "Query involves human psychology, emotion, or motivation",
        "keywords": [
            "psikologi", "rasa aman", "nyaman", "merasa", "emosi", "takut",
            "cemas", "status", "identitas", "motivasi", "ingin", "butuh",
            "kebutuhan", "perasaan", "attachment"
        ]
    },
    "economic": {
        "description": "Query involves economics, prices, markets, or financial dynamics",
        "keywords": [
            "harga", "mahal", "murah", "ekonomi", "pasar", "biaya", "gaji",
            "pendapatan", "inflasi", "investasi", "modal", "uang", "nilai",
            "suku bunga", "pajak", "terjangkau"
        ]
    },
    "social": {
        "description": "Query involves social dynamics, community, or relationships",
        "keywords": [
            "masyarakat", "sosial", "komunitas", "keluarga", "tetangga",
            "stratifikasi", "kelas", "budaya", "adat", "tradisi", "komunal"
        ]
    },
    "urban": {
        "description": "Query involves cities, urban planning, or spatial dynamics",
        "keywords": [
            "kota", "urban", "tata kota", "tata ruang", "metropolitan",
            "pusat kota", "pinggiran", "perkotaan", "kawasan", "zonasi",
            "aglomerasi", "kemacetan"
        ]
    },
    "technological": {
        "description": "Query involves technology, AI, or digital transformation",
        "keywords": [
            "teknologi", "ai", "artificial intelligence", "digital", "internet",
            "otomasi", "robot", "software", "algoritma", "platform", "aplikasi"
        ]
    },
    "current": {
        "description": "Query involves current events, recent trends, or present conditions",
        "keywords": [
            "saat ini", "sekarang", "terkini", "terbaru", "hari ini", "minggu ini",
            "tahun ini", "baru-baru ini", "trend", "fenomena saat ini"
        ]
    },
    "future": {
        "description": "Query involves future projections, scenarios, or implications",
        "keywords": [
            "masa depan", "nanti", "akan", "prediksi", "proyeksi", "skenario",
            "apakah ai", "kalau ai", "jika", "dampak ke depan", "generasi mendatang"
        ],
        "patterns": [r"apakah\s+(ai|teknologi|ini)\s+akan", r"kalau\s+\w+\s+bisa",
                     r"masa\s+depan\s+\w+"]
    },
    "comparison": {
        "description": "Query compares two or more things, places, or time periods",
        "keywords": [
            "dibanding", "vs", "versus", "perbedaan", "perbandingan", "lebih",
            "daripada", "antara", "mana yang"
        ]
    },
    "procedural": {
        "description": "Query seeks how-to instructions or step-by-step processes",
        "keywords": [
            "cara", "langkah", "tips", "panduan", "tutorial", "bagaimana caranya",
            "how to", "apa yang harus", "apa langkah"
        ],
        "patterns": [r"cara\s+membayar", r"cara\s+mengurus", r"langkah\s+\w+"]
    },
    "legal": {
        "description": "Query involves law, regulations, rights, or legal systems",
        "keywords": [
            "hukum", "aturan", "regulasi", "undang-undang", "hak", "kewajiban",
            "sertifikat", "legalitas", "perizinan", "pbb", "pajak"
        ]
    },
    "geographic": {
        "description": "Query involves location, geography, or spatial distribution",
        "keywords": [
            "di mana", "lokasi", "letak", "geografi", "wilayah", "daerah",
            "peta", "koordinat", "dekat", "jauh", "kenapa di", "kenapa kota"
        ]
    },
    "behavioral": {
        "description": "Query involves human behavior, patterns, or habits",
        "keywords": [
            "perilaku", "kebiasaan", "pola", "tren", "kenapa orang", "kenapa manusia",
            "mengapa orang", "pilihan", "preferensi", "keputusan"
        ]
    },
    "human_place": {
        "description": "Query has explicit Human–Place relation (assigned automatically when HP anchor passes)",
        "keywords": [
            "tempat tinggal", "rumah", "hunian", "kota", "tanah", "pemukiman",
            "ruang hidup", "desa", "kampung", "menetap", "bermukim"
        ]
    }
}

# Intents that strongly imply a Human–Place connection
HUMAN_PLACE_INTENTS = {"urban", "geographic", "historical", "origin", "psychological"}

# Intents that mark a topic as likely PROCEDURAL (not editorial/knowledge storytelling)
PROCEDURAL_ONLY_INTENTS = {"procedural"}


def classify_intent(query: str, context: str = "") -> Dict[str, Any]:
    """
    Classifies a query into one or more intent classes.
    
    Args:
        query: The search query or topic text
        context: Optional additional context
        
    Returns:
        dict with: intents (list), primary_intent, confidence_signals, 
                   human_place_implied, is_procedural_only
    """
    text = (query + " " + context).lower()
    matched_intents = []

    for intent_name, definition in INTENT_DEFINITIONS.items():
        hit_count = 0
        
        # Check keywords
        keywords_hit = [kw for kw in definition.get("keywords", []) if kw in text]
        hit_count += len(keywords_hit)
        
        # Check regex patterns
        patterns_hit = []
        for pattern in definition.get("patterns", []):
            if re.search(pattern, text):
                patterns_hit.append(pattern)
                hit_count += 2  # patterns count more than keywords

        if hit_count > 0:
            matched_intents.append({
                "intent": intent_name,
                "description": definition["description"],
                "hit_count": hit_count,
                "matched_keywords": keywords_hit,
                "matched_patterns": patterns_hit
            })

    # Sort by hit count descending
    matched_intents.sort(key=lambda x: x["hit_count"], reverse=True)

    intent_names = [i["intent"] for i in matched_intents]
    primary_intent = intent_names[0] if intent_names else "explanatory"

    # If the top hit is generic 'explanatory' or 'behavioral', but a specific domain intent exists
    # (historical, economic, psychological, urban, etc.), choose the specific domain as primary_intent
    if primary_intent in ("explanatory", "behavioral") and len(intent_names) > 1:
        domain_intents = [
            i for i in intent_names
            if i not in ("explanatory", "behavioral", "procedural", "human_place")
        ]
        if domain_intents:
            primary_intent = domain_intents[0]

    # Determine if human_place is implied by intents
    human_place_implied = bool(
        HUMAN_PLACE_INTENTS.intersection(set(intent_names)) or
        "human_place" in intent_names
    )

    # Determine if purely procedural (low editorial value)
    is_procedural_only = (
        len(intent_names) == 1 and "procedural" in intent_names
    )

    return {
        "intents": intent_names,
        "intent_details": matched_intents,
        "primary_intent": primary_intent,
        "human_place_implied": human_place_implied,
        "is_procedural_only": is_procedural_only,
        "confidence": "high" if matched_intents and matched_intents[0]["hit_count"] >= 3 else
                      "medium" if matched_intents else "low"
    }


def classify_multiple_queries(queries: List[str]) -> List[Dict[str, Any]]:
    """Classify a list of queries and return their intent classifications."""
    return [
        {"query": q, **classify_intent(q)}
        for q in queries
    ]
