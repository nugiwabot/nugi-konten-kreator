"""
engine/pipeline/research_dossier.py
===================================
Structured Research Dossier Engine for Nugi Content Intelligence Engine.

Decomposes research questions, collects multi-tier evidence from
BPS, OpenAlex, and Web Discovery, extracts claims and empirical data points,
tracks corroboration & contradictions, and produces both:
- research_dossier.json (machine-readable single source of truth)
- research_dossier.md (structured documentary briefing with narrative angles)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.providers.evidence_model import (
    Claim, EvidenceItem, Source, SourceTier, SourceType, DataPoint, classify_source_tier
)
import re
from engine.providers.research_base import ResearchProvider
from engine.providers.openalex_provider import OpenAlexProvider
from engine.providers.crossref_provider import CrossrefProvider
from engine.providers.gdelt_provider import GDELTProvider
from engine.providers.bps_provider import BPSDataProvider
from engine.providers.scholarly_providers import EuropePMCProvider, PubMedProvider
from engine.providers.search import (
    WebResearchProvider, DDGSWebResearchProvider, ResilientWebResearchProvider
)
from engine.intelligence.research import build_research_intelligence
from engine.intelligence.rss import RSSDiscoveryService
from engine.config import RSS_DISCOVERY_ENABLED

logger = logging.getLogger(__name__)


@dataclass
class ResearchDossier:
    """Complete structured research dossier."""
    topic: str
    research_question: str
    subquestions: List[str]
    key_findings: List[str]
    claims: List[Claim]
    evidence_items: List[EvidenceItem]
    primary_sources: List[Dict[str, Any]]
    secondary_sources: List[Dict[str, Any]]
    timeline: List[Dict[str, str]]
    causal_relationships: List[Dict[str, str]]
    entities: List[str]
    data_points: List[DataPoint]
    narrative_angles: List[Dict[str, str]]
    visual_implications: List[Dict[str, str]]
    # A transparent heuristic, not a statistical confidence interval.
    evidence_strength: float = 0.0
    epistemic_status: str = "VERIFIED"  # VERIFIED, PROBABLE, DISPUTED, UNVERIFIED
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    research_intelligence: Dict[str, Any] = field(default_factory=dict)
    evidence_gaps: List[Dict[str, Any]] = field(default_factory=list)
    claim_coverage: List[Dict[str, Any]] = field(default_factory=list)
    research_readiness: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "research_question": self.research_question,
            "subquestions": self.subquestions,
            "key_findings": self.key_findings,
            "evidence_strength": self.evidence_strength,
            "evidence_strength_method": "heuristic: source quality, claim coverage, independent lineage, and contradictions",
            "epistemic_status": self.epistemic_status,
            "claims": [c.to_dict() for c in self.claims],
            "evidence_items": [e.to_dict() for e in self.evidence_items],
            "primary_sources": self.primary_sources,
            "secondary_sources": self.secondary_sources,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "timeline": self.timeline,
            "causal_relationships": self.causal_relationships,
            "entities": self.entities,
            "narrative_angles": self.narrative_angles,
            "visual_implications": self.visual_implications,
            "created_at": self.created_at,
            "research_intelligence": self.research_intelligence,
            "evidence_gaps": self.evidence_gaps,
            "claim_coverage": self.claim_coverage,
            "research_readiness": self.research_readiness,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ResearchDossier:
        """Construct ResearchDossier from serialized dictionary."""
        claims = []
        for c in d.get("claims", []):
            if isinstance(c, Claim):
                claims.append(c)
            elif isinstance(c, dict):
                claims.append(Claim(
                    id=c.get("id", ""),
                    text=c.get("text", ""),
                    claim_type=c.get("claim_type", "FACTUAL"),
                    status=c.get("status", "UNVERIFIED"),
                    primary_source_count=c.get("primary_source_count", 0),
                    secondary_source_count=c.get("secondary_source_count", 0),
                    confidence_score=c.get("confidence_score", 0.0),
                    epistemic_notes=c.get("epistemic_notes", ""),
                    lineage_roots=c.get("lineage_roots", []),
                    independent_sources_count=c.get("independent_sources_count", 0),
                ))

        evidence_items = []
        for e in d.get("evidence_items", []):
            if isinstance(e, EvidenceItem):
                evidence_items.append(e)
            elif isinstance(e, dict):
                s_dict = e.get("source", {})
                tier_val = s_dict.get("tier", "S7")
                try:
                    tier_enum = SourceTier(tier_val)
                except Exception:
                    tier_enum = SourceTier.S7
                st_val = s_dict.get("source_type", "unknown")
                try:
                    st_enum = SourceType(st_val)
                except Exception:
                    st_enum = SourceType.UNKNOWN

                source_obj = Source(
                    url=s_dict.get("url", ""),
                    publisher=s_dict.get("publisher", ""),
                    tier=tier_enum,
                    source_type=st_enum,
                    title=s_dict.get("title", ""),
                    published_at=s_dict.get("published_at", ""),
                    retrieved_at=s_dict.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
                    reliability=s_dict.get("reliability", "MEDIUM"),
                    is_primary=s_dict.get("is_primary", False),
                    author=s_dict.get("author", ""),
                    metadata=s_dict.get("metadata", {}),
                )
                evidence_items.append(EvidenceItem(
                    id=e.get("id", ""),
                    claim_text=e.get("claim_text", ""),
                    source=source_obj,
                    exact_quote=e.get("exact_quote", ""),
                    retrieved_snippet=e.get("retrieved_snippet", ""),
                    source_description=e.get("source_description", ""),
                    summary=e.get("summary", ""),
                    data_points=[DataPoint(**dp) for dp in e.get("data_points", []) if isinstance(dp, dict)],
                    confidence=e.get("confidence", 1.0),
                    is_supporting=e.get("is_supporting", True),
                    corroboration_sources=e.get("corroboration_sources", []),
                    contradiction_notes=e.get("contradiction_notes", ""),
                    uncertainty_level=e.get("uncertainty_level", "LOW"),
                    lineage_root=e.get("lineage_root"),
                    cited_sources=e.get("cited_sources", []),
                    is_derivative=e.get("is_derivative", False),
                ))

        data_points = []
        for dp in d.get("data_points", []):
            if isinstance(dp, DataPoint):
                data_points.append(dp)
            elif isinstance(dp, dict):
                data_points.append(DataPoint(
                    metric=dp.get("metric", ""),
                    value=dp.get("value", ""),
                    unit=dp.get("unit", ""),
                    period=dp.get("period", ""),
                    entity=dp.get("entity", ""),
                    source_name=dp.get("source_name", ""),
                ))

        return cls(
            topic=d.get("topic", ""),
            research_question=d.get("research_question", ""),
            subquestions=d.get("subquestions", []),
            key_findings=d.get("key_findings", []),
            claims=claims,
            evidence_items=evidence_items,
            primary_sources=d.get("primary_sources", []),
            secondary_sources=d.get("secondary_sources", []),
            timeline=d.get("timeline", []),
            causal_relationships=d.get("causal_relationships", []),
            entities=d.get("entities", []),
            data_points=data_points,
            narrative_angles=d.get("narrative_angles", []),
            visual_implications=d.get("visual_implications", []),
            # Read legacy dossiers without perpetuating the misleading name.
            evidence_strength=d.get("evidence_strength", d.get("overall_confidence", 0.0)),
            epistemic_status=d.get("epistemic_status", "VERIFIED"),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            research_intelligence=d.get("research_intelligence", {}),
            evidence_gaps=d.get("evidence_gaps", []),
            claim_coverage=d.get("claim_coverage", []),
            research_readiness=d.get("research_readiness", {}),
        )

    def to_markdown(self) -> str:
        """Render a readable documentary dossier in Markdown."""
        lines = [
            f"# RESEARCH DOSSIER: {self.topic.upper()}",
            f"> **Generated:** {self.created_at} | **Status:** {self.epistemic_status} | **Evidence strength (heuristic):** {int(self.evidence_strength * 100)}%",
            "",
            "## 1. RESEARCH QUESTION & SUBQUESTIONS",
            f"**Core Question:** {self.research_question}",
            "",
            "**Subquestions:**",
        ]
        for idx, sq in enumerate(self.subquestions, 1):
            lines.append(f"- **Q{idx}:** {sq}")

        lines.extend([
            "",
            "## 2. KEY EMPIRICAL FINDINGS",
        ])
        for f in self.key_findings:
            lines.append(f"- {f}")

        if self.data_points:
            lines.extend([
                "",
                "## 3. KEY DATA POINTS & METRICS",
                "| Metric | Value | Unit | Period | Entity | Source |",
                "|---|---|---|---|---|---|",
            ])
            for dp in self.data_points:
                lines.append(
                    f"| {dp.metric} | {dp.value} | {dp.unit} | {dp.period or '-'} | {dp.entity or '-'} | {dp.source_name} |"
                )

        lines.extend([
            "",
            "## 4. CLAIMS & EVIDENCE MAPPING",
        ])
        for c in self.claims:
            badge = f"[{c.status}]"
            lines.append(f"### Claim: {c.text} {badge}")
            lines.append(f"- **Type:** {c.claim_type} | **Confidence:** {int(c.confidence_score * 100)}%")
            if c.supporting_evidence:
                lines.append("- **Supporting Evidence:**")
                for se in c.supporting_evidence:
                    lines.append(f"  - [{se.source.tier.value}] *{se.source.publisher}*: {se.summary}")
            if c.contradicting_evidence:
                lines.append("- **⚠️ Contradicting Evidence:**")
                for ce in c.contradicting_evidence:
                    lines.append(f"  - [{ce.source.tier.value}] *{ce.source.publisher}*: {ce.summary}")
            lines.append("")

        if self.research_readiness or self.evidence_gaps or self.claim_coverage:
            readiness = self.research_readiness or {}
            lines.extend([
                "",
                "## 4A. RESEARCH READINESS & EVIDENCE GAPS",
                f"- **Readiness:** {readiness.get('status', 'NOT_ASSESSED')}",
                f"- **Interpretation:** {readiness.get('summary', 'No readiness summary available.')}",
                f"- **Supporting claims:** {readiness.get('supporting_claims', 0)} / {readiness.get('claim_count', len(self.claims))}",
                f"- **Primary sources:** {readiness.get('primary_source_count', len(self.primary_sources))}",
            ])
            for gap in self.evidence_gaps:
                lines.append(f"- **Gap [{gap.get('severity', 'INFO')}]:** {gap.get('gap', '')} — {gap.get('next_action', '')}")
            for coverage in self.claim_coverage:
                lines.append(
                    f"- **Claim coverage [{coverage.get('status', 'UNVERIFIED')}]:** "
                    f"{coverage.get('claim', '')} | supporting sources: {coverage.get('supporting_source_count', 0)}; "
                    f"independent lineages: {coverage.get('independent_sources_count', 0)}"
                )

        lines.extend([
            "## 5. CAUSAL RELATIONSHIPS & HUMAN-PLACE ANCHOR",
        ])
        for cr in self.causal_relationships:
            lines.append(f"- **{cr.get('cause', '')}** → *{cr.get('effect', '')}* (Mechanism: {cr.get('mechanism', '')})")

        lines.extend([
            "",
            "## 6. NARRATIVE STORY ANGLES",
        ])
        for na in self.narrative_angles:
            lines.append(f"### Angle: {na.get('title', 'Perspective')}")
            lines.append(f"- **Core Revelation:** {na.get('revelation', '')}")
            lines.append(f"- **Human Dilemma:** {na.get('human_dilemma', '')}")
            lines.append(f"- **Deeper Why:** {na.get('why', '')}")
            lines.append("")

        lines.extend([
            "## 7. VISUAL & ARCHIVAL IMPLICATIONS (B-ROLL DIRECTIVE)",
        ])
        for vi in self.visual_implications:
            lines.append(f"- **Shot Need:** {vi.get('concept', '')} (Requirement: `{vi.get('requirement', 'GENERIC_ALLOWED')}`)")
            lines.append(f"  - Suggested Asset: {vi.get('asset_type', 'Footage')} | Source Strategy: {vi.get('strategy', '')}")

        lines.extend([
            "",
            "## 8. SOURCE PROVENANCE REGISTRY",
            "### Primary Sources (S0–S2):",
        ])
        for ps in self.primary_sources:
            lines.append(f"- **[{ps.get('tier', 'S1')}]** [{ps.get('publisher', '')}]({ps.get('url', '')}): *{ps.get('title', '')}* ({ps.get('published_at', '')})")

        lines.append("")
        lines.append("### Secondary Sources (S3–S6):")
        for ss in self.secondary_sources:
            lines.append(f"- **[{ss.get('tier', 'S4')}]** [{ss.get('publisher', '')}]({ss.get('url', '')}): *{ss.get('title', '')}*")

        intelligence = self.research_intelligence or {}
        if intelligence.get("rss_discoveries"):
            lines.extend(["", "## 9. RSS DISCOVERY LEADS (NOT VERIFIED EVIDENCE)"])
            for item in intelligence["rss_discoveries"][:20]:
                lines.append(
                    f"- [{item.get('source_name', 'Feed')}]({item.get('canonical_url', '')}): "
                    f"{item.get('title', '')} ({item.get('published_at', 'date unknown')}) — DISCOVERY_ONLY"
                )
        if intelligence.get("scholarly_discoveries") or intelligence.get("web_discoveries"):
            lines.extend(["", "## 9A. RESEARCH & SEARCH DISCOVERY LEADS (NOT CLAIM EVIDENCE)"])
            for item in (intelligence.get("scholarly_discoveries", []) + intelligence.get("web_discoveries", []))[:30]:
                lines.append(
                    f"- [{item.get('publisher', 'Discovery')}]({item.get('url', '')}): "
                    f"*{item.get('title', '')}* ({item.get('published_at', 'date unknown')}) — DISCOVERY_ONLY"
                )
        if intelligence.get("primary_source_queries"):
            lines.extend(["", "## 10. SOURCE ESCALATION QUERIES"])
            for query in intelligence["primary_source_queries"]:
                lines.append(f"- `{query}`")
            for result in intelligence.get("escalation_results", [])[:6]:
                lines.append(
                    f"  - Search lead: [{result.get('title', '')}]({result.get('url', '')}) "
                    f"— {result.get('publisher', '')}; NOT VERIFIED EVIDENCE"
                )

        return "\n".join(lines)


def _extract_entities_from_evidence(topic: str, all_evidence: List[EvidenceItem]) -> List[str]:
    """Extract distinct topic-grounded entities, institutions, and key concepts."""
    entities = set()
    # Extract from topic words
    words = re.findall(r"[A-Z][a-z0-9]+|\b[a-zA-Z]{4,}\b", topic)
    for w in words:
        if w.lower() not in ("tentang", "bagaimana", "mengapa", "kenapa", "adalah", "dengan", "untuk", "dalam", "pada", "oleh"):
            entities.add(w.title())

    # Extract from evidence publishers and titles
    for ev in all_evidence:
        if ev.source.publisher and ev.source.publisher not in ("Web", "Google"):
            entities.add(ev.source.publisher)
        title_words = re.findall(r"[A-Z][a-z0-9]+", ev.source.title)
        for tw in title_words:
            if len(tw) > 3 and tw.lower() not in ("overview", "study", "report", "journal", "analysis", "article"):
                entities.add(tw)

    # Extract from data points
    for ev in all_evidence:
        for dp in ev.data_points:
            if dp.entity:
                entities.add(dp.entity)

    # Fallback if empty
    if not entities:
        entities = {topic.title(), "Masyarakat", "Data Empiris"}
    return sorted(list(entities))[:10]


def _synthesize_topic_causality(topic: str, claims: List[Claim], all_evidence: List[EvidenceItem]) -> List[Dict[str, str]]:
    """Synthesizes dynamic cause-and-effect mechanisms specific to the researched topic."""
    links = []
    cause_1 = f"Dinamika struktural dan pendorong utama pada fenomena {topic}"
    effect_1 = f"Pergeseran nyata pada perilaku, ruang hidup, atau keputusan masyarakat terdampak"
    mech_1 = "Tekanan insentif dan adaptasi sistemik yang memaksa penyesuaian pola hidup"

    if len(claims) >= 2 and claims[1].text:
        cause_1 = f"Faktor pendorong: {claims[1].text[:80]}"
        mech_1 = "Mekanisme transmisi yang teridentifikasi dalam kajian riset empiris"

    if len(claims) >= 1 and claims[0].text:
        effect_1 = f"Konsekuensi terukur: {claims[0].text[:80]}"

    links.append({
        "cause": cause_1,
        "effect": effect_1,
        "mechanism": mech_1
    })

    links.append({
        "cause": f"Respon adaptif masyarakat dalam menghadapi pergeseran seputar {topic}",
        "effect": f"Terbentuknya kebiasaan dan kompromi harian baru dalam tatanan sosial",
        "mechanism": "Naluri bertahan hidup di tengah keterbatasan pilihan institusional"
    })

    return links


def _synthesize_narrative_angles(
    topic: str,
    claims: List[Claim],
    all_evidence: List[EvidenceItem],
    data_points: List[DataPoint]
) -> List[Dict[str, str]]:
    """Generates two distinct topic-specific editorial narrative angles."""
    claim_lead = claims[0].text[:80] if claims else f"dinamika {topic}"
    stat_summary = ""
    topic_words = set(re.findall(r"\w+", topic.lower()))
    relevant_dps = [dp for dp in data_points if any(w in dp.metric.lower() or w in (dp.entity or "").lower() for w in topic_words)]
    if relevant_dps:
        dp = relevant_dps[0]
        stat_summary = f" (indikator {dp.metric}: {dp.value} {dp.unit})"
    elif data_points:
        dp = data_points[0]
        stat_summary = f" (konteks {dp.metric}: {dp.value} {dp.unit})"

    return [
        {
            "title": f"Paradoks Empiris vs Persepsi Publik: {topic.title()}",
            "revelation": f"Apa yang selama ini dipandang publik sebagai anomali seputar {topic} ternyata didorong oleh {claim_lead}{stat_summary}.",
            "human_dilemma": f"Masyarakat terjepit antara ekspektasi lama vs realitas baru yang dipaksakan oleh dinamika {topic}.",
            "why": f"Struktur institusi dan regulasi sering kali lambat mengimbangi kecepatan transformasi {topic} di lapangan."
        },
        {
            "title": f"Dampak Eksistensial & Ruang Hidup Manusia",
            "revelation": f"Di balik angka dan perdebatan seputar {topic}, terdapat pengorbanan waktu dan adaptasi psikologis yang jarang terhitung.",
            "human_dilemma": f"Keharusan memilih jalan kompromi harian demi bertahan dalam lanskap baru {topic}.",
            "why": f"Ketiadaan jaminan risiko kolektif membebankan seluruh adaptasi langsung ke pundak setiap individu."
        }
    ]


def _synthesize_visual_implications(
    topic: str,
    entities: List[str],
    all_evidence: List[EvidenceItem]
) -> List[Dict[str, str]]:
    """Generates visual shot needs derived from actual entities and topic domain."""
    top_entity = entities[0] if entities else topic
    second_entity = entities[1] if len(entities) > 1 else "Dokumentasi Lapangan"

    return [
        {
            "concept": f"Dokumen resmi, arsip data, atau grafik indikator terkait {top_entity}",
            "requirement": "REAL_REQUIRED",
            "asset_type": "Data Visual / Archival Document",
            "strategy": f"Cari publikasi resmi, tabel data primer, atau arsip dokumenter {top_entity}"
        },
        {
            "concept": f"Aktivitas nyata subjek dan lingkungan operasional terkait {second_entity}",
            "requirement": "REAL_PREFERRED",
            "asset_type": "Documentary Footage / Photo",
            "strategy": f"Cari rekaman interaksi lapangan, fasilitas, atau ekosistem {second_entity}"
        },
        {
            "concept": f"Ekspresi manusia menghadapi dinamika perubahan dan tekanan seputar {topic}",
            "requirement": "GENERIC_ALLOWED",
            "asset_type": "B-roll Footage",
            "strategy": f"Cari footage suasana manusia, jalanan, atau ruang kerja yang mencerminkan ketegangan narasi"
        }
    ]


def _synthesize_timeline(topic: str, all_evidence: List[EvidenceItem]) -> List[Dict[str, str]]:
    """Constructs chronological stages relevant to the topic's evolution."""
    return [
        {
            "era": "Fase Pembentukan",
            "event": f"Latar belakang historis dan kondisi awal sebelum eskalasi fenomena {topic}"
        },
        {
            "era": "Fase Transformasi",
            "event": f"Titik balik krusial yang mempercepat perubahan dan memicu perdebatan publik saat ini"
        },
        {
            "era": "Fase Implikasi Depan",
            "event": f"Proyeksi dampak jangka panjang terhadap generasi penerus dan tatanan ruang sosial"
        }
    ]


def _topic_terms(topic: str) -> set[str]:
    stopwords = {
        "about", "after", "and", "atau", "bagaimana", "bagi", "dalam", "dan",
        "dari", "dengan", "di", "how", "ini", "ke", "kenapa", "mengapa",
        "of", "pada", "perihal", "tentang", "the", "untuk", "yang",
    }
    return {
        term for term in re.findall(r"[a-z0-9]+", topic.lower())
        if len(term) >= 4 and term not in stopwords
    }


def _topic_relevance_count(topic: str, text: str) -> int:
    """Simple overlap heuristic used only to avoid unrelated source-to-claim mapping."""
    return len(_topic_terms(topic) & set(re.findall(r"[a-z0-9]+", text.lower())))



def _build_evidence_gap_report(
    claims: List[Claim],
    evidence: List[EvidenceItem],
    data_points: List[DataPoint],
    discovery_count: int,
    depth: str,
) -> Dict[str, Any]:
    """Summarize evidence coverage and next actions without promoting search leads."""
    excluded_roles = {"DISCOVERY_ONLY", "RESEARCH_DISCOVERY", "BIBLIOGRAPHIC_DISCOVERY"}
    supporting = [
        item for item in evidence
        if item.is_supporting
        and item.source.metadata.get("evidence_role") not in excluded_roles
        and (item.exact_quote or item.retrieved_snippet)
    ]
    primary = {
        item.source.url or item.source.publisher for item in supporting
        if item.source.tier.rank <= 2 and (item.source.url or item.source.publisher)
    }
    coverage: List[Dict[str, Any]] = []
    gaps: List[Dict[str, str]] = []
    for claim in claims:
        claim_support = [
            item for item in claim.supporting_evidence
            if item.is_supporting
            and item.source.metadata.get("evidence_role") not in excluded_roles
            and (item.exact_quote or item.retrieved_snippet)
        ]
        coverage.append({
            "claim_id": claim.id,
            "claim": claim.text,
            "claim_type": claim.claim_type,
            "status": claim.status,
            "supporting_source_count": len({
                item.source.url or item.source.publisher for item in claim_support
                if item.source.url or item.source.publisher
            }),
            "independent_sources_count": claim.independent_sources_count,
            "has_contradiction": bool(claim.contradicting_evidence),
        })
        if claim.status in {"UNVERIFIED", "DISPUTED"}:
            gaps.append({
                "severity": "HIGH",
                "gap": f"Klaim '{claim.text[:140]}' berstatus {claim.status}.",
                "next_action": "Cari sumber yang langsung mendukung atau membantah klaim; jangan narasikan sebagai fakta terkonfirmasi.",
            })
        elif claim.status == "PROBABLE":
            gaps.append({
                "severity": "MEDIUM",
                "gap": f"Klaim '{claim.text[:140]}' belum VERIFIED.",
                "next_action": "Cari corroboration independen dan periksa apakah sumber mendukung klaim yang sama.",
            })
        if claim.claim_type in {"CAUSAL", "NUMERICAL"} and claim.independent_sources_count < 2:
            gaps.append({
                "severity": "HIGH" if claim.claim_type == "CAUSAL" else "MEDIUM",
                "gap": f"Klaim {claim.claim_type.lower()} belum memiliki dua jalur bukti independen.",
                "next_action": "Cari sumber primer atau penelitian independen yang menguji mekanisme/angka secara langsung.",
            })
    if not claims:
        gaps.append({
            "severity": "HIGH",
            "gap": "Belum ada klaim yang berhasil dibentuk dari bukti pendukung.",
            "next_action": "Persempit pertanyaan, cari dokumen primer/data resmi, lalu bentuk klaim atomik yang bisa diuji.",
        })
    if not primary:
        gaps.append({
            "severity": "HIGH",
            "gap": "Belum ada sumber primer/otoritatif yang dipakai sebagai bukti pendukung.",
            "next_action": "Prioritaskan data resmi, dokumen asli, arsip, atau penelitian sumber pertama.",
        })
    if not data_points:
        gaps.append({
            "severity": "MEDIUM",
            "gap": "Belum ada data point terstruktur yang berhasil diekstrak.",
            "next_action": "Cari statistik atau indikator yang sesuai; jangan mengarang angka.",
        })
    if depth == "quick":
        gaps.append({
            "severity": "INFO",
            "gap": "Riset memakai mode quick sehingga cakupan pencarian dan pemeriksaan kontradiksi terbatas.",
            "next_action": "Lakukan riset lebih mendalam sebelum menggunakan klaim penting dalam naskah.",
        })
    if discovery_count:
        gaps.append({
            "severity": "INFO",
            "gap": f"Ada {discovery_count} lead pencarian/RSS yang tetap terpisah dari bukti klaim.",
            "next_action": "Buka sumber asli dan verifikasi isi, konteks, tanggal, serta dukungannya; judul/snippet saja tidak cukup.",
        })
    verified = sum(c.status == "VERIFIED" for c in claims)
    probable = sum(c.status == "PROBABLE" for c in claims)
    disputed = sum(c.status == "DISPUTED" for c in claims)
    if not claims or verified == 0:
        status, summary = "INSUFFICIENT_EVIDENCE", "Belum ada klaim terverifikasi; dossier ini mengarahkan riset, bukan menjadi dasar klaim final."
    elif disputed:
        status, summary = "CONTRADICTIONS_REQUIRE_REVIEW", "Ada klaim yang diperselisihkan; selesaikan atau tampilkan perbedaan bukti secara eksplisit."
    elif probable or verified < len(claims) or not primary:
        status, summary = "PARTIAL_EVIDENCE", "Sebagian bukti tersedia, tetapi masih ada klaim yang memerlukan corroboration atau sumber primer."
    else:
        status, summary = "EVIDENCE_REVIEW_REQUIRED", "Klaim berstatus VERIFIED menurut heuristik; tinjauan editorial tetap wajib sebelum produksi."
    return {
        "research_readiness": {
            "status": status, "summary": summary, "claim_count": len(claims),
            "verified_claims": verified, "probable_claims": probable, "disputed_claims": disputed,
            "supporting_claims": sum(c.status in {"VERIFIED", "PROBABLE"} for c in claims),
            "primary_source_count": len(primary), "supporting_evidence_count": len(supporting),
            "discovery_leads_excluded": discovery_count, "depth": depth,
            "is_publication_approval": False,
        },
        "claim_coverage": coverage,
        "evidence_gaps": gaps,
    }


class DossierGenerator:
    """
    Orchestrates the entire research phase:
    1. Question decomposition
    2. Multi-provider retrieval (BPS, OpenAlex, Crossref, GDELT, Web)
    3. Epistemic extraction & claim-evidence mapping with contradiction search
    4. Topic-grounded dynamic synthesis & disk export
    """

    def __init__(
        self,
        bps_provider: Optional[ResearchProvider] = None,
        openalex_provider: Optional[ResearchProvider] = None,
        web_provider: Optional[WebResearchProvider] = None,
        crossref_provider: Optional[ResearchProvider] = None,
        gdelt_provider: Optional[ResearchProvider] = None,
        pubmed_provider: Optional[ResearchProvider] = None,
        europe_pmc_provider: Optional[ResearchProvider] = None,
    ):
        self.bps = bps_provider or BPSDataProvider()
        self.openalex = openalex_provider or OpenAlexProvider()
        self.web = web_provider or ResilientWebResearchProvider()
        self.crossref = crossref_provider or CrossrefProvider()
        self.gdelt = gdelt_provider or GDELTProvider()
        self.pubmed = pubmed_provider or PubMedProvider()
        self.europe_pmc = europe_pmc_provider or EuropePMCProvider()

    def build_dossier(
        self,
        topic: str,
        max_evidence_per_source: int = 4,
        depth: str = "deep",
        recency: Optional[str] = None,
    ) -> ResearchDossier:
        logger.info(f"DossierGenerator: Initiating research for '{topic}' (depth: {depth})")
        
        # Configure limit based on depth mode
        if depth == "quick":
            limit = 2
        elif depth == "investigative":
            limit = max(6, max_evidence_per_source)
        else:
            limit = max_evidence_per_source

        # 1. Question Decomposition
        subquestions = [
            f"Apa akar penyebab historis atau struktural di balik {topic}?",
            f"Data resmi dan statistik apa yang membuktikan skala fenomena ini?",
            f"Bagaimana riset akademik menjelaskan dampak fenomena ini pada perilaku manusia dan ruang hidup?",
            f"Apa kontradiksi antara persepsi publik vs realitas empiris di lapangan?",
            f"Siapa kelompok masyarakat yang paling terdampak dan bagaimana masa depannya?"
        ]

        # 2. Gather Evidence across Multi-Tier Providers
        bps_evidence = self.bps.search_evidence(topic, max_results=limit)
        academic_evidence = self.openalex.search_evidence(topic, max_results=limit)
        crossref_evidence = self.crossref.search_evidence(topic, max_results=limit)
        gdelt_evidence = self.gdelt.search_evidence(topic, max_results=limit)
        # PubMed/Europe PMC abstracts and records are discovery leads. They are
        # kept out of claim support until a cited publication is reviewed.
        pubmed_discoveries = self.pubmed.search_evidence(topic, max_results=limit)
        europe_pmc_discoveries = self.europe_pmc.search_evidence(topic, max_results=limit)
        # Only the web provider exposes a cross-provider recency contract.  It
        # must be passed through instead of being accepted only at the MCP edge.
        web_raw = self.web.search(topic, recency=recency, max_results=limit)

        web_evidence: List[EvidenceItem] = []
        for idx, w in enumerate(web_raw):
            cls = classify_source_tier(w.get("url", ""), w.get("publisher", ""))
            raw_content = w.get("content", "")

            s = Source(
                url=w.get("url", ""),
                publisher=w.get("publisher", w.get("source", "Web")),
                tier=cls["tier"],
                source_type=cls["source_type"],
                title=w.get("title", ""),
                published_at=w.get("date", ""),
                reliability=cls["reliability"],
                is_primary=cls["is_primary"],
                metadata={"evidence_role": "DISCOVERY_ONLY", "snippet_is_not_source_text": True},
            )
            item = EvidenceItem(
                id=f"web_{idx}",
                claim_text=raw_content[:200],
                source=s,
                # Web search returns a result snippet, not a source-verified
                # transcript. Keep it as a retrieved snippet, never a quote.
                exact_quote="",
                retrieved_snippet=raw_content,
                source_description=f"{w.get('publisher', 'Web')}: {w.get('title', '')}",
                summary=w.get("title", ""),
                confidence=0.75 if cls["tier"].rank <= 4 else 0.5,
                is_supporting=False,
                lineage_root=w.get("url", "")
            )
            web_evidence.append(item)

        # 2b. Contradiction / Counter-evidence search for deep/investigative modes
        contradiction_evidence: List[EvidenceItem] = []
        if depth in ("deep", "investigative"):
            try:
                contra_raw = self.web.search(
                    f"{topic} kritik mitos kegagalan resiko",
                    recency=recency,
                    max_results=2,
                )
                for c_idx, cw in enumerate(contra_raw):
                    c_cls = classify_source_tier(cw.get("url", ""), cw.get("publisher", ""))
                    c_content = cw.get("content", "")
                    c_s = Source(
                        url=cw.get("url", ""),
                        publisher=cw.get("publisher", "Web"),
                        tier=c_cls["tier"],
                        source_type=c_cls["source_type"],
                        title=cw.get("title", ""),
                        published_at=cw.get("date", ""),
                        reliability=c_cls["reliability"],
                        is_primary=c_cls["is_primary"],
                        metadata={"evidence_role": "DISCOVERY_ONLY", "snippet_is_not_source_text": True},
                    )
                    contra_item = EvidenceItem(
                        id=f"contra_{c_idx}",
                        claim_text=c_content[:200],
                        source=c_s,
                        exact_quote="",
                        retrieved_snippet=c_content,
                        source_description=f"Perspektif kritis/kontradiktif: {cw.get('title', '')}",
                        summary=f"Sisi kritis/alternatif: {cw.get('title', '')}",
                        confidence=0.6,
                        is_supporting=False,
                        contradiction_notes="Menyoroti perdebatan, keterbatasan data, atau sudut pandang alternatif",
                        lineage_root=cw.get("url", "")
                    )
                    contradiction_evidence.append(contra_item)
            except Exception as e:
                logger.info(f"Contradiction probe skipped: {e}")

        # Enforce strict S0-S7 hierarchy: S0 (Archival) -> S1 (BPS/Gov) -> S2 (Academic/Crossref) -> S3 (Wire) -> S4-S7
        all_discoveries = (
            crossref_evidence + gdelt_evidence + pubmed_discoveries
            + europe_pmc_discoveries + web_evidence + contradiction_evidence
        )
        all_collected = [
            item for item in (bps_evidence + academic_evidence)
            if item.is_supporting
        ]
        all_collected.extend(item for item in gdelt_evidence if item.is_supporting)
        all_collected.sort(key=lambda ev: (ev.source.tier.rank, -ev.confidence))
        all_evidence = all_collected

        # 3. Aggregate Data Points
        all_data_points: List[DataPoint] = []
        for ev in all_evidence:
            all_data_points.extend(ev.data_points)

        # 4. Formulate Synthesized Claims & Mapping
        claims: List[Claim] = []
        
        # Claim 1: Macro / Statistical Dimension (S1 Primary)
        if bps_evidence and bps_evidence[0].is_supporting:
            c1 = Claim(
                id="claim_structural_data",
                text=bps_evidence[0].claim_text,
                claim_type="NUMERICAL",
                supporting_evidence=[bps_evidence[0]],
                primary_source_count=1,
            )
            c1.evaluate_status()
            claims.append(c1)

        # Claim 2: Academic / Mechanism Dimension (S2 Specialist)
        acad_support = [
            item for item in academic_evidence
            if item.is_supporting
            and (item.retrieved_snippet or item.exact_quote)
            and _topic_relevance_count(topic, item.retrieved_snippet or item.exact_quote) >= max(1, min(2, len(_topic_terms(topic))))
        ]
        # Crossref provides bibliographic metadata only, so its entries remain
        # source leads and do not support a factual or mechanistic claim.
            
        if acad_support:
            c2 = Claim(
                id="claim_academic_mechanism",
                text=acad_support[0].claim_text,
                claim_type="CAUSAL",
                # Other papers found for the broad query do not automatically
                # corroborate this particular abstract's statement.
                supporting_evidence=[acad_support[0]],
                primary_source_count=1,
            )
            c2.evaluate_status()
            claims.append(c2)

        # Claim 3: Ground Reality & Sentiment (S3-S4 Media & Public)
        media_support: List[EvidenceItem] = []

        if media_support:
            # Only attach counter-evidence to Claim 3 if in investigative depth
            c3_contra = contradiction_evidence[:1] if (contradiction_evidence and depth == "investigative") else []
            c3 = Claim(
                id="claim_public_reality",
                text=media_support[0].claim_text,
                claim_type="FACTUAL",
                supporting_evidence=[media_support[0]],
                contradicting_evidence=c3_contra,
                secondary_source_count=len(media_support),
            )
            c3.evaluate_status()
            claims.append(c3)

        # 5. Extract Sources by Provenance
        primary_sources = []
        secondary_sources = []
        seen_urls = set()

        for ev in all_evidence:
            u = ev.source.url
            if not u or u in seen_urls:
                continue
            seen_urls.add(u)
            entry = ev.source.to_dict()
            if ev.source.tier.rank <= 2:
                primary_sources.append(entry)
            else:
                secondary_sources.append(entry)

        # 6. Key Findings (Topic-grounded, not hardcoded)
        key_findings: List[str] = []
        if claims:
            key_findings.append(f"Fakta utama teridentifikasi: {claims[0].text[:120]}")
        if len(claims) > 1:
            key_findings.append(f"Mekanisme penjelas: {claims[1].text[:120]}")
        if all_data_points:
            dp0 = all_data_points[0]
            key_findings.append(f"Indikator terukur: {dp0.metric} tercatat sebesar {dp0.value} {dp0.unit} ({dp0.source_name}).")
        if not key_findings:
            key_findings.append("Tidak ada bukti yang dapat diverifikasi berhasil diambil pada sesi riset ini.")

        # 7. Topic-Grounded Synthesis
        entities = _extract_entities_from_evidence(topic, all_evidence)
        causal_relationships = _synthesize_topic_causality(topic, claims, all_evidence)
        narrative_angles = _synthesize_narrative_angles(topic, claims, all_evidence, all_data_points)
        visual_implications = _synthesize_visual_implications(topic, entities, all_evidence)
        timeline = _synthesize_timeline(topic, all_evidence)

        # Determine overall epistemic status
        has_disputes = any(c.status == "DISPUTED" for c in claims)
        all_verified = all(c.status == "VERIFIED" for c in claims) if claims else False
        primary_verified = any(c.status == "VERIFIED" and c.id in ("claim_structural_data", "claim_academic_mechanism") for c in claims)

        if not claims:
            epistemic_status = "UNVERIFIED"
        elif all_verified:
            epistemic_status = "VERIFIED"
        elif has_disputes and not primary_verified:
            epistemic_status = "DISPUTED"
        else:
            epistemic_status = "PROBABLE"

        evidence_strength = self._calculate_evidence_strength(claims, all_evidence)

        research_intelligence = {}
        if RSS_DISCOVERY_ENABLED:
            try:
                feed_items = RSSDiscoveryService().discover(topic, max_items=20)
                intelligence = build_research_intelligence(
                    topic, feed_items, recency=recency, evidence_entities=entities
                )
                # Escalation heads are bounded follow-up query seeds. Search
                # snippets remain leads; structured literature hits are also
                # captured below without becoming claim evidence.
                for query in intelligence.primary_source_queries[:2]:
                    pubmed_discoveries.extend(self.pubmed.search_evidence(query, max_results=2))
                    europe_pmc_discoveries.extend(self.europe_pmc.search_evidence(query, max_results=2))
                for query in intelligence.primary_source_queries[:2]:
                    try:
                        search_rows = self.web.search(query, recency=recency, max_results=2)
                    except Exception as exc:
                        logger.info("Primary-source follow-up search skipped: %s", exc)
                        search_rows = []
                    for row in search_rows:
                        intelligence.escalation_results.append({
                            "title": str(row.get("title", ""))[:500],
                            "url": str(row.get("url", ""))[:2000],
                            "publisher": str(row.get("publisher", row.get("source", "Web")))[:200],
                            "published_at": str(row.get("date", ""))[:120],
                            "query": query,
                            "evidence_status": "DISCOVERY_ONLY",
                        })
                research_intelligence = intelligence.to_dict()
            except Exception as exc:
                logger.info("RSS discovery skipped after adapter error: %s", exc)
        else:
            research_intelligence = build_research_intelligence(
                topic, recency=recency, evidence_entities=entities
            ).to_dict()

        def discovery_record(item: EvidenceItem) -> Dict[str, Any]:
            return {
                "id": item.id,
                "title": item.source.title or item.summary,
                "url": item.source.url,
                "publisher": item.source.publisher,
                "published_at": item.source.published_at,
                "source_tier": item.source.tier.value,
                "evidence_role": item.source.metadata.get("evidence_role", "RESEARCH_DISCOVERY"),
                "abstract_preview": (item.retrieved_snippet or "")[:600],
                "exact_quote": "",
                "lineage_root": item.lineage_root or item.source.url,
                "evidence_status": "DISCOVERY_ONLY",
            }

        research_intelligence["research_discoveries"] = [
            discovery_record(item) for item in all_discoveries
        ][:100]
        research_intelligence["scholarly_discoveries"] = [
            discovery_record(item) for item in (pubmed_discoveries + europe_pmc_discoveries)
        ][:40]
        research_intelligence["web_discoveries"] = [
            discovery_record(item) for item in web_evidence
        ][:20]

        evidence_report = _build_evidence_gap_report(claims, all_evidence, all_data_points, len(all_discoveries), depth)

        return ResearchDossier(
            topic=topic,
            research_question=f"Mengapa fenomena {topic} terjadi dan bagaimana dampak nyatanya terhadap manusia?",
            subquestions=subquestions,
            key_findings=key_findings,
            claims=claims,
            evidence_items=all_evidence,
            primary_sources=primary_sources,
            secondary_sources=secondary_sources,
            timeline=timeline,
            causal_relationships=causal_relationships,
            entities=entities,
            data_points=all_data_points,
            narrative_angles=narrative_angles,
            visual_implications=visual_implications,
            evidence_strength=evidence_strength,
            epistemic_status=epistemic_status,
            research_intelligence=research_intelligence,
            evidence_gaps=evidence_report["evidence_gaps"],
            claim_coverage=evidence_report["claim_coverage"],
            research_readiness=evidence_report["research_readiness"],
        )

    @staticmethod
    def _calculate_evidence_strength(
        claims: List[Claim],
        evidence: List[EvidenceItem],
    ) -> float:
        """Return an explainable heuristic score; it is not a confidence claim."""
        usable_evidence = [
            item for item in evidence
            if item.is_supporting
            and item.source.metadata.get("evidence_role") not in {"DISCOVERY_ONLY", "RESEARCH_DISCOVERY", "BIBLIOGRAPHIC_DISCOVERY"}
            and (item.exact_quote or item.retrieved_snippet)
        ]
        if not usable_evidence:
            return 0.0

        quality = sum(max(0.0, 1.0 - (item.source.tier.rank / 8.0)) for item in usable_evidence) / len(usable_evidence)
        if claims:
            claim_support = sum(
                1.0 if claim.status == "VERIFIED" else 0.65 if claim.status == "PROBABLE" else 0.25 if claim.status == "UNVERIFIED" else 0.0
                for claim in claims
            ) / len(claims)
            independent = min(
                1.0,
                sum(max(1, claim.independent_sources_count) for claim in claims) / (2.0 * len(claims)),
            )
            contradiction_penalty = 0.2 if any(claim.status == "DISPUTED" for claim in claims) else 0.0
        else:
            claim_support = 0.0
            independent = 0.0
            contradiction_penalty = 0.0
        return round(max(0.0, min(1.0, 0.45 * quality + 0.4 * claim_support + 0.15 * independent - contradiction_penalty)), 3)

    def save_dossier_to_workspace(
        self,
        dossier: ResearchDossier,
        output_dir: Path
    ) -> Dict[str, str]:
        """Saves dossier as both research_dossier.json and research_dossier.md."""
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "research_dossier.json"
        md_path = output_dir / "research_dossier.md"

        json_path.write_text(json.dumps(dossier.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        md_path.write_text(dossier.to_markdown(), encoding="utf-8")

        return {
            "json_path": str(json_path),
            "md_path": str(md_path)
        }

