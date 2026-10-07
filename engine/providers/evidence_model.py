"""
engine/providers/evidence_model.py
==================================
Normalized Evidence Model and Source Hierarchy (S0–S7)
for Nugi Content Intelligence Engine.

Provides epistemic separation, provenance tracking, claim-to-evidence links,
corroboration, contradiction detection, and uncertainty modeling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class SourceTier(str, Enum):
    """
    Heuristic source hierarchy: S0 to S7.
    Context-sensitive evidentiary evaluation.
    """
    S0 = "S0"  # Direct / first-hand evidence / raw archival document / transcript
    S1 = "S1"  # Primary / authoritative sources (BPS, BI, OJK, official gov, legal statutes)
    S2 = "S2"  # Specialist research (peer-reviewed journals, universities, think-tanks)
    S3 = "S3"  # Professional journalism / wire services (Reuters, Bloomberg, AP)
    S4 = "S4"  # Reputable general media (Kompas, Tempo, Bisnis Indonesia, BBC, NYT)
    S5 = "S5"  # Trade / industry publications (TechCrunch, Lamudi, Inman, Rumah123)
    S6 = "S6"  # Community / social / blogs / user-generated content (Reddit, Twitter, Medium)
    S7 = "S7"  # Weak / unverified / low-provenance / anonymous claims

    @property
    def rank(self) -> int:
        return int(self.value[1])

    @property
    def label(self) -> str:
        labels = {
            "S0": "Direct / First-Hand Evidence",
            "S1": "Primary / Authoritative Source",
            "S2": "Specialist Academic / Institutional Research",
            "S3": "Professional Journalism / Wire Service",
            "S4": "Reputable General Media",
            "S5": "Trade & Industry Publication",
            "S6": "Community / Social / Web Commentary",
            "S7": "Weak / Unverified Material",
        }
        return labels.get(self.value, "Unknown Source Tier")

    @property
    def default_reliability(self) -> str:
        if self.rank <= 2:
            return "HIGH"
        if self.rank <= 4:
            return "MEDIUM_HIGH"
        if self.rank == 5:
            return "MEDIUM"
        return "LOW_NEEDS_VERIFICATION"


class SourceType(str, Enum):
    DIRECT = "direct"
    GOVERNMENT = "government"
    STATISTICS = "statistics"
    ACADEMIC = "academic"
    NEWS_WIRE = "news_wire"
    NEWS_GENERAL = "news_general"
    INDUSTRY = "industry"
    ARCHIVE = "archive"
    SOCIAL = "social"
    UNKNOWN = "unknown"


def classify_source_tier(url: str, publisher: str = "") -> Dict[str, Any]:
    """
    Master S0-S7 Source Quality Classifier.
    Evaluates domain and publisher according to evidentiary provenance.
    """
    domain = urlparse(url).netloc.lower() if url else (publisher.lower() if publisher else "")
    
    # S0: Direct Archival / Raw Evidence Repositories
    if any(d in domain for d in ["archive.org", "commons.wikimedia.org", "loc.gov", "nationalarchives.gov.uk"]):
        return {
            "tier": SourceTier.S0,
            "source_type": SourceType.ARCHIVE,
            "tier_name": SourceTier.S0.label,
            "reliability": "HIGH",
            "is_primary": True
        }

    # S1: Primary / Authoritative Government & Regulators & Statutes
    if any(d in domain for d in [".go.id", ".gov", "bps.go.id", "bi.go.id", "ojk.go.id", "peraturan.go.id", "kemenkeu.go.id", "bappenas.go.id", "atrbpn.go.id"]):
        return {
            "tier": SourceTier.S1,
            "source_type": SourceType.GOVERNMENT,
            "tier_name": SourceTier.S1.label,
            "reliability": "HIGH",
            "is_primary": True
        }

    # S2: Specialist Academic & Research Institutions
    if any(d in domain for d in [".edu", ".ac.id", "arxiv.org", "openalex.org", "doi.org", "nature.com", "science.org", "sciencedirect.com", "jstor.org", "crossref.org", "semanticscholar.org"]):
        return {
            "tier": SourceTier.S2,
            "source_type": SourceType.ACADEMIC,
            "tier_name": SourceTier.S2.label,
            "reliability": "HIGH",
            "is_primary": True
        }

    # S3: Professional Journalism & Wire Services
    if any(d in domain for d in ["reuters.com", "bloomberg.com", "apnews.com", "afp.com"]):
        return {
            "tier": SourceTier.S3,
            "source_type": SourceType.NEWS_WIRE,
            "tier_name": SourceTier.S3.label,
            "reliability": "HIGH",
            "is_primary": False
        }

    # S4: Reputable General Media
    if any(d in domain for d in ["kompas.com", "tempo.co", "bisnis.com", "katadata.co.id", "kontan.co.id", "bbc.com", "nytimes.com", "wsj.com", "theguardian.com", "economist.com"]):
        return {
            "tier": SourceTier.S4,
            "source_type": SourceType.NEWS_GENERAL,
            "tier_name": SourceTier.S4.label,
            "reliability": "MEDIUM_HIGH",
            "is_primary": False
        }

    # S5: Trade & Industry Publications
    if any(d in domain for d in ["techcrunch.com", "inman.com", "venturebeat.com", "rumah123.com", "lamudi.co.id", "housecanary.com", "knightfrank.com", "cbre.com"]):
        return {
            "tier": SourceTier.S5,
            "source_type": SourceType.INDUSTRY,
            "tier_name": SourceTier.S5.label,
            "reliability": "MEDIUM",
            "is_primary": False
        }

    # S6: Community, Social, Forum, UGC
    if any(d in domain for d in ["twitter.com", "x.com", "reddit.com", "tiktok.com", "instagram.com", "medium.com", "substack.com", "quora.com", "facebook.com", "threads.net"]):
        return {
            "tier": SourceTier.S6,
            "source_type": SourceType.SOCIAL,
            "tier_name": SourceTier.S6.label,
            "reliability": "LOW_NEEDS_VERIFICATION",
            "is_primary": False
        }

    # S7: Default / Generic Web / Low Provenance
    return {
        "tier": SourceTier.S7,
        "source_type": SourceType.UNKNOWN,
        "tier_name": SourceTier.S7.label,
        "reliability": "LOW_NEEDS_VERIFICATION",
        "is_primary": False
    }


@dataclass
class Source:
    """Source provenance and categorization."""
    url: str
    publisher: str
    tier: SourceTier
    source_type: SourceType = SourceType.UNKNOWN
    title: str = ""
    published_at: str = ""
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reliability: str = "MEDIUM"
    is_primary: bool = False
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        d["tier_label"] = self.tier.label
        d["source_type"] = self.source_type.value
        return d


@dataclass
class DataPoint:
    """Quantitative or empirical measurement extracted from evidence."""
    metric: str
    value: Any
    unit: str = ""
    period: str = ""
    entity: str = ""
    source_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    """Atomic verifiable piece of evidence backing or refuting a claim."""
    id: str
    claim_text: str
    source: Source
    exact_quote: str = ""  # MUST strictly contain real verbatim quote text only.
    retrieved_snippet: str = ""  # Raw passage or snippet retrieved from search/API.
    source_description: str = ""  # Narrative or metadata description of the evidence.
    summary: str = ""
    data_points: List[DataPoint] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 to 1.0
    is_supporting: bool = True  # False if contradictory
    corroboration_sources: List[str] = field(default_factory=list)
    contradiction_notes: str = ""
    uncertainty_level: str = "LOW"  # LOW, MODERATE, HIGH
    lineage_root: Optional[str] = None  # URL or publisher of root original evidence
    cited_sources: List[str] = field(default_factory=list)  # Referenced sources/documents
    is_derivative: bool = False  # True if reporting cites another entity rather than original research

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source"] = self.source.to_dict()
        d["data_points"] = [dp.to_dict() for dp in self.data_points]
        return d


def evaluate_recency(published_at: str, topic_mode: str = "general") -> Dict[str, Any]:
    """
    Evaluates source freshness and recency alignment.
    Distinguishes historical vs current vs outdated sources.
    """
    if not published_at:
        return {
            "publication_year": None,
            "temporal_category": "UNKNOWN",
            "is_outdated": False,
            "notes": "No publication date available."
        }

    # Extract 4-digit year
    m = re.search(r"\b(19\d{2}|20\d{2})\b", str(published_at))
    if not m:
        return {
            "publication_year": None,
            "temporal_category": "UNKNOWN",
            "is_outdated": False,
            "notes": f"Could not parse year from: '{published_at}'"
        }

    year = int(m.group(1))
    current_year = datetime.now(timezone.utc).year
    age = current_year - year

    if age <= 1:
        category = "CURRENT"
    elif age <= 3:
        category = "RECENT"
    elif age <= 10:
        category = "MODERATE"
    else:
        category = "HISTORICAL"

    is_outdated = False
    if topic_mode.lower() in ("current", "news", "breaking") and age > 3:
        is_outdated = True

    return {
        "publication_year": year,
        "age_years": age,
        "temporal_category": category,
        "is_outdated": is_outdated,
        "notes": f"Source is {age} years old ({category})."
    }


@dataclass
class Claim:
    """
    Atomic assertion made in research or narrative script.
    """
    id: str
    text: str
    claim_type: str = "FACTUAL"  # FACTUAL, CAUSAL, NUMERICAL, HISTORICAL, OPINION
    status: str = "UNVERIFIED"   # VERIFIED, PROBABLE, DISPUTED, UNVERIFIED
    supporting_evidence: List[EvidenceItem] = field(default_factory=list)
    contradicting_evidence: List[EvidenceItem] = field(default_factory=list)
    primary_source_count: int = 0
    secondary_source_count: int = 0
    confidence_score: float = 0.0
    epistemic_notes: str = ""
    lineage_roots: List[str] = field(default_factory=list)
    independent_sources_count: int = 0

    def evaluate_status(self) -> str:
        """
        Calculates verification status according to S0-S7 evidence strength
        and independent lineage verification.
        """
        has_contradiction = len(self.contradicting_evidence) > 0
        if has_contradiction:
            self.status = "DISPUTED"
            return self.status

        if not self.supporting_evidence:
            self.status = "UNVERIFIED"
            return self.status

        # Deduplicate evidence lineage to prevent syndicated repetition from inflating corroboration
        lineage_map: Dict[str, List[EvidenceItem]] = {}
        for e in self.supporting_evidence:
            root = e.lineage_root or (e.source.url if e.source.url else e.source.publisher)
            lineage_map.setdefault(root, []).append(e)

        self.lineage_roots = list(lineage_map.keys())
        self.independent_sources_count = len(lineage_map)

        # Count authoritative evidence (S0, S1, S2)
        auth_count = sum(
            1 for e in self.supporting_evidence if e.source.tier.rank <= 2
        )
        rep_count = sum(
            1 for e in self.supporting_evidence if 3 <= e.source.tier.rank <= 4
        )

        if auth_count >= 1 or (rep_count >= 2 and self.independent_sources_count >= 2):
            self.status = "VERIFIED"
            self.confidence_score = 0.9 if auth_count >= 1 else 0.8
        elif rep_count >= 1 or len(self.supporting_evidence) >= 2 or self.independent_sources_count >= 1:
            self.status = "PROBABLE"
            self.confidence_score = 0.65
        else:
            self.status = "UNVERIFIED"
            self.confidence_score = 0.35

        return self.status

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["supporting_evidence"] = [e.to_dict() for e in self.supporting_evidence]
        d["contradicting_evidence"] = [e.to_dict() for e in self.contradicting_evidence]
        return d

