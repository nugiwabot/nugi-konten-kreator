"""
Human–Place Engine v3
Replaces Property Bridge Engine with a broader HUMAN × PLACE × CHANGE × WHY paradigm.

The key shift:
- Old: Property/Life Anchor Test (5 questions, requires explicit property/land/housing keywords)
- New: Human–Place Anchor Test (10 criteria, covers psychology, history, city, land, migration,
       economy, technology, culture — property is ONE valid thread, not mandatory)

A story is accepted when it naturally explains at least ONE of the 10 Human–Place relations.
A story is rejected ONLY when no meaningful Human–Place relationship exists.
"""
import re
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# 10 Human–Place Anchor Criteria
# ---------------------------------------------------------------------------
HUMAN_PLACE_CRITERIA = [
    {
        "id": "A",
        "name": "where_humans_live",
        "description": "Where humans live",
        "keywords": [
            "tempat tinggal", "rumah", "hunian", "pemukiman", "kost", "apartemen",
            "desa", "kampung", "kota", "perumahan", "perkampungan"
        ]
    },
    {
        "id": "B",
        "name": "why_humans_live_there",
        "description": "Why humans choose to live where they do",
        "keywords": [
            "kenapa tinggal", "alasan pindah", "migrasi", "urbanisasi", "relokasi",
            "pilih lokasi", "pilih tempat", "kenapa orang", "memilih tinggal"
        ]
    },
    {
        "id": "C",
        "name": "how_homes_are_shaped",
        "description": "How homes/housing are formed and shaped",
        "keywords": [
            "bentuk rumah", "desain rumah", "arsitektur", "struktur bangunan",
            "material bangunan", "evolusi rumah", "tipe hunian", "rumah purba",
            "rumah tradisional"
        ]
    },
    {
        "id": "D",
        "name": "how_cities_are_shaped",
        "description": "How cities are formed, designed, or transformed",
        "keywords": [
            "kota", "tata kota", "tata ruang", "urban", "pusat kota", "pertumbuhan kota",
            "pembentukan kota", "zonasi", "kawasan", "metropolitan", "perkotaan"
        ]
    },
    {
        "id": "E",
        "name": "how_land_is_used",
        "description": "How land is used, owned, or distributed",
        "keywords": [
            "tanah", "lahan", "kepemilikan tanah", "hak atas tanah", "penggunaan lahan",
            "pertanian", "konversi lahan", "agraria", "sertifikat", "pajak tanah"
        ]
    },
    {
        "id": "F",
        "name": "home_work_movement",
        "description": "How people move between home and work",
        "keywords": [
            "komuter", "perjalanan kerja", "macet", "jarak tempuh", "remote work",
            "wfh", "kantor", "transportasi", "mobilitas", "commute"
        ]
    },
    {
        "id": "G",
        "name": "access_to_space",
        "description": "How access to physical space changes",
        "keywords": [
            "akses", "ruang publik", "ruang terbuka", "keterjangkauan", "harga rumah",
            "sewa", "afordabilitas", "gentrifikasi", "penggusuran", "displacement"
        ]
    },
    {
        "id": "H",
        "name": "technology_changes_living_space",
        "description": "How technology/economy/history changes human living spaces",
        "keywords": [
            "teknologi", "ai", "ekonomi", "sejarah", "industri", "infrastruktur",
            "revolusi industri", "internet", "digitalisasi", "otomasi", "perubahan ekonomi"
        ]
    },
    {
        "id": "I",
        "name": "psychology_and_home",
        "description": "How human psychology affects relationship with home/place",
        "keywords": [
            "rasa aman", "psikologi", "nyaman", "identitas", "status", "keluarga",
            "teritorial", "rumah sebagai", "arti rumah", "makna rumah", "attachment"
        ]
    },
    {
        "id": "J",
        "name": "historical_systems_today",
        "description": "How historical systems created today's living environment",
        "keywords": [
            "sejarah", "kolonial", "asal-usul", "zaman dahulu", "tempo doeloe",
            "warisan", "sistem feodal", "hukum agraria", "asal mula", "pertama kali"
        ]
    }
]

# ---------------------------------------------------------------------------
# Canonical Human–Place Bridges
# These are proven causal chains that DON'T require explicit property keywords.
# ---------------------------------------------------------------------------
CANONICAL_HUMAN_PLACE_BRIDGES = [
    {
        "id": "bridge_ai_geography",
        "pattern": r"(ai agent|otomasi|automation|kecerdasan buatan|chatgpt|deepseek|model ai|llm)",
        "chain": [
            "AI & Otomasi Tugas Pekerjaan",
            "Restrukturisasi Cara Kerja Manusia",
            "Fleksibilitas Lokasi Kerja",
            "Pergeseran Kebutuhan Ruang: Dari Kantor ke Rumah",
            "Reorganisasi Geografis Tempat Tinggal Manusia"
        ],
        "place_relation": "technology_changes_living_space",
        "place_relation_type": "second_order",
        "primary_domain": "ai"
    },
    {
        "id": "bridge_work_city",
        "pattern": r"(pekerjaan|kerja|industri|lapangan kerja|ekonomi kota|pertumbuhan ekonomi)",
        "chain": [
            "Pertumbuhan Sektor Pekerjaan",
            "Migrasi Tenaga Kerja",
            "Permintaan Tempat Tinggal",
            "Pertumbuhan Kota",
            "Perubahan Pola Kehidupan Manusia"
        ],
        "place_relation": "how_cities_are_shaped",
        "place_relation_type": "direct",
        "primary_domain": "work"
    },
    {
        "id": "bridge_demographics",
        "pattern": r"(fertility|kelahiran|anak|demografi|pernikahan|populasi|penduduk)",
        "chain": [
            "Pergeseran Demografi & Ukuran Keluarga",
            "Perubahan Kebutuhan Ruang Hunian",
            "Transformasi Tipologi Rumah",
            "Dampak pada Kota & Tata Ruang"
        ],
        "place_relation": "how_homes_are_shaped",
        "place_relation_type": "direct",
        "primary_domain": "human"
    },
    {
        "id": "bridge_remote_work",
        "pattern": r"(remote work|wfh|bekerja dari rumah|nomad digital|kerja jarak jauh)",
        "chain": [
            "Tren Kerja Fleksibel & Remote Work",
            "Perubahan Kriteria Hunian Ideal",
            "Desentralisasi Permintaan dari Pusat Kota",
            "Reorganisasi Pola Tempat Tinggal"
        ],
        "place_relation": "home_work_movement",
        "place_relation_type": "direct",
        "primary_domain": "work"
    },
    {
        "id": "bridge_transport",
        "pattern": r"(macet|kemacetan|mrt|lrt|kereta|jalan tol|transportasi|komuter)",
        "chain": [
            "Infrastruktur Transportasi",
            "Aksesibilitas Kota",
            "Pola Komuter Harian",
            "Pilihan Lokasi Tempat Tinggal",
            "Nilai & Desirabilitas Wilayah"
        ],
        "place_relation": "home_work_movement",
        "place_relation_type": "direct",
        "primary_domain": "city"
    },
    {
        "id": "bridge_history_city",
        "pattern": r"(sejarah|kolonial|zaman|asal.?usul|tempo doeloe|zaman dahulu|peradaban|prasejarah)",
        "chain": [
            "Konteks Historis",
            "Sistem Sosial & Ekonomi di Masa Lalu",
            "Pembentukan Awal Pemukiman & Kota",
            "Warisan yang Membentuk Kehidupan Saat Ini"
        ],
        "place_relation": "historical_systems_today",
        "place_relation_type": "direct",
        "primary_domain": "history"
    },
    {
        "id": "bridge_psychology_home",
        "pattern": r"(psikologi|rasa aman|nyaman|identitas|status|takut|cemas|emosi|perasaan|attachment|ikatan)",
        "chain": [
            "Kebutuhan Psikologis Manusia",
            "Pencarian Rasa Aman & Kepastian",
            "Relasi Emosional dengan Tempat Tinggal",
            "Perilaku Kepemilikan & Hunian"
        ],
        "place_relation": "psychology_and_home",
        "place_relation_type": "direct",
        "primary_domain": "human"
    },
    {
        "id": "bridge_property_explicit",
        "pattern": r"(rumah|tanah|kpr|properti|hunian|developer|apartemen|kost|sewa|lahan|kepemilikan)",
        "chain": [
            "Kebutuhan Tempat Tinggal",
            "Dinamika Pasar Perumahan",
            "Kepemilikan vs Sewa sebagai Keputusan Hidup",
            "Implikasi Finansial & Sosial"
        ],
        "place_relation": "where_humans_live",
        "place_relation_type": "direct",
        "primary_domain": "property"
    },
    {
        "id": "bridge_city_economics",
        "pattern": r"(harga tanah|harga rumah|nilai lahan|mahal|terjangkau|ekonomi kota|gentrifikasi)",
        "chain": [
            "Ekonomi Perkotaan",
            "Permintaan vs Pasokan Ruang",
            "Akses Tempat Tinggal",
            "Konsekuensi Sosial & Kehidupan Manusia"
        ],
        "place_relation": "access_to_space",
        "place_relation_type": "direct",
        "primary_domain": "economy"
    }
]

# ---------------------------------------------------------------------------
# Hard Rejection Patterns (cosmetic/forced connections)
# ---------------------------------------------------------------------------
COSMETIC_PATTERNS = [
    r"tools?\s+gratis\s+\d+",
    r"\d+\s+tools?\s+(ai|gratis|terbaik)",
    r"prompt\s+(terbaik|curian|rahasia|gratis)",
    r"cara\s+cepat\s+kaya\s+dengan\s+ai",
    r"beli\s+rumah\s+tanpa\s+modal\s+100%",
    r"review\s+klaster\s+perumahan",
    r"promo\s+developer\s+(dp|diskon)",
    r"diskon\s+dp\s+hanya",
    r"booking\s+fee\s+hanya",
    r"tips\s+(instagram|tiktok|viral)\s+(gratis|cepat|terbaik)"
]

# Always-reject patterns (literal sales copy / spam)
HARD_REJECT_PATTERNS = [
    r"dijual\s+(rumah|kost|ruko|apartemen)\s+murah",
    r"tipe\s+\d+/\d+\s+cicilan\s+hanya",
    r"hubungi\s+marketing\s+gallery",
    r"siap\s+huni\s+sertifikat\s+hak\s+milik",
]


def find_human_place_bridge(topic: str, description: str = "") -> Dict[str, Any]:
    """
    Finds or synthesizes a genuine causal bridge from a topic to PLACE / HUMAN LIVING.
    
    Returns:
        dict with keys: valid, is_cosmetic, reason, chain, place_relation, 
                        place_relation_type, primary_domain
    """
    text = (topic + " " + description).lower()

    # 1. Hard reject — literal sales/spam
    for p in HARD_REJECT_PATTERNS:
        if re.search(p, text):
            return {
                "valid": False,
                "is_cosmetic": True,
                "reason": f"Terdeteksi konten penjualan/spam langsung: pattern '{p}'",
                "chain": [],
                "place_relation": None,
                "place_relation_type": None
            }

    # 2. Cosmetic bridge — forced connections with no real Human–Place depth
    for p in COSMETIC_PATTERNS:
        if re.search(p, text):
            return {
                "valid": False,
                "is_cosmetic": True,
                "reason": f"Terdeteksi koneksi kosmetik/dipaksakan: pattern '{p}'",
                "chain": [],
                "place_relation": None,
                "place_relation_type": None
            }

    # 3. Check canonical bridges (proven causal chains)
    for bridge in CANONICAL_HUMAN_PLACE_BRIDGES:
        if re.search(bridge["pattern"], text):
            return {
                "valid": True,
                "is_cosmetic": False,
                "reason": "Ditemukan rantai kausal Human–Place yang terbukti",
                "chain": bridge["chain"],
                "place_relation": bridge["place_relation"],
                "place_relation_type": bridge["place_relation_type"],
                "primary_domain": bridge.get("primary_domain", "human"),
                "bridge_id": bridge["id"]
            }

    # 4. Evaluate 10 Human–Place criteria directly
    matched_criteria = evaluate_human_place_criteria(text)
    if matched_criteria:
        best = matched_criteria[0]
        return {
            "valid": True,
            "is_cosmetic": False,
            "reason": f"Kriteria Human–Place terpenuhi: {best['name']} — {best['description']}",
            "chain": [
                topic,
                f"Aspek manusia: {best['description']}",
                "Pengaruh terhadap cara/tempat manusia hidup",
                "Koneksi dengan ruang fisik dan pengalaman hunian"
            ],
            "place_relation": best["name"],
            "place_relation_type": "inferred",
            "primary_domain": "human",
            "matched_criteria": [c["id"] for c in matched_criteria]
        }

    return {
        "valid": False,
        "is_cosmetic": False,
        "reason": (
            "Topik tidak memiliki hubungan bermakna dengan "
            "HUMAN × PLACE: tidak ada kaitan dengan cara manusia hidup, "
            "tempat tinggal, kota, ruang, tanah, mobilitas, atau psikologi hunian."
        ),
        "chain": [],
        "place_relation": None,
        "place_relation_type": None
    }


def evaluate_human_place_criteria(text: str) -> List[Dict[str, Any]]:
    """
    Evaluates text against all 10 Human–Place criteria.
    Returns matched criteria sorted by number of keyword hits.
    """
    matched = []
    for criterion in HUMAN_PLACE_CRITERIA:
        hits = [kw for kw in criterion["keywords"] if kw in text]
        if hits:
            matched.append({
                **criterion,
                "matched_keywords": hits,
                "hit_count": len(hits)
            })
    matched.sort(key=lambda x: x["hit_count"], reverse=True)
    return matched


def evaluate_human_place_anchor(topic: str, context: str = "") -> Dict[str, Any]:
    """
    Evaluates a topic against the Human–Place Anchor Test (10 criteria).
    
    Returns:
        dict with: passed, score (0-20), matched_criteria, bridge, verdict
    """
    text = (topic + " " + context).lower()
    bridge = find_human_place_bridge(topic, context)

    # If cosmetic or hard reject
    if not bridge["valid"]:
        return {
            "passed": False,
            "score": 0,
            "matched_criteria": [],
            "bridge": bridge,
            "verdict": "REJECT / NO HUMAN-PLACE CONNECTION"
        }

    matched_criteria = evaluate_human_place_criteria(text)

    # Score: each matched criterion contributes, capped at 20
    # At least 1 canonical bridge match = 12 baseline
    # Each additional criterion: +2 pts, capped at 20
    if bridge.get("bridge_id"):
        base_score = 14  # canonical bridge confirmed
    else:
        base_score = 12  # inferred from criteria keywords

    bonus = min(6, len(matched_criteria) * 2)
    score = min(20, base_score + bonus)

    passed = score >= 10 and bridge["valid"]

    return {
        "passed": passed,
        "score": score,
        "matched_criteria": [c["id"] for c in matched_criteria],
        "criteria_details": [
            {"id": c["id"], "name": c["name"], "description": c["description"],
             "matched_keywords": c.get("matched_keywords", [])}
            for c in matched_criteria
        ],
        "bridge": bridge,
        "verdict": "PASS" if passed else "REJECT / WEAK HUMAN-PLACE CONNECTION"
    }


# ---------------------------------------------------------------------------
# Backward compatibility alias
# (code that imported property_bridge can import from here as needed)
# ---------------------------------------------------------------------------
def find_property_bridge(topic: str, description: str = "") -> Dict[str, Any]:
    """
    Backward compatible alias. 
    Calls find_human_place_bridge and maps result to old property_bridge format.
    """
    result = find_human_place_bridge(topic, description)
    # Map new keys to old expected keys
    result.setdefault("anchor", _place_relation_to_anchor(result.get("place_relation")))
    return result


def evaluate_property_anchor(topic: str, context: str = "") -> Dict[str, Any]:
    """
    Backward compatible alias. Calls evaluate_human_place_anchor.
    """
    return evaluate_human_place_anchor(topic, context)


def _place_relation_to_anchor(place_relation: Optional[str]) -> str:
    """Maps new place_relation names to legacy anchor names."""
    mapping = {
        "where_humans_live": "housing",
        "why_humans_live_there": "housing",
        "how_homes_are_shaped": "housing",
        "how_cities_are_shaped": "city",
        "how_land_is_used": "land",
        "home_work_movement": "mobility",
        "access_to_space": "space",
        "technology_changes_living_space": "space",
        "psychology_and_home": "housing",
        "historical_systems_today": "space"
    }
    return mapping.get(place_relation or "", "space")
