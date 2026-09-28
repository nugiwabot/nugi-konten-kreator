"""
Topic Taxonomy and Classification Schema v2
"""
import re
from typing import Dict, Any, List

PRIMARY_DOMAINS = [
    "property",
    "city",
    "economy",
    "ai",
    "technology",
    "work",
    "human",
    "history",
    "future"
]

ANCHORS = [
    "housing",
    "land",
    "city",
    "space",
    "work",
    "ownership",
    "mobility"
]

LENSES = [
    "economics",
    "psychology",
    "sociology",
    "history",
    "technology",
    "business",
    "urbanism",
    "philosophy"
]

RESEARCH_MODES = [
    "evergreen",
    "current",
    "historical",
    "data_driven"
]

DNA_MATRICES = {
    "Matrix A": {"pair": "PROPERTY × HUMAN", "description": "Rasa aman, psikologi hunian, dan simbol status"},
    "Matrix B": {"pair": "PROPERTY × ECONOMY", "description": "Kenaikan harga tanah, disparitas upah vs harga rumah"},
    "Matrix C": {"pair": "PROPERTY × CITY", "description": "Pertumbuhan kota, aglomerasi tata ruang, kemacetan"},
    "Matrix D": {"pair": "AI × PROPERTY", "description": "Remote work, kantor fisik, geografi persebaran hunian"},
    "Matrix E": {"pair": "AI × HUMAN", "description": "Nilai keahlian manusia, otonomi berpikir, dan identitas"},
    "Matrix F": {"pair": "WORK × SPACE", "description": "Komuter, waktu tempuh, dan barter kenyamanan rumah"},
    "Matrix G": {"pair": "HISTORY × PROPERTY", "description": "Asal-usul pusat kota, sejarah agraria, tata ruang kolonial"},
    "Matrix H": {"pair": "FUTURE × PROPERTY", "description": "Arsitektur masa depan, smart space vs privasi"}
}

CONTENT_PORTFOLIO_TARGETS = {
    "property_and_housing": 0.40,
    "city_space_and_economy": 0.25,
    "ai_technology_and_work": 0.20,
    "human_history_and_future": 0.15
}


def classify_topic(topic: str, context: str = "") -> Dict[str, Any]:
    """
    Classifies a raw inquiry into standard v2 taxonomy metadata.
    """
    text = (topic + " " + context).lower()
    
    # 1. Primary Domain Classification
    if any(k in text for k in ["rumah", "properti", "kpr", "tanah", "hunian", "developer", "pengembang", "kost", "ruko"]):
        domain = "property"
    elif any(k in text for k in ["kota", "macet", "urban", "transport", "jalan", "mrt", "lrt", "pusat kota"]):
        domain = "city"
    elif any(k in text for k in ["ai", "kecerdasan buatan", "chatgpt", "deepseek", "agen ai", "komputasi", "algoritma"]):
        domain = "ai"
    elif any(k in text for k in ["gaji", "inflasi", "suku bunga", "biaya hidup", "ekonomi", "uang"]):
        domain = "economy"
    elif any(k in text for k in ["kantor", "remote work", "pekerjaan", "wfh", "karir", "komuter"]):
        domain = "work"
    elif any(k in text for k in ["sejarah", "kolonial", "zaman dulu", "asal-usul", "tempo doeloe"]):
        domain = "history"
    elif any(k in text for k in ["masa depan", "2050", "demografi", "generasi"]):
        domain = "future"
    else:
        domain = "human"

    # 2. Anchor Classification
    if any(k in text for k in ["tanah", "lahan"]):
        anchor = "land"
    elif any(k in text for k in ["kota", "urban", "kawasan", "daerah"]):
        anchor = "city"
    elif any(k in text for k in ["kantor", "kerja", "meja"]):
        anchor = "work"
    elif any(k in text for k in ["milik", "kepemilikan", "sertifikat", "aset"]):
        anchor = "ownership"
    elif any(k in text for k in ["macet", "komuter", "transport", "jalan", "kereta", "lrt", "mrt"]):
        anchor = "mobility"
    elif any(k in text for k in ["ruang", "space", "kamar", "lingkungan"]):
        anchor = "space"
    else:
        anchor = "housing"

    # 3. Lens Classification
    if any(k in text for k in ["sejarah", "kolonial", "asal-usul", "tempo doeloe"]):
        lens = "history"
    elif any(k in text for k in ["tata ruang", "arsitektur", "zonasi", "desain kota"]):
        lens = "urbanism"
    elif any(k in text for k in ["harga", "gaji", "biaya", "keuangan", "suku bunga", "investasi"]) or re.search(r"\buang\b", text):
        lens = "economics"
    elif any(k in text for k in ["psikolog", "rasa aman", "takut", "emosi", "status", "ingin"]):
        lens = "psychology"
    elif any(k in text for k in ["ai", "teknologi", "komputasi", "mesin"]):
        lens = "technology"
    elif any(k in text for k in ["masyarakat", "keluarga", "sosial", "tetangga"]):
        lens = "sociology"
    else:
        lens = "philosophy"

    # 4. Research Mode Detection
    if any(k in text for k in ["sejarah", "kolonial", "asal-usul", "dulu"]):
        mode = "historical"
    elif any(k in text for k in ["persen", "%", "angka", "data", "statistik", "bps", "survei", "rasio"]):
        mode = "data_driven"
    elif any(k in text for k in ["baru", "terkini", "minggu ini", "rilis", "kebijakan baru", "aturan baru"]):
        mode = "current"
    else:
        mode = "evergreen"

    # 5. DNA Matrix Pairing
    if domain == "property" and lens in ("psychology", "philosophy"):
        matrix = "Matrix A"
    elif domain == "property" and lens == "economics":
        matrix = "Matrix B"
    elif domain in ("city", "property") and lens in ("urbanism", "sociology"):
        matrix = "Matrix C"
    elif domain in ("ai", "technology") and anchor in ("housing", "land", "city"):
        matrix = "Matrix D"
    elif domain in ("ai", "technology") and lens in ("philosophy", "psychology"):
        matrix = "Matrix E"
    elif domain == "work" and anchor in ("space", "housing", "mobility"):
        matrix = "Matrix F"
    elif domain == "history" or lens == "history":
        matrix = "Matrix G"
    else:
        matrix = "Matrix H"

    return {
        "primary_domain": domain,
        "anchor": anchor,
        "lens": lens,
        "research_mode": mode,
        "dna_matrix": matrix
    }
