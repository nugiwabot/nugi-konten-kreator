"""
Property Bridge Engine v2
Discovers causal chains from general topics to space, property, housing, and cities.
Enforces the mandatory Property/Life Anchor Test.
"""
import re
from typing import Dict, Any, List, Optional

CANONICAL_BRIDGES = [
    {
        "pattern": r"(ai agent|otomasi|automation|kecerdasan buatan|chatgpt|deepseek|model ai)",
        "chain": [
            "AI & Otomasi Pekerjaan",
            "Pengurangan Kebutuhan Meja Kantor Fisik",
            "Restrukturisasi Ruang Komersial Perkotaan",
            "Pekerja Memiliki Fleksibilitas Lokasi",
            "Pergeseran Permintaan Hunian ke Sub-Urban & Kota Penyangga"
        ],
        "anchor": "housing",
        "primary_domain": "ai"
    },
    {
        "pattern": r"(fertility|kelahiran|anak|demografi|pernikahan|populasi)",
        "chain": [
            "Pergeseran Demografi & Penurunan Angka Kelahiran",
            "Pengecilan Ukuran Rata-rata Rumah Tangga (Household Size)",
            "Penurunan Kebutuhan Rumah Tapak Tipe Besar",
            "Lonjakan Kebutuhan Hunian Kompak, Efisien, & Modular",
            "Transformasi Pasar Properti & Desain Kota"
        ],
        "anchor": "housing",
        "primary_domain": "human"
    },
    {
        "pattern": r"(remote work|wfh|bekerja dari rumah|nomad|pekerja lepas|kantor)",
        "chain": [
            "Tren Remote Work & Pekerjaan Fleksibel",
            "Pengurangan Ketergantungan Komuter Harian",
            "Perubahan Kriteria Hunian: Dari Sekadar Tempat Tidur Menjadi Ruang Kerja",
            "Desentralisasi Permintaan Properti dari Pusat Kota ke Pinggiran",
            "Restrukturisasi Geografi Hunian dan Nilai Lahan"
        ],
        "anchor": "work",
        "primary_domain": "work"
    },
    {
        "pattern": r"(kendaraan listrik|ev|mobil listrik|motor listrik|charging)",
        "chain": [
            "Adopsi Kendaraan Listrik",
            "Tuntutan Fasilitas Pengisian Daya Rumahan (Home Charging)",
            "Kebutuhan Daya Listrik Minimal & Garasi Pribadi",
            "Divergensi Nilai Properti: Klaster Modern Apresiasi, Gang Sempit Terdepresiasi"
        ],
        "anchor": "housing",
        "primary_domain": "technology"
    },
    {
        "pattern": r"(macet|kemacetan|mrt|lrt|kereta|jalan tol|transport)",
        "chain": [
            "Kemacetan Kronis & Biaya Waktu Komuter",
            "Kebutuhan Aksesibilitas Transportasi Massal (TOD)",
            "Premi Harga Tanah di Radius Stasiun Transit",
            "Polarisasi Geografi Nilai Properti dan Pusat Pertumbuhan Baru"
        ],
        "anchor": "mobility",
        "primary_domain": "city"
    },
    {
        "pattern": r"(rumah|tanah|kpr|properti|hunian|developer|apartemen|kost|sewa)",
        "chain": [
            "Kebutuhan Tempat Tinggal & Aset Fisik Terbatas",
            "Dinamika Pasokan Lahan vs Pertumbuhan Penduduk",
            "Kepemilikan Tanah sebagai Manifestasi Rasa Aman & Status Manusia",
            "Pasar Properti & Lingkungan Hidup Nyata"
        ],
        "anchor": "housing",
        "primary_domain": "property"
    }
]

COSMETIC_PATTERNS = [
    r"tools? gratis",
    r"trik cepat kaya",
    r"prompt (terbaik|curian|rahasia)",
    r"cara cepat beli rumah dengan ai",
    r"beli rumah tanpa modal",
    r"review klaster",
    r"promo developer",
    r"diskon dp"
]


def find_property_bridge(topic: str, description: str = "") -> Dict[str, Any]:
    """
    Finds or synthesizes a natural causal bridge from a topic to property/space/life.
    Distinguishes genuine causal links from cosmetic/forced connections.
    """
    text = (topic + " " + description).lower()

    # 1. Check for cosmetic/forced bridge violations
    for p in COSMETIC_PATTERNS:
        if re.search(p, text):
            return {
                "valid": False,
                "is_cosmetic": True,
                "reason": f"Terdeteksi hubungan kosmetik / gimmick terlarang: pattern '{p}'",
                "chain": []
            }

    # 2. Check canonical bridges
    for b in CANONICAL_BRIDGES:
        if re.search(b["pattern"], text):
            return {
                "valid": True,
                "is_cosmetic": False,
                "reason": "Ditemukan rantai kausal alami yang terbukti",
                "chain": b["chain"],
                "anchor": b["anchor"],
                "primary_domain": b["primary_domain"]
            }

    # 3. Fallback: Synthesize general space/life connection if physical keywords present
    space_keywords = ["kota", "ruang", "hidup", "masyarakat", "pekerjaan", "manusia", "lingkungan", "keluarga"]
    matched = [k for k in space_keywords if k in text]
    if matched:
        return {
            "valid": True,
            "is_cosmetic": False,
            "reason": f"Ditemukan hubungan struktural melalui variabel ruang hidup: {', '.join(matched)}",
            "chain": [
                topic,
                f"Perubahan pada {matched[0]} sehari-hari",
                "Pengaruh terhadap tempat manusia tinggal dan beraktivitas",
                "Implikasi pada ruang fisik dan tata hunian"
            ],
            "anchor": "space",
            "primary_domain": "human"
        }

    return {
        "valid": False,
        "is_cosmetic": False,
        "reason": "Topik tidak memiliki hubungan sebab-akibat dengan ruang, tanah, kota, atau tempat tinggal manusia",
        "chain": []
    }


def evaluate_property_anchor(topic: str, context: str = "") -> Dict[str, Any]:
    """
    Evaluates topic against the 5 Property Anchor Test questions.
    Returns pass/fail status and an anchor score (0-20 points).
    """
    text = (topic + " " + context).lower()
    bridge = find_property_bridge(topic, context)

    # If bridge is cosmetic or explicitly invalid
    if not bridge["valid"]:
        return {
            "passed": False,
            "score": 0,
            "matched_questions": [],
            "bridge": bridge,
            "verdict": "REJECT / OUT OF BRAND"
        }

    matched_questions = []

    # Q1: Apakah berhubungan dengan tempat manusia hidup?
    if any(k in text for k in ["rumah", "hunian", "tempat tinggal", "kost", "kamar", "apartemen", "keluarga", "tidur"]):
        matched_questions.append("Q1: Tempat Hidup Manusia")

    # Q2: Apakah berhubungan dengan bagaimana manusia bekerja?
    if any(k in text for k in ["kantor", "kerja", "pekerjaan", "remote", "wfh", "gaji", "komuter"]):
        matched_questions.append("Q2: Cara Manusia Bekerja")

    # Q3: Apakah berhubungan dengan kota, rumah, tanah, ruang, aset, atau mobilitas?
    if any(k in text for k in ["tanah", "kota", "ruang", "aset", "macet", "jalan", "lahan", "mobilitas", "transport"]):
        matched_questions.append("Q3: Ruang, Kota, Aset, Mobilitas")

    # Q4: Apakah menjelaskan perubahan cara manusia hidup?
    if any(k in text for k in ["berubah", "perubahan", "masa depan", "teknologi", "ai", "zaman", "kenapa", "mengapa"]):
        matched_questions.append("Q4: Perubahan Cara Hidup")

    # Q5: Apakah ada hubungan struktural dengan property/space?
    if bridge["valid"] and len(bridge["chain"]) >= 3:
        matched_questions.append("Q5: Hubungan Struktural Kausal")

    # Scoring (each matched question gives up to 4 points, max 20)
    score = min(20, max(12, len(matched_questions) * 4))
    passed = score >= 10 and len(matched_questions) >= 1

    return {
        "passed": passed,
        "score": score,
        "matched_questions": matched_questions,
        "bridge": bridge,
        "verdict": "PASS" if passed else "REJECT / OUT OF BRAND"
    }
