"""
engine/pipeline/visual_requirements.py
======================================
Transforms parsed script sections into a sequence of dynamic visual shot requirements.

Editing Principles:
  - Faceless visual essay / mini-documentary aesthetic
  - No static slideshows: longer sections are cut into dynamic sub-shots (3–7s pacing)
  - Progression follows narrative meaning:
      working human → AI/tech → pressure/exhaustion → data/proof → metaphor → resolution
  - Short, punchy text overlays for core phrases
  - Prioritizes real archival footage, documentary photos, and visual metaphors
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.pipeline.script_parser import NarasiScript, ScriptSection

# ── 5 Visual Requirement Classes (Section 4) ─────────────────────────────────
REAL_REQUIRED = "REAL_REQUIRED"
REAL_PREFERRED = "REAL_PREFERRED"
GENERIC_ALLOWED = "GENERIC_ALLOWED"
NO_BROLL = "NO_BROLL"
REMOTION_REQUIRED = "REMOTION_REQUIRED"

# ── Source Roles (Section 12) ────────────────────────────────────────────────
PRIMARY_EVIDENCE = "PRIMARY_EVIDENCE"
DIRECT_CONTEXT = "DIRECT_CONTEXT"
GENERIC_ATMOSPHERE = "GENERIC_ATMOSPHERE"
ARCHIVAL_REFERENCE = "ARCHIVAL_REFERENCE"
DOCUMENT = "DOCUMENT"
MOTION_GRAPHICS = "MOTION_GRAPHICS"
NO_VISUAL = "NO_VISUAL"


@dataclass
class VisualShotRequirement:
    """Requirement for a single visual shot on the timeline."""
    shot_id: str
    section_index: int
    section_name: str
    section_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    visual_description: str
    search_query: str
    fallback_queries: List[str] = field(default_factory=list)
    text_overlay: str = ""
    preferred_media_type: str = "any"  # "video", "image", or "any"
    visual_metaphor: str = ""

    # Evidence-Based Retrieval fields (Sections 17-19)
    visual_requirement: str = GENERIC_ALLOWED
    visual_type: str = "METAPHOR"
    entity_type: str = ""
    entities: List[str] = field(default_factory=list)
    era: str = "auto"
    future_mode: str = ""  # FORECAST, RESEARCH_BACKED, PROJECTION, CONCEPT, SPECULATIVE, GENERATED
    source_role: str = GENERIC_ATMOSPHERE
    motion_spec: Optional[Dict[str, Any]] = None
    search_required: bool = True

    # Human relatability alignment for visual retrieval.
    primary_human_basic_need: str = ""
    life_lens: str = ""
    human_basic_need_score: float = 0.0
    life_lens_score: float = 0.0
    everyday_relevance_score: float = 0.0
    human_place_relevance_score: float = 0.0
    human_alignment_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full retrieval contract without implying assets exist."""
        data = asdict(self)
        data["query"] = self.search_query
        data["search_query"] = self.search_query
        data["start_frame"] = self.start_frame
        data["end_frame"] = self.end_frame
        data["duration_frames"] = self.duration_frames
        data["visual_evidence_policy"] = "VISUALS_DO_NOT_SUBSTITUTE_FOR_CLAIM_EVIDENCE"
        data["asset_availability"] = "NOT_CHECKED"
        data["rights_status"] = "NOT_CHECKED"
        return data

    @property
    def start_frame(self) -> int:
        return int(round(self.start_seconds * 30))

    @property
    def end_frame(self) -> int:
        return int(round(self.end_seconds * 30)) - 1

    @property
    def duration_frames(self) -> int:
        return max(1, self.end_frame - self.start_frame + 1)


# ── Generic Linguistic Patterns & Rules (Content-Agnostic) ───────────────────

_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}\s+(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember|january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4})\b", re.IGNORECASE),
    re.compile(r"\b((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})\b", re.IGNORECASE),
    re.compile(r"\b(1[6-9][0-9]{2}|200[0-9]|201[0-9]|202[0-9])\b"),
]

_NO_BROLL_PHRASES = [
    "tapi di sinilah masalah sebenarnya dimulai",
    "di sinilah masalah sebenarnya dimulai",
    "pertanyaannya kemudian berubah",
    "yang berubah ternyata bukan rumahnya",
    "mungkin kita selama ini melihat masalah ini dari arah yang salah",
    "tapi di sinilah semuanya berubah",
    "di sinilah semuanya berubah",
    "tapi di sinilah masalahnya",
    "pertanyaannya kemudian",
    "pertanyaan besarnya adalah",
    "namun pertanyaannya",
    "mungkin kita salah melihat",
    "lalu apa yang sebenarnya terjadi",
    "tapi di sinilah",
]

_STAT_PATTERNS = [
    re.compile(r"meningkat\s+dari\s+(.+?)\s+menjadi\s+(.+)", re.IGNORECASE),
    re.compile(r"meningkat\s+(?:dua|tiga|empat|lima|\d+)\s+kali\s+lipat", re.IGNORECASE),
    re.compile(r"(?:dua|tiga|empat|lima|\d+)\s+kali\s+lipat\s+dalam\s+\d+\s+(?:tahun|bulan|dekade)", re.IGNORECASE),
    re.compile(r"\b\d+[\.,]?\d*\s*%", re.IGNORECASE),
    re.compile(r"\b(populasi|harga rumah|biaya hidup|data statistik|angka kemiskinan|pertumbuhan ekonomi|pdb|inflasi|penjualan)\b.*\b(meningkat|melonjak|naik|turun|berlipat|tumbuh)\b", re.IGNORECASE),
    re.compile(r"\b(meningkat|melonjak|tumbuh)\s+dua\s+kali\s+lipat\b", re.IGNORECASE),
]


_FUTURE_MODE_CUES = {
    "FORECAST": ("forecast", "forecasts", "ramalan", "prakiraan"),
    "RESEARCH_BACKED": ("research-backed", "research backed", "berdasarkan riset", "didukung riset"),
    "PROJECTION": ("projection", "projected", "proyeksi", "diproyeksikan"),
    "SPECULATIVE": ("speculative", "speculation", "spekulatif", "spekulasi"),
    "GENERATED": ("generated", "ai-generated", "imagined", "rekaan", "buatan ai"),
    "CONCEPT": ("concept", "conceptual", "konsep", "futuristic", "futuristik", "masa depan", "future"),
}


def classify_future_intent(text: str) -> str:
    """Label future-oriented visuals so illustrative media is never future evidence."""
    lower = (text or "").lower()
    for mode in ("FORECAST", "RESEARCH_BACKED", "PROJECTION", "SPECULATIVE", "GENERATED", "CONCEPT"):
        if any(cue in lower for cue in _FUTURE_MODE_CUES[mode]):
            return mode
    return ""


def classify_visual_era(text: str) -> str:
    """Classify a shot's stated time context without interpreting visuals as proof."""
    lower = (text or "").lower()
    future_cues = (
        "future", "futuristic", "masa depan", "futuristik", "speculative", "spekulatif",
        "near-future", "forecast", "ramalan", "prakiraan", "projection", "proyeksi",
    )
    if re.search(r"\b20(?:3[0-9]|[4-9][0-9])\b", lower) or any(cue in lower for cue in future_cues):
        return "future"
    if any(cue in lower for cue in ("hari ini", "saat ini", "sekarang", "today", "current", "present day", "kontemporer")):
        return "present"
    if any(cue in lower for cue in ("sejarah", "historical", "historic", "masa lalu", "zaman", "abad", "archival", "arsip", "perang dunia")) or re.search(r"\b(1[6-9][0-9]{2}|20[0-2][0-9])\b", lower):
        return "historical"
    return "timeless"


def extract_entities(text: str) -> List[Dict[str, str]]:
    """
    Extract structured entities from natural language text using generic
    linguistic cues, syntactic patterns, and temporal rules.
    Works fully offline, deterministic, and content-agnostic.
    """
    if not text:
        return []

    entities: List[Dict[str, str]] = []
    seen: set = set()

    def _add_entity(ent_type: str, name: str):
        clean_name = name.strip(" ,.;:\"'()")
        if not clean_name or len(clean_name) < 2:
            return
        key = (ent_type, clean_name.lower())
        if key not in seen and not any(clean_name.lower() == k[1] for k in seen):
            seen.add(key)
            entities.append({"type": ent_type, "name": clean_name})

    # 1. Dates, Years, and Centuries
    for pat in _DATE_PATTERNS:
        for match in pat.finditer(text):
            _add_entity("DATE", match.group(0))

    century_matches = re.finditer(r"\b(abad\s+ke-\d+(?:\s*(?:sm|m))?|\d+(?:th|st|nd|rd)\s+century|era\s+[a-z]+|zaman\s+[a-z]+)\b", text, re.IGNORECASE)
    for match in century_matches:
        _add_entity("HISTORICAL_PERIOD", match.group(0))

    # 2. Events (generic triggers)
    event_generic = re.finditer(r"\b(d-day|d day|world war (?:i{1,3}|[12])|perang dunia (?:i{1,3}|ke-[12]|kedua|pertama)|revolusi industri|industrial revolution)\b", text, re.IGNORECASE)
    for match in event_generic:
        val = "D-Day" if match.group(0).lower() in ("d-day", "d day") else match.group(0)
        _add_entity("EVENT", val)

    event_cues = re.finditer(r"\b(?:pendaratan|landing(?:\s+on|\s+in)?|invasi|revolusi|proklamasi|krisis|tragedi|keynote)\s+([A-Z][a-zA-Z0-9\-]+(?:\s+[A-Z][a-zA-Z0-9\-]+)*)\b", text)
    for match in event_cues:
        _add_entity("EVENT", match.group(0))

    # 3. Documents (generic triggers)
    doc_cues = re.finditer(r"\b(?:surat|naskah|dokumen|deklarasi|perjanjian|treaty of|manuskrip)\s+([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*)\b", text, re.IGNORECASE)
    for match in doc_cues:
        _add_entity("DOCUMENT", match.group(0))

    # 4. Landmarks / Physical Structures (generic triggers)
    landmark_cues = re.finditer(r"\b(?:candi|tembok|gedung|monumen|menara|pabrik|jembatan)\s+([A-Z][a-zA-Z0-9\-]+(?:\s+[A-Z][a-zA-Z0-9\-]+)*)\b", text)
    for match in landmark_cues:
        _add_entity("LANDMARK", match.group(0))
    landmark_suffix = re.finditer(r"\b([A-Z][a-zA-Z0-9\-]+(?:\s+[A-Z][a-zA-Z0-9\-]+)*\s+(?:Wall|Tower|Factory|Temple|Monument|Bridge))\b", text)
    for match in landmark_suffix:
        _add_entity("LANDMARK", match.group(0))

    # 5. Organizations (generic triggers)
    org_cues = re.finditer(r"\b(pasukan\s+[A-Z][a-zA-Z0-9\-]+|tentara\s+[A-Z][a-zA-Z0-9\-]+|allied forces|axis powers)\b", text, re.IGNORECASE)
    for match in org_cues:
        _add_entity("ORGANIZATION", match.group(0))

    # 6. Products / Technologies (generic triggers)
    prod_verbs = re.finditer(r"\b(?:memperkenalkan|merilis|menciptakan)\s+([A-Z0-9][a-zA-Z0-9\-]+(?:\s+[A-Za-z0-9\-]+)?)\b", text)
    for match in prod_verbs:
        _add_entity("PRODUCT", match.group(1))
    prod_cues = re.finditer(r"\b(iphone|ipad|macintosh|pc|computer|komputer|smartphone|assembly line|steam engine)\b", text, re.IGNORECASE)
    for match in prod_cues:
        _add_entity("PRODUCT", match.group(0))

    # 7. Geographic Locations / Places / Cities (preposition + Capitalized word)
    place_preps = re.finditer(r"\b(?:di|ke|dari|in|at|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    stopwords_place = {"Indonesia", "Pagi", "Sore", "Malam", "Tahun", "Bulan", "Hari", "Sana", "Sini", "Depan", "Belakang", "Dalam", "Luar"}
    for match in place_preps:
        candidate = match.group(1).strip()
        if candidate not in stopwords_place:
            _add_entity("PLACE", candidate)
    geo_cues = re.finditer(r"\b(?:kota|negara|pulau|pantai|provinsi|city of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    for match in geo_cues:
        _add_entity("PLACE", match.group(1))

    # Mid-sentence capitalized proper words (e.g. Jakarta, Tokyo, Batavia, London)
    mid_caps = re.finditer(r"\b([A-Z][a-z]{2,})\b", text)
    stopwords_mid = {
        "Namun", "Tetapi", "Lalu", "Ketika", "Setelah", "Sementara", "Bahkan",
        "Pagi", "Siang", "Sore", "Malam", "Hari", "Bulan", "Tahun", "Abad", "Zaman", "Era",
        "Ada", "Bisa", "Jika", "Kalau", "Yang", "Untuk", "Dengan", "Dalam", "Dari", "Pada",
        "Dan", "Atau", "Serta", "Juga", "Hanya", "Akan", "Sudah", "Masih"
    }
    for match in mid_caps:
        if match.start() > 0:
            word = match.group(1).strip()
            if word not in stopwords_mid and not any(word.lower() in k[1] for k in seen):
                _add_entity("PLACE", word)

    # 8. Persons (Multi-word capitalized phrases or capitalized names with role triggers)
    person_cues = re.finditer(r"\b(?:tokoh|ilmuwan|presiden|ditemukan oleh|diciptakan oleh|dipimpin oleh)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    for match in person_cues:
        _add_entity("PERSON", match.group(1))

    multi_caps = re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
    stopwords_caps = {
        "Perhatikan Ini", "Ada Yang", "Fakta Di", "Penyebab Sebenarnya", "Menurut Anda",
        "Pagi Hari", "Jam Kerja", "Beban Kognitif", "Tekanan Waktu", "Manusia Bukan",
        "Pada Tahun", "Pada Tanggal", "Pada Bulan", "Pasukan Sekutu", "Tembok Berlin", "Candi Prambanan"
    }
    for match in multi_caps:
        candidate = match.group(1).strip()
        if candidate in stopwords_caps:
            continue
        if not any(candidate.lower() in k[1] for k in seen):
            _add_entity("PERSON", candidate)

    return entities


_HUMAN_BASIC_NEED_CUES = {
    "safety": ["aman", "keamanan", "terlindungi", "bahaya", "risiko", "safety", "security"],
    "shelter": ["rumah", "hunian", "tempat tinggal", "berlindung", "kamar", "ruang pribadi", "shelter", "home"],
    "health": ["tidur", "sehat", "kesehatan", "capek", "lelah", "panas", "udara", "cahaya", "bising", "stres", "recovery"],
    "wealth": ["uang", "gaji", "biaya", "mahal", "murah", "harga", "cicilan", "waktu", "transportasi", "aset", "wealth", "cost"],
    "belonging": ["tetangga", "komunitas", "teman", "bersama", "kesepian", "belonging", "keluarga"],
    "status": ["status", "gengsi", "prestise", "alamat", "mewah", "status sosial"],
    "autonomy": ["privasi", "kendali", "kontrol", "bebas", "otonomi", "pilihan", "autonomy"],
    "family": ["pasangan", "anak", "keluarga", "suami", "istri", "keluarga muda"],
    "meaning": ["identitas", "kenangan", "berarti", "makna", "rumah masa kecil"],
    "curiosity": ["kenapa", "mengapa", "ternyata", "asal", "sejarah", "mengapa bisa", "curiosity"],
}

_LIFE_LENS_CUES = {
    "health": ["tidur", "sehat", "kesehatan", "capek", "lelah", "panas", "udara", "cahaya", "bising", "stres", "recovery", "berjalan kaki"],
    "wealth": ["uang", "gaji", "biaya", "mahal", "murah", "harga", "cicilan", "waktu", "transportasi", "aset", "produktif"],
    "relationship": ["tetangga", "pasangan", "anak", "keluarga", "komunitas", "teman", "privasi", "bersama", "kesepian"],
}

_HUMAN_LIFE_CUES = {
    "orang", "manusia", "pekerja", "karyawan", "keluarga", "pasangan", "anak",
    "tetangga", "orang tua", "profesional", "ibu", "ayah", "warga",
    "pulang", "berangkat", "bekerja", "tidur", "makan", "berjalan",
    "bermain", "istirahat", "komuter", "commute", "people", "person", "family",
    "worker", "neighbor", "couple", "child", "walking", "sleeping"
}

_PLACE_LIFE_CUES = {
    "rumah", "hunian", "kamar", "lingkungan", "perumahan", "kampung", "tetangga",
    "jalan", "trotoar", "taman", "kota", "kantor", "apartemen", "kos", "neighborhood",
    "home", "house", "apartment", "street", "sidewalk", "park", "city", "neighborhood"
}

def analyze_human_relatability(text: str) -> Dict[str, Any]:
    """Deterministic editorial mapping for human-related B-roll alignment."""
    lower = (text or "").lower()

    need_scores = {
        need: sum(1 for k in cues if k in lower)
        for need, cues in _HUMAN_BASIC_NEED_CUES.items()
    }
    top_need = max(need_scores, key=need_scores.get) if need_scores else ""
    need_hits = need_scores.get(top_need, 0)

    lens_scores = {
        lens: sum(1 for k in cues if k in lower)
        for lens, cues in _LIFE_LENS_CUES.items()
    }
    top_lens = max(lens_scores, key=lens_scores.get) if lens_scores else ""
    lens_hits = lens_scores.get(top_lens, 0)

    human_hits = sum(1 for cue in _HUMAN_LIFE_CUES if cue in lower)
    place_hits = sum(1 for cue in _PLACE_LIFE_CUES if cue in lower)

    human_basic_need_score = min(1.0, 0.35 + 0.16 * need_hits) if need_hits else 0.20
    life_lens_score = min(1.0, 0.35 + 0.16 * lens_hits) if lens_hits else 0.20
    everyday_relevance_score = min(1.0, 0.25 + 0.10 * min(human_hits, 7)) if human_hits else 0.15
    human_place_relevance_score = min(1.0, 0.25 + 0.10 * min(place_hits, 7)) if place_hits else 0.15

    if human_hits and place_hits:
        everyday_relevance_score = min(1.0, everyday_relevance_score + 0.10)
        human_place_relevance_score = min(1.0, human_place_relevance_score + 0.10)

    alignment = round(
        0.35 * human_basic_need_score
        + 0.20 * life_lens_score
        + 0.25 * everyday_relevance_score
        + 0.20 * human_place_relevance_score,
        4,
    )

    return {
        "human_basic_need": top_need,
        "life_lens": top_lens,
        "human_basic_need_score": round(human_basic_need_score, 4),
        "life_lens_score": round(life_lens_score, 4),
        "everyday_relevance_score": round(everyday_relevance_score, 4),
        "human_place_relevance_score": round(human_place_relevance_score, 4),
        "human_alignment_score": alignment,
        "has_human_life_scene": human_hits > 0,
        "has_place_scene": place_hits > 0,
    }

def classify_visual_requirement(
    text: str,
) -> Tuple[str, str, List[Dict[str, str]], Optional[Dict[str, Any]], str]:
    """
    Classify a natural language text / sentence into one of the 5 visual requirement classes:
    (REAL_REQUIRED, REAL_PREFERRED, GENERIC_ALLOWED, NO_BROLL, REMOTION_REQUIRED)

    Returns:
        (visual_requirement, visual_type, entities, motion_spec, source_role)
    """
    if not text or not text.strip():
        return (GENERIC_ALLOWED, "METAPHOR", [], None, GENERIC_ATMOSPHERE)

    lower = text.lower().strip()

    # 1. Check NO_BROLL (narrative pause / rhetorical shift)
    for phrase in _NO_BROLL_PHRASES:
        if phrase in lower:
            return (NO_BROLL, "narrative_pause", [], None, NO_VISUAL)

    # 2. Check REMOTION_REQUIRED (statistics / growth / data visualization)
    for spat in _STAT_PATTERNS:
        m = spat.search(lower)
        if m:
            subject_match = re.search(r"^(.*?)(?:\s+(?:meningkat|melonjak|naik|turun|tumbuh|berlipat))\b", text, re.IGNORECASE)
            if subject_match and subject_match.group(1).strip():
                headline = subject_match.group(1).strip()
            else:
                headline = text.strip()
            if len(headline) > 60:
                headline = headline[:57] + "..."
            headline = headline.title()

            chart_type = "bar_chart" if "meningkat dari" in lower or "naik dari" in lower else "statistic"
            motion_spec = {
                "type": chart_type,
                "data_needed": True,
                "headline": headline,
                "animation": "progressive_growth",
            }
            return (REMOTION_REQUIRED, "STATISTIC", [], motion_spec, MOTION_GRAPHICS)

    # 3. Extract entities dynamically
    entities = extract_entities(text)
    ent_types = {e["type"] for e in entities}

    # Metaphor check: e.g. "Manusia diperlakukan seperti mesin"
    if "seperti mesin" in lower or "bagaikan mesin" in lower:
        return (GENERIC_ALLOWED, "METAPHOR", entities, None, GENERIC_ATMOSPHERE)

    # 4. Check REAL_REQUIRED
    has_person = "PERSON" in ent_types
    has_event = "EVENT" in ent_types
    has_landmark = "LANDMARK" in ent_types
    has_product = "PRODUCT" in ent_types
    has_document = "DOCUMENT" in ent_types
    has_date = "DATE" in ent_types
    has_place = any(t in ent_types for t in ("PLACE", "CITY", "COUNTRY"))

    if has_person or has_event or has_landmark or has_product or has_document or (has_date and has_place):
        visual_type = "EVENT" if (has_event or (has_date and has_place)) else ("PERSON" if has_person else ("LANDMARK" if has_landmark else ("DOCUMENT" if has_document else "OBJECT")))
        source_role = DOCUMENT if has_document else PRIMARY_EVIDENCE
        return (REAL_REQUIRED, visual_type, entities, None, source_role)

    # 5. Check REAL_PREFERRED
    has_hist_period = "HISTORICAL_PERIOD" in ent_types
    lower_words = set(re.findall(r"\b\w+\b", lower))
    has_human_life = bool(lower_words & _HUMAN_LIFE_CUES)
    has_place_life = bool(lower_words & _PLACE_LIFE_CUES)
    if has_place or has_hist_period or has_human_life or has_place_life:
        if has_human_life and has_place_life:
            visual_type = "HUMAN_LIFE_IN_PLACE"
        elif has_human_life:
            visual_type = "HUMAN_LIFE"
        elif has_hist_period:
            visual_type = "HISTORICAL_CONTEXT"
        else:
            visual_type = "LOCATION"
        return (REAL_PREFERRED, visual_type, entities, None, DIRECT_CONTEXT)

    # 6. Default: GENERIC_ALLOWED
    return (GENERIC_ALLOWED, "ATMOSPHERE", entities, None, GENERIC_ATMOSPHERE)


class VisualRequirementsGenerator:
    """Generates visual shot sequences for parsed narratives (Content-Agnostic)."""

    def generate_shots_for_narrative(
        self, narrative: NarasiScript
    ) -> List[VisualShotRequirement]:
        """
        Produce a list of VisualShotRequirement items for the given narrative dynamically.
        Rely solely on intelligent automatic heuristic generation based on actual script content.
        """
        return self._build_heuristic(narrative)

    def _build_heuristic(self, narrative: NarasiScript) -> List[VisualShotRequirement]:
        shots: List[VisualShotRequirement] = []
        shot_counter = 1
        for sec in narrative.sections:
            sec_shots = self._build_section_heuristic(sec, narrative, shot_counter)
            shots.extend(sec_shots)
            shot_counter += len(sec_shots)
        return shots

    def _build_section_heuristic(
        self, sec: ScriptSection, narrative: NarasiScript, start_counter: int
    ) -> List[VisualShotRequirement]:
        if sec.duration_seconds <= 7.0:
            num_shots = 1
        elif sec.duration_seconds <= 15.0:
            num_shots = 2
        elif sec.duration_seconds <= 25.0:
            num_shots = 3
        else:
            num_shots = 4

        shot_dur = sec.duration_seconds / num_shots
        results: List[VisualShotRequirement] = []

        keywords = self._extract_keywords(sec.text)
        v_req, v_type, ents, m_spec, s_role = classify_visual_requirement(sec.text)
        visual_era = classify_visual_era(sec.text)
        future_mode = classify_future_intent(sec.text) if visual_era == "future" else ""
        human_map = analyze_human_relatability(sec.text)
        ent_names = [e["name"] for e in ents]
        primary_ent_type = ents[0]["type"] if ents else ""

        for i in range(num_shots):
            st = sec.start_seconds + i * shot_dur
            et = sec.end_seconds if i == num_shots - 1 else sec.start_seconds + (i + 1) * shot_dur
            shot_id = f"shot_{narrative.index:02d}_{start_counter + i:02d}"

            if v_req == REAL_REQUIRED and ent_names:
                core_entity = " ".join(ent_names[:3])
                q = f"{core_entity} archival documentary"
                overlay = ent_names[0]
            elif v_req == REAL_PREFERRED and ent_names:
                q = f"{' '.join(ent_names)} documentary"
                overlay = ent_names[0]
            elif v_req == REAL_PREFERRED and v_type in ("HUMAN_LIFE", "HUMAN_LIFE_IN_PLACE"):
                q = f"{' '.join(keywords[:4])} real people real place documentary"
                overlay = " ".join(w.capitalize() for w in keywords[:2])
            elif keywords:
                q = f"{' '.join(keywords[:3])} cinematic documentary"
                overlay = " ".join(w.capitalize() for w in keywords[:2])
            else:
                q = "documentary scene"
                overlay = sec.name

            fallbacks = [
                f"{' '.join(keywords[:2])} footage" if keywords else "documentary footage",
                "archival reference footage"
            ]

            results.append(
                VisualShotRequirement(
                    shot_id=shot_id,
                    section_index=sec.index,
                    section_name=sec.name,
                    section_type=sec.section_type,
                    start_seconds=st,
                    end_seconds=et,
                    duration_seconds=et - st,
                    visual_description=f"Visual {sec.section_type}: {q}",
                    search_query=q,
                    fallback_queries=fallbacks,
                    text_overlay=overlay,
                    preferred_media_type="any",
                    visual_metaphor=sec.section_type,
                    visual_requirement=v_req,
                    visual_type=v_type,
                    entity_type=primary_ent_type,
                    entities=ent_names,
                    source_role=s_role,
                    era=visual_era,
                    future_mode=future_mode,
                    motion_spec=m_spec,
                    search_required=(v_req not in (NO_BROLL, REMOTION_REQUIRED)),
                    primary_human_basic_need=human_map["human_basic_need"],
                    life_lens=human_map["life_lens"],
                    human_basic_need_score=human_map["human_basic_need_score"],
                    life_lens_score=human_map["life_lens_score"],
                    everyday_relevance_score=human_map["everyday_relevance_score"],
                    human_place_relevance_score=human_map["human_place_relevance_score"],
                    human_alignment_score=human_map["human_alignment_score"],
                )
            )

        return results

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        stopwords = {
            "yang", "untuk", "dengan", "dalam", "bisa", "lebih", "kita", "karena",
            "sudah", "kalau", "nggak", "pada", "oleh", "dari", "akan", "kamu",
            "anda", "juga", "hanya", "mereka", "secara", "seperti", "sebenarnya"
        }
        filtered = [w for w in words if w not in stopwords]
        return filtered[:5] if filtered else ["documentary", "visual"]
