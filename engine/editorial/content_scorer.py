"""
engine/editorial/content_scorer.py
==================================
10-Dimension Content Quality Evaluator for Nugi Content Intelligence Engine.

Scores production content packages against Nugi's editorial and epistemic standards:
1. Research Strength
2. Source Quality
3. Evidence Coverage
4. Claim Confidence
5. Story Strength
6. Human Relevance
7. Hook Strength
8. Originality
9. Visual Feasibility
10. Publishability

Provides explicit pass/review/reject status with actionable diagnostics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ContentQualityReport:
    overall_score: int  # 0 to 100
    status: str  # PUBLISH_READY, MINOR_EDIT, NEEDS_REVIEW, REJECT_AND_RESEARCH_AGAIN
    dimension_scores: Dict[str, float]  # 10 dimensions, 0.0 to 10.0 each
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    topic: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContentQualityEvaluator:
    """
    Evaluates research dossiers, scripts, fact-check audits, and visual shot plans.
    """

    def evaluate(
        self,
        topic: str,
        dossier_data: Dict[str, Any],
        script_text: str,
        fact_check_result: Dict[str, Any],
        shots_data: List[Dict[str, Any]],
        downloaded_assets: List[Dict[str, Any]],
    ) -> ContentQualityReport:
        blockers = []
        warnings = []
        dim = {}

        # 1. Research Strength (0 - 10)
        # Evaluates multi-source diversity and authoritative presence (S0-S2)
        primary_sources = dossier_data.get("primary_sources", [])
        evidence_items = dossier_data.get("evidence_items", [])
        if len(primary_sources) >= 2:
            dim["research_strength"] = 10.0
        elif len(primary_sources) == 1:
            dim["research_strength"] = 8.5
        elif len(evidence_items) >= 4:
            dim["research_strength"] = 7.0
        else:
            dim["research_strength"] = 5.0
            warnings.append("Bukti riset primer terbatas (<1 sumber S0-S2).")

        # 2. Source Quality (0 - 10)
        # Evaluates source tiers and reliability
        high_tier_count = sum(1 for ps in primary_sources if ps.get("tier") in ("S0", "S1", "S2"))
        if high_tier_count >= 2:
            dim["source_quality"] = 9.5
        elif high_tier_count == 1:
            dim["source_quality"] = 8.0
        else:
            dim["source_quality"] = 6.0
            warnings.append("Sebagian besar sumber merupakan kutipan sekunder (S4-S7).")

        # 3. Evidence Coverage (0 - 10)
        # Ratio of claims backed by supporting evidence
        claims = dossier_data.get("claims", [])
        if not claims:
            dim["evidence_coverage"] = 4.0
            blockers.append("Tidak ada klaim terstruktur yang terdaftar dalam research dossier.")
        else:
            backed = sum(1 for c in claims if c.get("supporting_evidence"))
            cov_ratio = backed / len(claims)
            dim["evidence_coverage"] = round(cov_ratio * 10.0, 1)
            if cov_ratio < 0.6:
                warnings.append("Lebih dari 40% klaim riset belum memiliki bukti pendukung langsung.")

        # 4. Claim Confidence & Fact Check Verdict (0 - 10)
        overall_verdict = fact_check_result.get("overall_verdict", "UNVERIFIED")
        breakdown = fact_check_result.get("breakdown", {})
        disputed = breakdown.get("disputed", 0)
        unverified = breakdown.get("unverified", 0)

        if disputed > 0:
            dim["claim_confidence"] = 4.0
            blockers.append(f"Terdapat {disputed} pernyataan dalam naskah yang berstatus DISPUTED / overclaim.")
        elif overall_verdict == "VERIFIED" and fact_check_result.get("pass_gate") is True:
            dim["claim_confidence"] = 9.5
        elif overall_verdict == "PROBABLE":
            dim["claim_confidence"] = 8.0
            blockers.append("Fact-check berstatus PROBABLE; bukti belum cukup untuk melewati publish gate.")
        else:
            dim["claim_confidence"] = 6.0
            warnings.append(f"Terdapat {unverified} pernyataan naratif yang belum terverifikasi secara empiris.")
            blockers.append(f"Fact-check berstatus {overall_verdict}; publish gate belum lulus.")

        # 5. Story Strength (0 - 10)
        # Structural teleprompter chapters: HOOK, TENSION, CAUSE, REVELATION
        has_hook = "HOOK" in script_text
        has_tension = "TENSION" in script_text or "PARADOX" in script_text
        has_cause = "CAUSE" in script_text or "CONTEXT" in script_text
        has_revelation = "REVELATION" in script_text or "WHY" in script_text
        structure_count = sum([has_hook, has_tension, has_cause, has_revelation])
        dim["story_strength"] = round((structure_count / 4.0) * 10.0, 1)
        if structure_count < 3:
            warnings.append("Struktur naskah tidak lengkap mengikuti bab teleprompter Nugi.")

        # 6. Human Relevance (0 - 10)
        # Presence of human dilemma / consequence in script or angles
        s_lower = script_text.lower()
        has_human_words = any(w in s_lower for w in ["manusia", "masyarakat", "kita", "orang", "kehidupan", "hidup", "warga", "individu"])
        narrative_angles = dossier_data.get("narrative_angles", [])
        has_dilemma = any("human_dilemma" in na for na in narrative_angles)
        if has_human_words and has_dilemma:
            dim["human_relevance"] = 9.5
        elif has_human_words or has_dilemma:
            dim["human_relevance"] = 8.0
        else:
            dim["human_relevance"] = 5.0
            warnings.append("Keterikatan dimensi manusiawi (HUMAN × WHY) belum tampak kuat dalam naskah.")

        # 7. Hook Strength (0 - 10)
        # Curiosity gap vs generic clickbait
        clickbait_patterns = ["pasti kaya", "cuan 100%", "klik link", "wajib tahu", "rahasia terbongkar"]
        has_clickbait = any(cb in s_lower for cb in clickbait_patterns)
        if has_clickbait:
            dim["hook_strength"] = 4.0
            blockers.append("Hook memuat frasa clickbait/promosi terlarang.")
        elif has_hook:
            dim["hook_strength"] = 9.0
        else:
            dim["hook_strength"] = 6.0

        # 8. Originality & Anti-Filler (0 - 10)
        # Scan for robotic filler
        ai_fillers = ["di era modern ini", "di era digital yang serba cepat", "fenomena ini menarik", "tentu saja hal ini"]
        filler_found = [f for f in ai_fillers if f in s_lower]
        if filler_found:
            dim["originality"] = 6.0
            warnings.append(f"Ditemukan klise robotik generik: {', '.join(filler_found)}")
        else:
            dim["originality"] = 9.5

        # 9. Visual Feasibility (0 - 10)
        # Shot plan coverage and requirement assignments
        if not shots_data:
            dim["visual_feasibility"] = 4.0
            warnings.append("Belum ada rencana visual shot (broll_plan.json).")
        else:
            has_real_pref = any(s.get("visual_requirement") in ("REAL_REQUIRED", "REAL_PREFERRED") for s in shots_data)
            dim["visual_feasibility"] = 9.5 if has_real_pref else 8.0

        # 10. Publishability (0 - 10)
        # Composite readiness without fatal blockers
        avg_other = sum(dim[k] for k in dim if k != "publishability") / len(dim)
        if blockers:
            dim["publishability"] = 5.0
        else:
            dim["publishability"] = round(avg_other, 1)

        # Calculate Overall Score (0 - 100)
        total_score = sum(dim.values())
        overall_score = int(round(total_score))

        # Status classification
        if blockers:
            status = "REJECT_AND_RESEARCH_AGAIN" if overall_score < 70 else "NEEDS_REVIEW"
        elif overall_score >= 90:
            status = "PUBLISH_READY"
        elif overall_score >= 80:
            status = "MINOR_EDIT"
        elif overall_score >= 70:
            status = "NEEDS_REVIEW"
        else:
            status = "REJECT_AND_RESEARCH_AGAIN"

        return ContentQualityReport(
            overall_score=overall_score,
            status=status,
            dimension_scores=dim,
            blockers=blockers,
            warnings=warnings,
            topic=topic
        )
