"""
engine/editorial/script_auditor.py
==================================
Python Script Fact & Narrative Verification Engine for Nugi Content Creator.

Core Principle:
---------------
EVIDENCE-BACKED FACTUAL SUPPORT.
We do NOT claim to be an absolute "truth detector".
Instead, this auditor evaluates:
"Is the available evidence sufficiently strong, relevant, and consistent
to support the claim as formulated in the script?"

Features:
- Structured claim extraction (Quantitative, Temporal, Historical, Causal,
  Comparative, Population, Universal, Scientific, Economic, Technology,
  Urban/Property, Behavioral, Opinion, Speculation)
- Evidence resolution & multi-source evaluation via existing infrastructure
- Fine-grained entailment & nuance matching (Supported, Partially Supported,
  Needs Context, Unverified, Contradicted, Conflicting Evidence)
- Overclaim & Causal Overclaim detection (correlation vs causation)
- Scope & Demographic Mismatch detection
- Temporal validity & recency check
- Numerical & metric consistency check
- Priority / Severity assignment (Critical, High, Medium, Low)
- Actionable, non-destructive recommendations (does NOT mutate scripts)
- Seamless integration with Human–Place and Editorial Identity Engines
"""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

# Reuse existing research and source classification infrastructure
from engine.providers.search import classify_source_quality, WebResearchProvider, DDGSWebResearchProvider
from engine.pipeline.research_runner import ResearchRunner

logger = logging.getLogger(__name__)


# =============================================================================
# 1. ENUMS & DATA MODELS
# =============================================================================

class ClaimType(str, Enum):
    QUANTITATIVE = "QUANTITATIVE"       # Angka, persentase, kelipatan, rasio
    TEMPORAL = "TEMPORAL"               # Waktu, tahun, era, "sejak...", "saat ini"
    HISTORICAL = "HISTORICAL"           # Masa lampau, peradaban, nenek moyang
    CAUSAL = "CAUSAL"                   # Sebab-akibat ("menyebabkan", "memicu")
    COMPARATIVE = "COMPARATIVE"         # Komparasi ("lebih X daripada Y", "menyusut")
    POPULATION = "POPULATION"           # Cakupan warga/masyarakat ("orang Indonesia", "pekerja")
    UNIVERSAL = "UNIVERSAL"             # Generalisasi mutlak ("semua", "selalu", "tidak pernah")
    SCIENTIFIC = "SCIENTIFIC"           # Biologi, otak, hormon, medis, fisika
    ECONOMIC = "ECONOMIC"               # Uang, gaji, harga, KPR, inflasi, bunga
    TECHNOLOGY = "TECHNOLOGY"           # AI, server, komputasi, listrik
    URBAN_PROPERTY = "URBAN_PROPERTY"   # Kota, tanah, kavling, hunian, tata ruang
    BEHAVIORAL = "BEHAVIORAL"           # Kebiasaan manusia, psikologi teritori
    OTHER_FACTUAL = "OTHER_FACTUAL"     # Klaim faktual umum
    OPINION = "OPINION"                 # Pernyataan subjektif / nilai rasa
    SPECULATION = "SPECULATION"         # Dugaan / hipotesis belum terbukti


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"                       # Didukung langsung oleh sumber primer/kredibel
    SUPPORTED = "SUPPORTED"                     # Didukung kuat secara substansial
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED" # Didukung sebagian, namun wording lebih kuat dari data
    NEEDS_CONTEXT = "NEEDS_CONTEXT"             # Membutuhkan konteks penting (temporal, scope, metode)
    UNVERIFIED = "UNVERIFIED"                   # Belum ditemukan evidence cukup (UNVERIFIED != FALSE)
    CONTRADICTED = "CONTRADICTED"               # Evidence kredibel bertentangan langsung dengan klaim
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE" # Sumber-sumber kredibel saling bertentangan
    OPINION = "OPINION"                         # Pandangan subjektif, tidak dinilai sebagai fakta
    SPECULATION = "SPECULATION"                 # Dugaan / spekulasi


class Severity(str, Enum):
    CRITICAL = "CRITICAL"   # Kontradiksi fatal, angka inti salah, fabrikasi data
    HIGH = "HIGH"           # Klaim sentral tidak didukung, overklaim kausalitas kunci
    MEDIUM = "MEDIUM"       # Scope/temporal mismatch, overklaim wording pendukung
    LOW = "LOW"             # Fakta ilustrasi kecil, butuh sedikit konteks tambahan


class OverallStatus(str, Enum):
    PASS = "PASS"           # Tidak ada risiko faktual penting, klaim utama didukung
    REVISE = "REVISE"       # Ada isu yang bisa diperbaiki (overclaim, konteks, wording)
    BLOCK = "BLOCK"         # Ada kontradiksi fatal atau kekeliruan data substansial


@dataclass
class EvidenceItem:
    """Represents an empirical source or piece of evidence."""
    source: str
    source_tier: int = 6
    source_tier_name: str = "Secondary Commentary / Web"
    reliability: str = "MEDIUM"
    content: str = ""
    url: str = ""
    publisher: str = ""
    year: Optional[int] = None
    geography: Optional[str] = None
    sample_scope: Optional[str] = None
    supports: Optional[str] = None
    limitations: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceItem:
        url = data.get("url", "")
        pub = data.get("publisher", data.get("source", ""))
        content = data.get("content", data.get("text", data.get("finding", "")))
        
        # Reuse existing classify_source_quality
        tier_info = classify_source_quality(url, pub)
        tier = data.get("source_tier", tier_info.get("tier", 6))
        tier_name = data.get("source_tier_name", tier_info.get("tier_name", "Web"))
        rel = data.get("reliability", tier_info.get("reliability", "MEDIUM"))

        # Extract year if possible
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", str(data.get("year", "")) + " " + content + " " + pub)
        extracted_year = int(year_match.group(1)) if year_match else None

        return cls(
            source=pub or data.get("source", "Unknown Source"),
            source_tier=tier,
            source_tier_name=tier_name,
            reliability=rel,
            content=content,
            url=url,
            publisher=pub,
            year=extracted_year,
            geography=data.get("geography"),
            sample_scope=data.get("sample_scope"),
            supports=data.get("supports"),
            limitations=data.get("limitations")
        )


@dataclass
class ExtractedClaim:
    """Represents a discrete claim extracted from a script."""
    text: str
    claim_type: ClaimType
    section_name: str = "GENERAL"
    raw_sentence: str = ""
    is_opinion_or_speculation: bool = False
    extracted_entities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaimVerificationResult:
    """Detailed audit verdict for a single claim."""
    claim: str
    type: ClaimType
    status: VerificationStatus
    severity: Severity
    confidence: str                 # "HIGH", "MEDIUM", "LOW"
    reason: str
    recommendation: Optional[str] = None
    issues: List[str] = field(default_factory=list) # e.g. OVERCLAIM, CAUSAL_OVERCLAIM
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    section: str = "GENERAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "type": self.type.value,
            "status": self.status.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "issues": self.issues,
            "reason": self.reason,
            "recommendation": self.recommendation,
            "section": self.section,
            "evidence": self.evidence
        }


@dataclass
class ScriptAuditReport:
    """Comprehensive audit report for an entire script."""
    overall_status: OverallStatus
    summary: Dict[str, int]
    claims: List[ClaimVerificationResult]
    warnings: List[str]
    recommendations: List[str]
    property_brand_fit: Optional[Dict[str, Any]] = None
    editorial_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "claims": [c.to_dict() for c in self.claims],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "property_brand_fit": self.property_brand_fit,
            "editorial_metadata": self.editorial_metadata
        }


# =============================================================================
# 1B. NUGI PROPERTY BRAND FIT EVALUATION
# =============================================================================

PROPERTY_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "housing_shelter": [
        "rumah", "hunian", "kamar", "apartemen", "kost", "kontrakan", "perumahan",
        "cluster", "denah", "ruang tamu", "dapur", "atap", "dinding", "fasad",
        "plafon", "ventilasi", "balkon", "kamar tidur", "ruang keluarga", "bangunan",
        "ruang makan", "tempat tinggal", "tempat berteduh", "ruang tidur"
    ],
    "land_ownership": [
        "tanah", "lahan", "kavling", "kepemilikan", "sertifikat", "hak milik",
        "shm", "hgb", "agunan", "warisan", "luas kavling", "luas tanah", "agunan fisik"
    ],
    "real_estate_economics": [
        "kpr", "harga tanah", "harga rumah", "sewa", "kontrak", "cicilan", "developer",
        "backlog", "biaya perawatan", "nilai lokasi", "appraisal", "bunga kpr",
        "pajak bumi", "total cost of ownership", "tco", "afordabilitas", "daya beli",
        "tenor", "uang muka", "dp rumah", "investasi properti", "yield sewa",
        "biaya renovasi", "biaya operasional rumah", "ipl"
    ],
    "location_urban_value": [
        "stasiun", "aksesibilitas", "lebar jalan", "trotoar", "walkability",
        "kawasan hunian", "tata kota", "zonasi", "tata ruang", "transportasi umum",
        "lingkungan rumah", "jarak tempuh", "transit", "tod", "suburban", "pusat kota",
        "jalan depan rumah"
    ],
    "spatial_living_dynamics": [
        "ruang hidup", "ruang kerja di rumah", "suhu rumah", "panas kamar",
        "cahaya alami", "orientasi matahari", "arah matahari", "akustik kamar",
        "kedap suara", "polusi suara", "desain tropis", "pendingin ruangan",
        "arsitektur", "layout rumah", "ventilasi silang", "kualitas udara kamar",
        "desain hunian", "penataan ruang", "sirkulasi udara"
    ],
    "history_psychology_home": [
        "arti rumah", "makna rumah", "rasa aman", "privasi", "identitas tempat",
        "harta di rumah", "keterikatan tanah", "benteng", "tempat pulang",
        "psikologi kepemilikan", "sejarah rumah", "ruang privat", "ruang domestik"
    ]
}


def evaluate_nugi_property_brand_fit(
    script_text: str,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates how strongly a script aligns with Nugi Properti brand identity.
    Core Principle: 'PROPERTY IS THE LENS, NOT ALWAYS THE OBJECT.'

    Score range (0-20):
    - 17–20: CORE PROPERTY (Properti/housing/land/ownership inti cerita)
    - 13–16: STRONG PROPERTY LENS (Property mekanisme penting bagi WHY cerita)
    - 9–12:  ACCEPTABLE (Koneksi hunian/ruang cukup kuat tapi sekunder)
    - 5–8:   WEAK (Mirip urbanism/general knowledge umum)
    - 0–4:   OFF BRAND (Generic knowledge, property sekadar ditempel di akhir)
    """
    from engine.editorial.quality_gate import check_hard_rejections

    # 1. Check hard rejections (property sales listing or generic AI tools)
    rejections = check_hard_rejections(script_text)
    if rejections:
        return {
            "score": 0,
            "tier": "OFF BRAND",
            "status": "REVISE_OR_REPLACE",
            "feedback": f"Terdeteksi hard rejection: {rejections[0]['reason']}",
            "active_dimensions": [],
            "tacked_on_warning": False,
            "breakdown": {"hook_title": 0, "why_mechanism": 0, "revelation": 0, "depth": 0}
        }

    full_lower = script_text.lower()
    title_lower = (title or "").lower()

    # Flatten all property keywords
    all_prop_keywords: set[str] = set()
    for kw_list in PROPERTY_DIMENSION_KEYWORDS.values():
        all_prop_keywords.update(kw_list)

    def _has_any_kw(kws: Union[List[str], set[str]], text: str) -> List[str]:
        found = []
        for kw in kws:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                found.append(kw)
        return found

    # 2. Check for "Tacked-on property closing" anti-pattern
    # (e.g. clock hands, galaxy, generic history, where 'rumah' only appears in the final 15% of the text)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", script_text) if s.strip()]
    if len(sentences) >= 4:
        split_point = int(len(sentences) * 0.8)
        early_text = " ".join(sentences[:split_point]).lower()
        ending_text = " ".join(sentences[split_point:]).lower()

        early_hits = _has_any_kw(all_prop_keywords, early_text)
        ending_hits = _has_any_kw(all_prop_keywords, ending_text)
        title_hits = _has_any_kw(all_prop_keywords, title_lower)

        if not early_hits and not title_hits and ending_hits:
            return {
                "score": 3,
                "tier": "OFF BRAND",
                "status": "REVISE_OR_REPLACE",
                "feedback": (
                    "Konsep properti/rumah hanya ditempelkan pada penutup/revelation. "
                    "Topik utama tidak memiliki mekanisme properti substantif."
                ),
                "active_dimensions": [],
                "tacked_on_warning": True,
                "breakdown": {"hook_title": 0, "why_mechanism": 0, "revelation": 2, "depth": 1}
            }

    # 3. Structural scoring (Max 20)
    active_dims = []
    for dim_name, kws in PROPERTY_DIMENSION_KEYWORDS.items():
        if _has_any_kw(kws, full_lower):
            active_dims.append(dim_name)

    # A. Hook / Title alignment (0 - 4 pts)
    hook_score = 0
    if _has_any_kw(all_prop_keywords, title_lower):
        hook_score += 2
    early_sample = " ".join(sentences[:max(1, len(sentences) // 4)]).lower() if sentences else full_lower[:100]
    if _has_any_kw(all_prop_keywords, early_sample):
        hook_score += 2
    hook_score = min(4, hook_score)

    # B. WHY Mechanism / Explanatory core (0 - 8 pts)
    # The explanatory core (middle body) must address property/living space mechanisms
    mid_sample = " ".join(sentences[max(1, len(sentences)//4):int(len(sentences)*0.85)]).lower() if len(sentences) >= 4 else full_lower
    mid_dims = [dim for dim, kws in PROPERTY_DIMENSION_KEYWORDS.items() if _has_any_kw(kws, mid_sample)]
    
    if len(mid_dims) >= 3:
        why_score = 8
    elif len(mid_dims) == 2:
        why_score = 6
    elif len(mid_dims) == 1:
        why_score = 4
    elif _has_any_kw(all_prop_keywords, mid_sample):
        why_score = 3
    else:
        why_score = 1

    # C. Revelation & Perspective Shift (0 - 4 pts)
    rev_sample = " ".join(sentences[int(len(sentences)*0.75):]).lower() if len(sentences) >= 4 else full_lower
    rev_score = 0
    if _has_any_kw(all_prop_keywords, rev_sample):
        rev_score = 4
    elif any(k in rev_sample for k in ["ruang", "hidup", "tinggal", "kota", "tempat"]):
        rev_score = 2

    # D. Vocabulary density & multi-dimensional depth (0 - 4 pts)
    total_distinct_kws = sum(1 for kw in all_prop_keywords if re.search(r"\b" + re.escape(kw) + r"\b", full_lower))
    if len(active_dims) >= 3 and total_distinct_kws >= 6:
        depth_score = 4
    elif len(active_dims) >= 2 and total_distinct_kws >= 4:
        depth_score = 3
    elif len(active_dims) >= 1 and total_distinct_kws >= 2:
        depth_score = 2
    else:
        depth_score = 1

    total_score = min(20, hook_score + why_score + rev_score + depth_score)

    if total_score >= 17:
        tier = "CORE PROPERTY"
    elif total_score >= 13:
        tier = "STRONG PROPERTY LENS"
    elif total_score >= 9:
        tier = "ACCEPTABLE"
    elif total_score >= 5:
        tier = "WEAK"
    else:
        tier = "OFF BRAND"

    status = "PASS" if total_score >= 9 else "REVISE_OR_REPLACE"
    feedback = (
        f"Skor {total_score}/20 ({tier}). "
        + (f"Dimensi aktif: {', '.join(active_dims)}." if active_dims else "Tidak ada dimensi properti yang terdeteksi.")
    )

    return {
        "score": total_score,
        "tier": tier,
        "status": status,
        "feedback": feedback,
        "active_dimensions": active_dims,
        "tacked_on_warning": False,
        "breakdown": {
            "hook_title": hook_score,
            "why_mechanism": why_score,
            "revelation": rev_score,
            "depth": depth_score
        }
    }


# =============================================================================
# 2. CLAIM EXTRACTION LOGIC
# =============================================================================

# Subjective opinion indicators
OPINION_MARKERS = [
    r"\bmenurut (saya|hemat saya|pandangan saya)\b",
    r"\brasanya\b",
    r"\btampaknya\b",
    r"\bsepertinya\b",
    r"\bterasa seperti\b",
    r"\bbagaikan\b",
    r"\bpandangan saya\b",
    r"\bsaya kira\b",
    r"\bseakan-akan\b"
]

# Speculation indicators
SPECULATION_MARKERS = [
    r"\bmungkin saja\b",
    r"\bbisa jadi\b",
    r"\bbisa saja\b",
    r"\bjangan-jangan\b",
    r"\bkira-kira\b",
    r"\bdi masa depan nanti\b",
    r"\bakankah\b",
    r"\bkemungkinan besar akan\b"
]

# Causal indicators (active causation assertion)
CAUSAL_CONNECTORS = [
    r"\bmenyebabkan\b",
    r"\bmemicu\b",
    r"\bmengakibatkan\b",
    r"\bmembuat\b",
    r"\bberdampak pada\b",
    r"\bmenghasilkan\b",
    r"\bberujung pada\b",
    r"\bmendorong\b",
    r"\bmemaksa\b",
    r"\bkarena itulah\b"
]

# Universal/Absolute overclaim indicators
UNIVERSAL_MARKERS = [
    r"\bselalu\b",
    r"\btidak pernah\b",
    r"\bsemua orang\b",
    r"\bsetiap orang\b",
    r"\bmanusia selalu\b",
    r"\bpasti\b",
    r"\bmustahil\b",
    r"\b100%\b",
    r"\bmutlak\b",
    r"\btanpa terkecuali\b"
]


def extract_claims_from_text(script_text: str, default_section: str = "BODY") -> List[ExtractedClaim]:
    """
    Extracts distinct factual, causal, numerical, and conceptual claims
    from spoken narrative sentences.
    """
    # 1. Parse markdown structure if present
    sections = _parse_script_sections(script_text)
    
    extracted: List[ExtractedClaim] = []

    for section_name, text in sections:
        # Segment into sentences
        sentences = _segment_sentences(text)
        
        for sent in sentences:
            sent_clean = sent.strip()
            if not sent_clean or len(sent_clean.split()) < 4:
                continue
                
            # Filter pure rhetorical questions without factual assertions
            if sent_clean.endswith("?") and not any(k in sent_clean.lower() for k in [
                "karena", "sejak", "meningkat", "%", "tahun", "mengapa", "kenapa", "penelitian"
            ]):
                continue

            claim_obj = _classify_and_build_claim(sent_clean, section_name)
            if claim_obj:
                extracted.append(claim_obj)

    return extracted


def _parse_script_sections(raw_text: str) -> List[Tuple[str, str]]:
    """Splits markdown script into (section_name, text) pairs."""
    lines = raw_text.splitlines()
    sections: List[Tuple[str, str]] = []
    current_sec = "GENERAL"
    current_lines: List[str] = []

    for line in lines:
        line_s = line.strip()
        # Skip markdown table rows
        if line_s.startswith("|") and line_s.endswith("|"):
            continue

        sec_match = re.match(r"^#{2,4}\s*(.*)", line_s)
        if sec_match:
            if current_lines:
                sections.append((current_sec, "\n".join(current_lines)))
                current_lines = []
            header_title = sec_match.group(1).upper()
            if "HOOK" in header_title:
                current_sec = "HOOK"
            elif "SETUP" in header_title or "OBSERVATION" in header_title:
                current_sec = "SETUP"
            elif "WHY" in header_title or "EVIDENCE" in header_title or "BODY" in header_title:
                current_sec = "WHY_EVIDENCE"
            elif "REVELATION" in header_title:
                current_sec = "REVELATION"
            elif "ENDING" in header_title:
                current_sec = "ENDING"
            else:
                current_sec = header_title[:20]
        else:
            # Skip metadata lines like TITLE: TEMA:
            if not re.match(r"^\*\*(TITLE|TEMA|ARKETIPE|HUMAN|TARGET|ESTIMASI).*:\*\*", line_s):
                current_lines.append(line)

    if current_lines:
        sections.append((current_sec, "\n".join(current_lines)))

    if not sections:
        sections = [("GENERAL", raw_text)]

    return sections


def _segment_sentences(text: str) -> List[str]:
    """Segments text into sentences considering Indonesian dialogue & ellipsis."""
    # Replace ellipsis with comma pause so it doesn't break sentences prematurely
    normalized = re.sub(r"\s*\.{3,}\s*", ", ", text)
    # Split on period, exclamation, question mark, or newlines
    raw_sents = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    return [s.strip() for s in raw_sents if s.strip()]


def _extract_spoken_narration(script_text: str) -> str:
    """Return narration only; production headings and metadata are not claims."""
    lines = script_text.splitlines()
    spoken_fence_types = {"text", "txt", "narration", "spoken"}
    has_spoken_fence = any(
        line.strip().startswith("```")
        and line.strip()[3:].strip().lower() in spoken_fence_types
        for line in lines
    )
    in_fence = False
    count_fence = False
    narration = []
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            if not in_fence:
                in_fence = True
                count_fence = line[3:].strip().lower() in spoken_fence_types
            else:
                in_fence = False
                count_fence = False
            continue
        if in_fence:
            if not count_fence:
                continue
        elif has_spoken_fence:
            continue
        if not line or line.startswith(("#", "---", "- **", "* **")):
            continue
        if line.lower().startswith(("metadata:", "status epistemik", "title:", "judul:")):
            continue
        if re.match(r"^\[\d{2}:\d{2}.*\]\s+[A-Z][A-Z &/\-]*$", line):
            continue
        narration.append(line)
    return "\n".join(narration)


def _classify_and_build_claim(sentence: str, section_name: str) -> Optional[ExtractedClaim]:
    """Analyzes a single sentence and constructs a classified ExtractedClaim."""
    lower = sentence.lower()
    
    # Check Opinion & Rhetorical / Imperative Closings / Observational Prompts
    is_opinion = any(re.search(p, lower) for p in OPINION_MARKERS) or (
        any(lower.startswith(p) for p in [
            "coba", "pernahkah", "pernah nggak", "bayangkan", "tengoklah", "ingatlah",
            "kembalikan", "beri sedikit", "saat melihat", "saat menandatangani", "tanyakan pada"
        ])
        and not any(k in lower for k in ["penelitian", "data", "angka", "studi", "bukti", "menurut riset"])
    )
    if is_opinion:
        return ExtractedClaim(
            text=sentence,
            claim_type=ClaimType.OPINION,
            section_name=section_name,
            raw_sentence=sentence,
            is_opinion_or_speculation=True
        )

    # Check Speculation
    is_speculation = any(re.search(p, lower) for p in SPECULATION_MARKERS)
    if is_speculation:
        return ExtractedClaim(
            text=sentence,
            claim_type=ClaimType.SPECULATION,
            section_name=section_name,
            raw_sentence=sentence,
            is_opinion_or_speculation=True
        )

    # Quantitative check: Numbers, percentages, multipliers, currency
    num_matches = re.findall(
        r"(\d+[\.,]?\d*|\d+)\s*(%|persen|kali lipat|x lipat|tahun|bulan|jam|desibel|db|m²|meter|kavling|ppm|derajat|°c|miliar|juta|ribu|triliun|rp)",
        lower
    )
    raw_numbers = re.findall(r"\b\d+[\.,]?\d*\b", lower)
    has_numbers = bool(num_matches or (raw_numbers and not re.search(r"^\d+\.", sentence)))

    # Temporal check: explicit year, century, decade, or time anchors
    temporal_match = re.search(r"\b(18\d\d|19\d\d|20\d\d|abad ke-\d+|dekade|tiga dekade|zaman|sejak|saat ini|kini)\b", lower)

    # Causal check
    has_causal = any(re.search(p, lower) for p in CAUSAL_CONNECTORS)

    # Universal check
    has_universal = any(re.search(p, lower) for p in UNIVERSAL_MARKERS)

    # Comparative check
    has_comparative = any(k in lower for k in [
        "lebih ", "daripada", "dibandingkan", "melampaui", "menyusut", "meningkat", "menurun"
    ])

    # Population check
    has_population = any(k in lower for k in [
        "orang indonesia", "warga jakarta", "pekerja", "anak muda", "masyarakat", "generasi", "kebanyakan orang"
    ])

    # Domain-specific indicators
    has_scientific = any(k in lower for k in [
        "otak", "retina", "melatonin", "amigdala", "hormon", "saraf", "karbon dioksida", "co2",
        "endowment effect", "biologi", "biphasic", "sirkadian"
    ])
    has_economic = any(k in lower for k in [
        "kpr", "bunga bank", "amortisasi", "harga tanah", "upah riil", "inflasi", "sewa",
        "daya beli", "financialization", "modal", "cicilan"
    ])
    has_tech = any(k in lower for k in [
        "ai", "kecerdasan buatan", "server", "data center", "komputasi", "laptop", "listrik", "lampu pijar"
    ])
    has_urban = any(k in lower for k in [
        "tanah", "kavling", "kota", "jalan raya", "tiang listrik", "mrt", "krl", "utilitas", "tata ruang"
    ])
    has_historical = any(k in lower for k in [
        "nenek moyang", "zaman kuno", "ratusan ribu tahun", "abad ke-19", "sejarah", "kuno", "purba", "ditemukan pada"
    ])

    # Assign primary claim type by precedence
    if has_numbers and any(k in lower for k in ["%", "persen", "kali lipat", "m²", "ppm", "db", "desibel", "juta", "miliar"]):
        primary_type = ClaimType.QUANTITATIVE
    elif has_universal:
        primary_type = ClaimType.UNIVERSAL
    elif has_causal:
        primary_type = ClaimType.CAUSAL
    elif temporal_match and not has_scientific and not has_economic:
        primary_type = ClaimType.TEMPORAL
    elif has_historical:
        primary_type = ClaimType.HISTORICAL
    elif has_scientific:
        primary_type = ClaimType.SCIENTIFIC
    elif has_economic:
        primary_type = ClaimType.ECONOMIC
    elif has_tech:
        primary_type = ClaimType.TECHNOLOGY
    elif has_comparative:
        primary_type = ClaimType.COMPARATIVE
    elif has_population:
        primary_type = ClaimType.POPULATION
    elif has_urban:
        primary_type = ClaimType.URBAN_PROPERTY
    else:
        primary_type = ClaimType.OTHER_FACTUAL

    extracted_entities = {
        "numbers": raw_numbers,
        "units": [m[1] for m in num_matches] if num_matches else [],
        "temporal": temporal_match.group(0) if temporal_match else None,
        "causal": bool(has_causal),
        "universal": bool(has_universal)
    }

    return ExtractedClaim(
        text=sentence,
        claim_type=primary_type,
        section_name=section_name,
        raw_sentence=sentence,
        is_opinion_or_speculation=False,
        extracted_entities=extracted_entities
    )


# =============================================================================
# 3. EVIDENCE RESOLUTION & SOURCE MATCHING
# =============================================================================

class EvidenceResolver:
    """
    Finds and normalizes evidence candidates using:
    1. Direct evidence objects passed to auditor (e.g. Evidence Cards / Research Notes)
    2. Search infrastructure (ResearchRunner / DDGSWebResearchProvider)
    """

    def __init__(self, search_provider: Optional[WebResearchProvider] = None):
        self.search_provider = search_provider or DDGSWebResearchProvider()
        self.research_runner = ResearchRunner(self.search_provider)

    def resolve_for_claim(
        self,
        claim: ExtractedClaim,
        provided_evidence: Optional[List[Union[EvidenceItem, Dict[str, Any]]]] = None,
        enable_web_fallback: bool = False
    ) -> List[EvidenceItem]:
        """
        Resolves relevant evidence items for a given claim.
        Prioritizes structured provided evidence before triggering web lookups.
        """
        resolved: List[EvidenceItem] = []

        # 1. Evaluate provided evidence items
        if provided_evidence:
            claim_words = set(re.findall(r"\w{3,}", claim.text.lower()))
            stops = {"yang", "dari", "pada", "untuk", "dengan", "akan", "bisa", "jika", "karena", "maka", "atau"}
            claim_words = claim_words - stops
            for raw_item in provided_evidence:
                item = raw_item if isinstance(raw_item, EvidenceItem) else EvidenceItem.from_dict(raw_item)
                item_content = (item.content + " " + item.source + " " + (item.supports or "")).lower()
                
                # Check keyword overlap or entity match
                overlap = sum(1 for w in claim_words if w in item_content)
                is_single_candidate = len(provided_evidence) == 1
                has_entity_match = any(num in item_content for num in claim.extracted_entities.get("numbers", []))

                if overlap >= 2 or has_entity_match or (is_single_candidate and overlap >= 1):
                    resolved.append(item)

        # 2. Web research fallback if explicitly requested and no evidence found
        if not resolved and enable_web_fallback and not claim.is_opinion_or_speculation:
            try:
                # Query with essential keywords
                keywords = " ".join(list(claim_words)[:5])
                web_results = self.search_provider.search(keywords, max_results=3)
                for res in web_results:
                    resolved.append(EvidenceItem.from_dict(res))
            except Exception as e:
                logger.warning(f"Live evidence resolution failed for claim '{claim.text[:30]}': {e}")

        return resolved


# =============================================================================
# 4. FACTUAL AUDIT & VERIFICATION ENGINE
# =============================================================================

class ScriptAuditor:
    """
    Main Auditor Engine.
    Evaluates claims against evidence with fine-grained epistemic checks:
    - Numerical consistency
    - Causal overstatement (correlation vs causation)
    - Universal / certainty overclaim
    - Scope and demographic mismatch
    - Temporal relevance and mismatch
    - Conflicting sources
    """

    def __init__(self, resolver: Optional[EvidenceResolver] = None):
        self.resolver = resolver or EvidenceResolver()

    def audit_script(
        self,
        script_text: str,
        provided_evidence: Optional[List[Union[EvidenceItem, Dict[str, Any]]]] = None,
        enable_web_fallback: bool = False,
        editorial_context: Optional[Dict[str, Any]] = None
    ) -> ScriptAuditReport:
        """
        Audits an entire script narrative against provided or resolved evidence.
        """
        # 1. Extract all claims
        claims = extract_claims_from_text(script_text)
        
        results: List[ClaimVerificationResult] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        # Summary counter
        summary = {
            "total_claims": len(claims),
            "factual_claims": 0,
            "opinions": 0,
            "speculations": 0,
            "verified": 0,
            "supported": 0,
            "partially_supported": 0,
            "needs_context": 0,
            "unverified": 0,
            "contradicted": 0,
            "conflicting_evidence": 0
        }

        for c in claims:
            if c.claim_type == ClaimType.OPINION:
                summary["opinions"] += 1
                results.append(ClaimVerificationResult(
                    claim=c.text,
                    type=ClaimType.OPINION,
                    status=VerificationStatus.OPINION,
                    severity=Severity.LOW,
                    confidence="HIGH",
                    reason="Pernyataan bersifat reflektif / opini subjektif, bukan klaim faktual terikat bukti.",
                    section=c.section_name
                ))
                continue

            if c.claim_type == ClaimType.SPECULATION:
                summary["speculations"] += 1
                results.append(ClaimVerificationResult(
                    claim=c.text,
                    type=ClaimType.SPECULATION,
                    status=VerificationStatus.SPECULATION,
                    severity=Severity.LOW,
                    confidence="HIGH",
                    reason="Pernyataan berupa hipotesis / dugaan masa depan.",
                    section=c.section_name
                ))
                continue

            summary["factual_claims"] += 1
            
            # Resolve evidence for factual claim
            matched_evidence = self.resolver.resolve_for_claim(
                c, provided_evidence=provided_evidence, enable_web_fallback=enable_web_fallback
            )

            # Audit the claim against evidence
            v_result = self.verify_single_claim(c, matched_evidence)
            results.append(v_result)

            # Update summary counts
            st_key = v_result.status.value.lower()
            if st_key in summary:
                summary[st_key] += 1

            # Aggregate warnings & recommendations
            if v_result.issues:
                warnings.append(f"[{v_result.section}] {', '.join(v_result.issues)}: \"{c.text}\"")
            if v_result.recommendation:
                recommendations.append(f"[{v_result.section}] {v_result.recommendation}")

        # Compute overall status
        overall_status = self._compute_overall_status(results)

        # Property Brand Fit Evaluation
        title_ctx = editorial_context.get("title") if editorial_context else None
        brand_fit = evaluate_nugi_property_brand_fit(script_text, title=title_ctx)

        # Optional integration with Human-Place / Editorial Identity
        if editorial_context:
            from engine.editorial.human_place_engine import evaluate_human_place_anchor
            hp = evaluate_human_place_anchor(
                editorial_context.get("title", script_text[:50]), script_text
            )
            editorial_context["human_place_evaluation"] = hp
            editorial_context["nugi_property_brand_fit"] = brand_fit

        if brand_fit.get("status") == "REVISE_OR_REPLACE":
            warnings.append(
                f"Nugi Property Brand Fit rendah ({brand_fit.get('score')}/20 - {brand_fit.get('tier')}): "
                f"{brand_fit.get('feedback')}"
            )

        return ScriptAuditReport(
            overall_status=overall_status,
            summary=summary,
            claims=results,
            warnings=warnings,
            recommendations=recommendations,
            property_brand_fit=brand_fit,
            editorial_metadata=editorial_context
        )

    def verify_single_claim(
        self,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem]
    ) -> ClaimVerificationResult:
        """
        Deep evaluation of a single claim against matching evidence.
        """
        text = claim.text
        lower_claim = text.lower()

        # CASE A: No Evidence Found
        if not evidence_list:
            severity = Severity.HIGH if claim.claim_type in [
                ClaimType.QUANTITATIVE, ClaimType.CAUSAL, ClaimType.UNIVERSAL
            ] else Severity.MEDIUM

            return ClaimVerificationResult(
                claim=text,
                type=claim.claim_type,
                status=VerificationStatus.UNVERIFIED,
                severity=severity,
                confidence="MEDIUM",
                reason=(
                    "Belum ditemukan data atau rujukan bukti yang memadai untuk memverifikasi klaim ini. "
                    "Catatan: Status UNVERIFIED tidak berarti klaim salah, melainkan butuh bukti pendukung."
                ),
                recommendation=f"Sertakan rujukan penelitian atau batasi kepastian kalimat: \"{text}\"",
                section=claim.section_name
            )

        # CASE B: Conflicting Evidence Check
        if self._detect_conflicting_evidence(evidence_list):
            return ClaimVerificationResult(
                claim=text,
                type=claim.claim_type,
                status=VerificationStatus.CONFLICTING_EVIDENCE,
                severity=Severity.HIGH,
                confidence="HIGH",
                issues=["CONFLICTING_EVIDENCE"],
                reason="Ditemukan perbedaan temuan atau kontradiksi langsung antar-sumber kredibel yang tersedia.",
                recommendation="Jelaskan adanya ketidakpastian / perdebatan ilmiah alih-alih mengambil kesimpulan sepihak.",
                evidence=[asdict(e) for e in evidence_list],
                section=claim.section_name
            )

        issues: List[str] = []
        recommendations: List[str] = []
        is_contradicted = False
        contradiction_reason = ""

        # Aggregate evidence content
        combined_ev = " ".join([e.content.lower() for e in evidence_list])
        max_tier = min([e.source_tier for e in evidence_list])

        # 1. Numerical Verification
        num_mismatch, num_reason = self._check_numerical_consistency(claim, evidence_list)
        if num_mismatch:
            issues.append("NUMERICAL_MISMATCH")
            is_contradicted = True
            contradiction_reason = num_reason
            recommendations.append(f"Koreksi angka: {num_reason}")

        # 2. Causal Overclaim Check (Correlation vs Causation)
        if claim.claim_type == ClaimType.CAUSAL or any(re.search(p, lower_claim) for p in CAUSAL_CONNECTORS):
            is_causal_overclaim, causal_reason = self._check_causal_overstatement(claim, combined_ev)
            if is_causal_overclaim:
                issues.append("CAUSAL_OVERCLAIM")
                recommendations.append(
                    "Bukti hanya mengonfirmasi korelasi/asosiasi. "
                    "Ubah diksi kausal ('menyebabkan') menjadi hubungan non-mutlak ('berkaitan dengan' / 'berhubungan dengan')."
                )

        # 3. Universal / Certainty Overclaim Check
        is_overclaim, overclaim_reason = self._check_overclaim_wording(claim, combined_ev)
        if is_overclaim:
            issues.append("OVERCLAIM")
            recommendations.append(
                "Wording script menggunakan klaim kepastian mutlak ('semua' / 'selalu' / 'pasti'). "
                "Gunakan epistemic humility ('cenderung' / 'penelitian menunjukkan')."
            )

        # 4. Scope & Population Mismatch Check
        scope_mismatch, scope_reason = self._check_scope_mismatch(claim, evidence_list)
        if scope_mismatch:
            issues.append("SCOPE_MISMATCH")
            recommendations.append(f"Persempit generalisasi populasi/wilayah: {scope_reason}")

        # 5. Temporal Mismatch Check
        temporal_mismatch, temp_reason = self._check_temporal_mismatch(claim, evidence_list)
        if temporal_mismatch:
            issues.append("TEMPORAL_MISMATCH")
            recommendations.append(f"Klarifikasi konteks waktu data: {temp_reason}")

        # Determine Final Status for Claim
        if is_contradicted:
            status = VerificationStatus.CONTRADICTED
            severity = Severity.CRITICAL
            confidence = "HIGH"
            reason = contradiction_reason
        elif "CAUSAL_OVERCLAIM" in issues or "OVERCLAIM" in issues:
            status = VerificationStatus.PARTIALLY_SUPPORTED
            severity = Severity.HIGH if claim.claim_type == ClaimType.CAUSAL else Severity.MEDIUM
            confidence = "HIGH"
            reason = "Substansi didukung bukti, namun tingkat kepastian wording kalimat lebih kuat dari derajat temuan bukti."
        elif "SCOPE_MISMATCH" in issues or "TEMPORAL_MISMATCH" in issues:
            status = VerificationStatus.NEEDS_CONTEXT
            severity = Severity.MEDIUM
            confidence = "HIGH"
            reason = "Klaim membutuhkan penegasan konteks ruang/waktu agar tidak menimbulkan salah tafsir generalisasi."
        else:
            # Fully supported or verified
            if max_tier <= 3:
                status = VerificationStatus.VERIFIED
                confidence = "HIGH"
                reason = "Didukung secara langsung dan presisi oleh sumber primer/institusi resmi."
            else:
                status = VerificationStatus.SUPPORTED
                confidence = "MEDIUM"
                reason = "Didukung secara memadai oleh literatur dan publikasi kredibel."
            severity = Severity.LOW

        rec_str = " ".join(recommendations) if recommendations else None

        return ClaimVerificationResult(
            claim=text,
            type=claim.claim_type,
            status=status,
            severity=severity,
            confidence=confidence,
            reason=reason,
            recommendation=rec_str,
            issues=issues,
            evidence=[asdict(e) for e in evidence_list],
            section=claim.section_name
        )

    # -------------------------------------------------------------------------
    # Helper Inspection Rules
    # -------------------------------------------------------------------------

    def _detect_conflicting_evidence(self, evidence_list: List[EvidenceItem]) -> bool:
        """Checks if multiple high-tier sources provide contradictory findings."""
        if len(evidence_list) < 2:
            return False

        high_tier = [e for e in evidence_list if e.source_tier <= 4]
        if len(high_tier) < 2:
            return False

        # Check for explicit contradiction markers between findings
        has_increase = any(any(k in e.content.lower() for k in ["meningkat", "naik", "peningkatan", "growth"]) for e in high_tier)
        has_decrease = any(any(k in e.content.lower() for k in ["menurun", "turun", "penurunan", "decline"]) for e in high_tier)
        
        return has_increase and has_decrease

    def _check_numerical_consistency(
        self,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem]
    ) -> Tuple[bool, str]:
        """Verifies if numbers and percentages in claim align with evidence."""
        claim_nums = claim.extracted_entities.get("numbers", [])
        if not claim_nums:
            return False, ""

        combined_ev = " ".join([e.content for e in evidence_list])
        ev_nums = re.findall(r"\b\d+[\.,]?\d*\b", combined_ev)

        # Check percentages
        claim_pcts = re.findall(r"(\d+[\.,]?\d*)\s*(%|persen)", claim.text.lower())
        ev_pcts = re.findall(r"(\d+[\.,]?\d*)\s*(%|persen)", combined_ev.lower())

        if claim_pcts and ev_pcts:
            c_val = float(claim_pcts[0][0].replace(",", "."))
            e_vals = [float(p[0].replace(",", ".")) for p in ev_pcts]
            
            # If claim claims exact number and no evidence contains it or near it
            if not any(abs(c_val - ev_v) <= 2.0 for ev_v in e_vals):
                return True, f"Klaim menyebutkan {c_val}%, namun data sumber mencantumkan {e_vals[0]}%."

        return False, ""

    def _check_causal_overstatement(
        self,
        claim: ExtractedClaim,
        evidence_text: str
    ) -> Tuple[bool, str]:
        """Checks if script turns correlation/association into hard causation."""
        # Evidence only indicates correlation/association
        has_corr_evidence = any(k in evidence_text for k in [
            "korelasi", "asosiasi", "hubungan", "associated with", "correlated with", "terkait", "berkaitan"
        ])
        has_causal_proof = any(k in evidence_text for k in [
            "kausalitas", "causal effect", "terbukti menyebabkan", "membuktikan penyebab", "kausal"
        ])

        if has_corr_evidence and not has_causal_proof:
            return True, "Sumber menyatakan korelasi/asosiasi, tetapi script mengklaim hubungan sebab-akibat mutlak."

        return False, ""

    def _check_overclaim_wording(
        self,
        claim: ExtractedClaim,
        evidence_text: str
    ) -> Tuple[bool, str]:
        """Detects exaggerated universal quantifiers (semua, selalu, pasti, 100%)."""
        lower = claim.text.lower()
        matched_univ = [p for p in UNIVERSAL_MARKERS if re.search(p, lower)]
        
        if matched_univ:
            # Check if evidence supports absolute universality
            if not any(k in evidence_text for k in ["seluruhnya", "100%", "tanpa pengecualian", "mutlak"]):
                return True, f"Script menggunakan kata absolut '{matched_univ[0]}' yang tidak didukung data populasi universal."

        return False, ""

    def _check_scope_mismatch(
        self,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem]
    ) -> Tuple[bool, str]:
        """Detects demographic/geographic overgeneralization."""
        lower_claim = claim.text.lower()

        for ev in evidence_list:
            ev_content = ev.content.lower()
            # Case: Script says "Orang Indonesia", evidence says "warga Jakarta"
            if "orang indonesia" in lower_claim and any(k in ev_content for k in ["warga jakarta", "responden jakarta", "di jakarta"]):
                if "seluruh indonesia" not in ev_content:
                    return True, "Data riset hanya berbasis responden warga Jakarta, tetapi script menggeneralisasi ke 'Orang Indonesia'."

            # Case: Script says "Pekerja", evidence specifies "pekerja remote / tech"
            if "pekerja" in lower_claim and "pekerja teknologi" in ev_content:
                if "seluruh pekerja" not in ev_content:
                    return True, "Data riset berasal dari sampel pekerja sektor teknologi, bukan tenaga kerja umum."

        return False, ""

    def _check_temporal_mismatch(
        self,
        claim: ExtractedClaim,
        evidence_list: List[EvidenceItem]
    ) -> Tuple[bool, str]:
        """Detects temporal mismatch (claiming 'saat ini' from older data)."""
        lower = claim.text.lower()
        if any(k in lower for k in ["saat ini", "sekarang", "kini", "hari ini"]):
            for ev in evidence_list:
                if ev.year and ev.year <= 2019:
                    return True, f"Script menggunakan klaim 'saat ini', namun rujukan data berasal dari tahun {ev.year}."

        return False, ""

    def _compute_overall_status(self, results: List[ClaimVerificationResult]) -> OverallStatus:
        """Determines PASS, REVISE, or BLOCK based on claim severity."""
        if any(r.severity == Severity.CRITICAL for r in results):
            return OverallStatus.BLOCK

        # If any high severity issue or multiple medium issues
        high_issues = [r for r in results if r.severity == Severity.HIGH]
        medium_issues = [r for r in results if r.severity == Severity.MEDIUM]

        if high_issues or len(medium_issues) >= 2:
            return OverallStatus.REVISE

        return OverallStatus.PASS


# =============================================================================
# 5. CLI & CONVENIENCE FUNCTIONS
# =============================================================================

def audit_script_file(
    file_path: Union[str, Path],
    evidence_path: Optional[Union[str, Path]] = None,
    enable_web_fallback: bool = False
) -> ScriptAuditReport:
    """Convenience function to audit a script file from disk."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Script file not found: {file_path}")

    content = p.read_text(encoding="utf-8")
    
    provided_evidence = None
    if evidence_path:
        ev_p = Path(evidence_path)
        if ev_p.exists():
            try:
                ev_data = json.loads(ev_p.read_text(encoding="utf-8"))
                provided_evidence = ev_data if isinstance(ev_data, list) else [ev_data]
            except Exception as e:
                logger.warning(f"Failed to parse evidence file {evidence_path}: {e}")

    auditor = ScriptAuditor()
    return auditor.audit_script(
        script_text=content,
        provided_evidence=provided_evidence,
        enable_web_fallback=enable_web_fallback
    )


if __name__ == "__main__":
    import sys
    import argparse
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Nugi Script Fact & Narrative Verification Engine"
    )
    parser.add_argument("script_file", help="Path to script markdown or text file")
    parser.add_argument("--evidence", "-e", help="Optional JSON evidence file", default=None)
    parser.add_argument("--web", "-w", help="Enable web research fallback", action="store_true")
    parser.add_argument("--json", "-j", help="Output raw JSON", action="store_true")

    args = parser.parse_args()

    report = audit_script_file(
        file_path=args.script_file,
        evidence_path=args.evidence,
        enable_web_fallback=args.web
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 80)
        print(f"SCRIPT AUDIT REPORT — STATUS: {report.overall_status.value}")
        print("=" * 80)
        print(f"Total Claims Extracted : {report.summary['total_claims']}")
        print(f"  - Verified           : {report.summary['verified']}")
        print(f"  - Supported          : {report.summary['supported']}")
        print(f"  - Partially Supported: {report.summary['partially_supported']}")
        print(f"  - Needs Context      : {report.summary['needs_context']}")
        print(f"  - Unverified         : {report.summary['unverified']}")
        print(f"  - Contradicted       : {report.summary['contradicted']}")
        print(f"  - Conflicting        : {report.summary['conflicting_evidence']}")
        if report.property_brand_fit:
            pbf = report.property_brand_fit
            print("-" * 80)
            print(f"NUGI PROPERTY BRAND FIT: {pbf.get('score')}/20 ({pbf.get('tier')}) [{pbf.get('status')}]")
            print(f"  - Active Dimensions  : {', '.join(pbf.get('active_dimensions', []))}")
            if pbf.get('tacked_on_warning'):
                print("  - WARNING            : Konsep properti hanya ditempelkan pada akhir cerita!")
        print("-" * 80)
        print("DETAILED CLAIMS:")
        for idx, c in enumerate(report.claims, 1):
            issue_tag = f" [{', '.join(c.issues)}]" if c.issues else ""
            print(f"\n{idx}. [{c.type.value}] ({c.status.value}){issue_tag} - {c.severity.value}")
            print(f"   Claim : \"{c.claim}\"")
            print(f"   Reason: {c.reason}")
            if c.recommendation:
                print(f"   Rec   : {c.recommendation}")
        print("\n" + "=" * 80)


# ------------------------------------------------------------------------------
# Epistemic Verification Extension (4-State Verdict & Dossier Cross-Check)
# ------------------------------------------------------------------------------

def audit_script_with_dossier(
    script_text: str,
    dossier_data: Optional[Dict[str, Any]] = None,
    story_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Comprehensive epistemic fact-checker cross-checking script sentences
    against structured research dossier and empirical evidence.
    
    Produces 4-state verdicts:
    - VERIFIED: Corroborated by S0-S2 sources or explicit dossier facts.
    - PROBABLE: Supported by reputable S3-S4 reporting or plausible reasoning.
    - DISPUTED: Conflicting evidence, causal overclaim, or numerical mismatch.
    - UNVERIFIED: Lacks empirical backing or unverified speculation.
    """
    sentences = _segment_sentences(_extract_spoken_narration(script_text))
    audited_claims = []
    
    verified_count = 0
    probable_count = 0
    disputed_count = 0
    unverified_count = 0

    known_data_points = []
    if dossier_data and "data_points" in dossier_data:
        known_data_points = dossier_data["data_points"]

    for idx, sentence in enumerate(sentences):
        if len(sentence.strip()) < 15:
            continue

        claim_obj = _classify_and_build_claim(sentence, 'NARRATIVE')
        c_type = claim_obj.claim_type
        s_lower = sentence.lower()

        verdict = "UNVERIFIED"
        reason = "Pernyataan naratif belum memiliki referensi data primer eksplisit."
        confidence = 0.5
        flags = []

        # 1. Check for Causal Overclaims and False Certainty
        if any(w in s_lower for w in ["satu-satunya penyebab", "pasti karena", "hanya disebabkan", "mutlak", "100% akibat", "tidak mungkin karena yang lain"]):
            verdict = "DISPUTED"
            reason = "Causal Overclaim: Mengklaim sebab tunggal mutlak untuk fenomena multi-faktor (Korelasi vs Kausalitas)."
            flags.append("CAUSAL_OVERCLAIM")
            confidence = 0.3
        elif any(w in s_lower for w in ["pasti benar", "tanpa ragu", "100% terbukti", "pasti untung", "dijamin 100%"]):
            verdict = "DISPUTED"
            reason = "False Certainty: Menggunakan klaim kepastian mutlak tanpa pembatasan epistemik yang wajar."
            flags.append("FALSE_CERTAINTY")
            confidence = 0.35

        # 2. Check for Numerical claims against known DataPoints
        has_numbers = bool(re.search(r"\b\d+(?:[.,]\d+)?%?\b", sentence))
        if has_numbers and known_data_points:
            matched_dp = False
            for dp in known_data_points:
                val_str = str(dp.get("value", ""))
                metric_name = dp.get("metric", "").lower()
                if val_str and val_str in sentence:
                    verdict = "VERIFIED"
                    reason = f"Numerical Match: Terverifikasi oleh data {dp.get('source_name', 'BPS')} ({dp.get('metric')}: {dp.get('value')} {dp.get('unit', '')})."
                    confidence = 0.95
                    matched_dp = True
                    break
            if not matched_dp and verdict != "DISPUTED":
                # A number not found in the dossier is not "probable" merely
                # because the dossier contains other data points.
                verdict = "UNVERIFIED"
                reason = "Angka dalam naskah tidak cocok dengan nilai data point yang tersedia di dossier."
                flags.append("UNLINKED_NUMERICAL_DETAIL")
                confidence = 0.25

        # 3. Check for Dossier Finding Match
        if dossier_data and verdict == "UNVERIFIED":
            for claim_obj in dossier_data.get("claims", []):
                c_text = claim_obj.get("text", "").lower()
                overlap = len(set(s_lower.split()).intersection(set(c_text.split())))
                if overlap >= 4:
                    dossier_status = str(claim_obj.get("status", "UNVERIFIED")).upper()
                    if dossier_status in {"VERIFIED", "PROBABLE"}:
                        verdict = dossier_status
                        reason = f"Dossier Corroboration: Terhubung dengan klaim riset '{claim_obj.get('text', '')[:60]}...'."
                        confidence = float(claim_obj.get("confidence_score", 0.8) or 0.8)
                    else:
                        verdict = "UNVERIFIED"
                        reason = (
                            f"Klaim terkait di dossier berstatus {dossier_status}; "
                            "kemiripan teks tidak cukup untuk menaikkan status bukti."
                        )
                        confidence = 0.25
                    break

        # 4. Standard Heuristic Verdict if still UNVERIFIED
        if verdict == "UNVERIFIED":
            if c_type == ClaimType.OPINION:
                verdict = "PROBABLE"
                reason = "Refleksi filosofis/sudut pandang editorial yang wajar."
                confidence = 0.70
            elif c_type == ClaimType.SPECULATION:
                verdict = "UNVERIFIED"
                reason = "Spekulasi masa depan atau proyeksi yang belum terbukti."
                confidence = 0.40
            else:
                # Factual claim types (QUANTITATIVE, HISTORICAL, CAUSAL, ECONOMIC, etc.)
                if any(w in s_lower for w in ["bps", "data", "survei", "penelitian", "studi", "sejarah", "abad", "resmi"]):
                    verdict = "PROBABLE"
                    reason = "Mengacu pada bukti historis/studi umum tanpa sanggahan langsung."
                    confidence = 0.75

        if verdict == "VERIFIED":
            verified_count += 1
        elif verdict == "PROBABLE":
            probable_count += 1
        elif verdict == "DISPUTED":
            disputed_count += 1
        else:
            unverified_count += 1

        audited_claims.append({
            "sentence_index": idx + 1,
            "sentence": sentence,
            "claim_type": c_type.value,
            "verdict": verdict,
            "confidence": confidence,
            "reason": reason,
            "flags": flags
        })

    # Derive the overall status from claims actually checked. An empty report
    # is UNKNOWN; unchecked factual claims cannot be promoted to VERIFIED.
    if disputed_count > 0:
        overall = "DISPUTED"
    elif not audited_claims:
        overall = "UNKNOWN"
    elif unverified_count > 0:
        overall = "UNVERIFIED"
    elif probable_count > 0:
        overall = "PROBABLE"
    else:
        overall = "VERIFIED"

    report = {
        "status": "ok",
        "overall_verdict": overall,
        "total_sentences_checked": len(audited_claims),
        "breakdown": {
            "verified": verified_count,
            "probable": probable_count,
            "disputed": disputed_count,
            "unverified": unverified_count
        },
        "pass_gate": overall == "VERIFIED",
        "claims": audited_claims
    }
    report["narrative_integrity"] = audit_narrative_integrity(
        script_text, dossier_data or {}, story_plan
    )
    # Fact-check verdict alone is not sufficient for editorial readiness.
    integrity_gate = report["narrative_integrity"]["gate_status"]
    report["editorial_gate"] = {
        "status": integrity_gate,
        "publication_approval": False,
        "reason": report["narrative_integrity"]["summary"],
    }
    return report


def audit_narrative_integrity(
    script_text: str,
    dossier_data: Optional[Dict[str, Any]] = None,
    story_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check that story-plan references and risky script details stay inside dossier evidence."""
    dossier_data = dossier_data or {}
    claims = dossier_data.get("claims", []) or []
    data_points = dossier_data.get("data_points", []) or []
    causal_relationships = dossier_data.get("causal_relationships", []) or []
    supported_claims = [
        claim for claim in claims if isinstance(claim, dict)
        and str(claim.get("status", "UNVERIFIED")).upper() in {"VERIFIED", "PROBABLE"}
    ]
    supported_text = " ".join(
        [str(c.get("text", "")) for c in supported_claims]
        + [str(dp.get("value", "")) + " " + str(dp.get("metric", "")) for dp in data_points if isinstance(dp, dict)]
    )
    findings: List[Dict[str, Any]] = []

    if story_plan:
        for beat in story_plan.get("beats", []) or []:
            if not isinstance(beat, dict):
                continue
            refs = beat.get("evidence_claims", []) or []
            if beat.get("evidence_status") == "SUPPORTED_CLAIM":
                invalid_refs = [
                    ref for ref in refs if not isinstance(ref, dict)
                    or str(ref.get("status", "UNVERIFIED")).upper() not in {"VERIFIED", "PROBABLE"}
                ]
                if not refs or invalid_refs:
                    findings.append({
                        "code": "STORY_PLAN_OVERSTATES_EVIDENCE",
                        "severity": "CRITICAL",
                        "beat_id": beat.get("beat_id", ""),
                        "message": "Beat ditandai didukung, tetapi referensi klaim tidak ada atau status buktinya belum mendukung.",
                        "recommendation": "Ubah status beat menjadi GAP_OR_QUESTION atau perbaiki referensi berdasarkan dossier.",
                    })

            dossier_by_id = {
                str(c.get("id", "")): c for c in claims
                if isinstance(c, dict) and c.get("id") not in (None, "")
            }
            for ref in refs:
                if not isinstance(ref, dict):
                    continue
                ref_id = str(ref.get("id", ""))
                source_claim = dossier_by_id.get(ref_id) if ref_id else None
                if ref_id and source_claim is None:
                    findings.append({
                        "code": "STORY_PLAN_CLAIM_REFERENCE_MISSING",
                        "severity": "HIGH",
                        "beat_id": beat.get("beat_id", ""),
                        "message": f"Referensi klaim '{ref_id}' tidak ditemukan di dossier.",
                        "recommendation": "Sinkronkan story plan dengan klaim yang benar-benar tersimpan di dossier.",
                    })
                elif source_claim and str(source_claim.get("status", "UNVERIFIED")).upper() not in {"VERIFIED", "PROBABLE"} and str(ref.get("status", "")).upper() in {"VERIFIED", "PROBABLE"}:
                    findings.append({
                        "code": "STORY_PLAN_PROMOTES_UNRESOLVED_CLAIM",
                        "severity": "CRITICAL",
                        "beat_id": beat.get("beat_id", ""),
                        "message": "Status klaim di story plan lebih kuat daripada status klaim sumber di dossier.",
                        "recommendation": "Turunkan status beat dan pertahankan ketidakpastian klaim.",
                    })

    narration = _extract_spoken_narration(script_text)
    sentences = _segment_sentences(narration)
    causal_markers = (
        "menyebabkan", "mengakibatkan", "memicu", "berujung pada",
        "pendorong utamanya", "penyebab utamanya", "karena itulah",
    )
    has_supported_causal_path = any(
        isinstance(item, dict) and item.get("cause") and item.get("mechanism")
        and str(item.get("status", "")).upper() in {"VERIFIED", "PROBABLE"}
        for item in causal_relationships
    )
    for sentence in sentences:
        lower = sentence.lower()
        if re.search(r"\b\d+(?:[.,]\d+)?\s*(?:%|persen|juta|miliar|triliun|tahun|orang|unit)\b", lower):
            numbers = re.findall(r"\d+(?:[.,]\d+)?", sentence)
            dossier_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", supported_text))
            missing = [number for number in numbers if number not in dossier_numbers]
            if missing:
                findings.append({
                    "code": "SCRIPT_NUMERIC_DETAIL_NOT_LINKED",
                    "severity": "HIGH",
                    "sentence": sentence,
                    "message": f"Detail angka {', '.join(missing)} tidak ditemukan pada klaim/data yang berstatus VERIFIED atau PROBABLE di dossier.",
                    "recommendation": "Hapus angka tersebut atau tambahkan sumber yang mendukungnya ke dossier dan jalankan fact-check ulang.",
                })
        if any(marker in lower for marker in causal_markers) and not has_supported_causal_path:
            findings.append({
                "code": "CAUSAL_ASSERTION_NEEDS_EVIDENCE",
                "severity": "MEDIUM",
                "sentence": sentence,
                "message": "Kalimat memakai bahasa sebab-akibat, tetapi dossier belum mencatat jalur kausal yang berstatus VERIFIED/PROBABLE.",
                "recommendation": "Ubah menjadi pertanyaan/hipotesis atau dukung dengan sumber yang menguji mekanisme kausal.",
            })

    # Stable de-duplication prevents repeated warnings for the same sentence/code.
    unique_findings = []
    seen = set()
    for finding in findings:
        key = (finding.get("code"), finding.get("sentence"), finding.get("beat_id"))
        if key not in seen:
            seen.add(key)
            unique_findings.append(finding)
    findings = unique_findings

    if any(item["severity"] == "CRITICAL" for item in findings):
        gate = "BLOCKED"
    elif findings or str(dossier_data.get("epistemic_status", "UNVERIFIED")).upper() != "VERIFIED":
        gate = "REVIEW_REQUIRED"
    else:
        gate = "ELIGIBLE_FOR_EDITORIAL_REVIEW"

    return {
        "schema_version": 1,
        "gate_status": gate,
        "summary": (
            f"{len(findings)} temuan integritas narasi; status gate {gate}. "
            "Status ini bukan persetujuan publikasi."
        ),
        "finding_count": len(findings),
        "findings": findings,
        "publication_approval": False,
    }
