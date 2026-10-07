"""
engine/production/final_qa.py
=============================
Rigorous Multi-Gate Artifact QA Engine for Nugi Content Production.
Location: engine/production/final_qa.py

Strictly separates HARD GATES (binary blockers for publishability)
from SOFT SCORES (continuous dimensional quality indicators).
Validates REAL disk artifacts, never mocks or hardcoded PASS.

Verdicts:
  - PUBLISH_READY: All hard gates passed, quality score >= 80, 0 blockers.
  - MINOR_EDIT: All hard gates passed, quality score 70-79, minor warnings.
  - NEEDS_REVIEW: Hard gate advisory warning or quality score 60-69.
  - BLOCKED: One or more hard gates failed (disputed claims, missing assets, broken draft).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.pipeline.capcut_validator import CapCutValidator

logger = logging.getLogger("final_qa")


class QAVerdict(str, Enum):
    PUBLISH_READY = "PUBLISH_READY"
    MINOR_EDIT = "MINOR_EDIT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass
class FinalQAReport:
    """Consolidated QA report detailing hard blockers and soft dimensional scores."""
    verdict: str  # QAVerdict
    is_publishable: bool
    overall_quality_score: float
    hard_blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts_checked: Dict[str, bool] = field(default_factory=dict)
    dimensional_scores: Dict[str, float] = field(default_factory=dict)
    media_coverage_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "is_publishable": self.is_publishable,
            "overall_quality_score": round(self.overall_quality_score, 1),
            "media_coverage_pct": round(self.media_coverage_pct, 1),
            "hard_blockers": self.hard_blockers,
            "warnings": self.warnings,
            "artifacts_checked": self.artifacts_checked,
            "dimensional_scores": self.dimensional_scores,
        }

    def save(self, workspace_dir: Path | str) -> Path:
        ws = Path(workspace_dir).resolve()
        out_p = ws / "final_qa.json"
        out_p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return out_p


class FinalQAEngine:
    """Inspects filesystem artifacts to deliver an honest production verdict."""

    def __init__(self):
        self.capcut_validator = CapCutValidator()

    def evaluate_production(self, workspace_dir: Path | str) -> FinalQAReport:
        ws = Path(workspace_dir).resolve()
        hard_blockers: List[str] = []
        warnings: List[str] = []
        artifacts_checked: Dict[str, bool] = {}
        scores: Dict[str, float] = {}

        # 1. Production Plan artifact check
        plan_p = ws / "production_plan.json"
        artifacts_checked["production_plan"] = plan_p.is_file()
        target_dur = 75.0
        if not plan_p.is_file():
            hard_blockers.append("Missing production_plan.json")
        else:
            try:
                p_data = json.loads(plan_p.read_text(encoding="utf-8"))
                target_dur = float(p_data.get("duration_seconds", 75.0))
            except Exception as e:
                hard_blockers.append(f"Corrupt production_plan.json: {e}")

        # 2. Research Dossier check
        dossier_p = ws / "research_dossier.json"
        artifacts_checked["research_dossier"] = dossier_p.is_file()
        dossier_data: Dict[str, Any] = {}
        if not dossier_p.is_file():
            hard_blockers.append("Missing research_dossier.json")
            scores["evidence_depth"] = 0.0
        else:
            try:
                dossier_data = json.loads(dossier_p.read_text(encoding="utf-8"))
                ev_count = len(dossier_data.get("sources", [])) + len(dossier_data.get("data_points", []))
                if ev_count < 2:
                    warnings.append(f"Low empirical evidence count ({ev_count} items)")
                    scores["evidence_depth"] = 60.0
                else:
                    scores["evidence_depth"] = min(100.0, 70.0 + ev_count * 5.0)

                # Check for fabricated quotes
                for src in dossier_data.get("sources", []):
                    quote = src.get("exact_quote", "")
                    title = src.get("title", "")
                    if quote and quote == title and len(quote) > 10:
                        hard_blockers.append(f"Fabricated quote detected: title was used as exact quote for '{title[:30]}'")
            except Exception as e:
                hard_blockers.append(f"Corrupt research_dossier.json: {e}")

        # 3. Fact-Check Report check
        fact_p = ws / "fact_check_report.json"
        artifacts_checked["fact_check_report"] = fact_p.is_file()
        if not fact_p.is_file():
            hard_blockers.append("Missing fact_check_report.json")
            scores["fact_integrity"] = 0.0
        else:
            try:
                fact_data = json.loads(fact_p.read_text(encoding="utf-8"))
                disputed = [c for c in fact_data.get("claims", []) if c.get("status") == "DISPUTED"]
                if disputed:
                    hard_blockers.append(f"Script contains {len(disputed)} DISPUTED factual claims: {[c.get('claim', '')[:30] for c in disputed[:2]]}")
                    scores["fact_integrity"] = 40.0
                elif not fact_data.get("pass_gate", True):
                    hard_blockers.append("Fact check report failed gate")
                    scores["fact_integrity"] = 50.0
                else:
                    scores["fact_integrity"] = 95.0
            except Exception as e:
                hard_blockers.append(f"Corrupt fact_check_report.json: {e}")

        # 4. Script duration & format check
        script_p = ws / "script.md"
        artifacts_checked["script"] = script_p.is_file()
        if not script_p.is_file():
            hard_blockers.append("Missing script.md")
            scores["script_pacing"] = 0.0
        else:
            try:
                script_txt = script_p.read_text(encoding="utf-8")
                words = len(script_txt.split())
                expected_wpm = 150  # spoken Indonesian words per minute ~2.5 words/sec
                expected_words = int(round(target_dur * 2.3))
                tolerance = max(25, int(round(expected_words * 0.25)))

                if abs(words - expected_words) > tolerance:
                    warnings.append(f"Script word count ({words} words) deviates from target for {target_dur}s (~{expected_words} words)")
                    scores["script_pacing"] = 70.0
                else:
                    scores["script_pacing"] = 92.0
            except Exception as e:
                hard_blockers.append(f"Error reading script.md: {e}")

        # 5. Visual Plan & B-roll Coverage check
        broll_plan_p = ws / "broll_plan.json"
        artifacts_checked["broll_plan"] = broll_plan_p.is_file()
        coverage_pct = 0.0
        if not broll_plan_p.is_file():
            hard_blockers.append("Missing broll_plan.json")
            scores["visual_coverage"] = 0.0
        else:
            try:
                broll_plan = json.loads(broll_plan_p.read_text(encoding="utf-8"))
                total_shots = len(broll_plan)
                footage_dir = ws / "footage"
                existing_media = list(footage_dir.glob("*")) if footage_dir.is_dir() else []
                media_files = [f for f in existing_media if f.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}]

                if total_shots > 0:
                    coverage_pct = min(100.0, (len(media_files) / total_shots) * 100.0)
                else:
                    coverage_pct = 100.0 if media_files else 50.0

                if coverage_pct < 40.0 and len(media_files) == 0:
                    warnings.append(f"Low B-roll footage coverage ({len(media_files)} downloaded for {total_shots} planned shots)")
                    scores["visual_coverage"] = 60.0
                else:
                    scores["visual_coverage"] = min(100.0, 70.0 + coverage_pct * 0.3)
            except Exception as e:
                hard_blockers.append(f"Error parsing broll_plan.json: {e}")

        # 6. Subtitles check
        srt_p = ws / "subtitles.srt"
        artifacts_checked["subtitles"] = srt_p.is_file()
        if not srt_p.is_file():
            hard_blockers.append("Missing subtitles.srt")
            scores["subtitle_accuracy"] = 0.0
        else:
            try:
                srt_txt = srt_p.read_text(encoding="utf-8").strip()
                if not srt_txt:
                    hard_blockers.append("subtitles.srt is empty")
                    scores["subtitle_accuracy"] = 0.0
                elif "-->" not in srt_txt:
                    hard_blockers.append("subtitles.srt lacks valid timecode arrows ('-->')")
                    scores["subtitle_accuracy"] = 30.0
                else:
                    scores["subtitle_accuracy"] = 95.0
            except Exception as e:
                hard_blockers.append(f"Error reading subtitles.srt: {e}")

        # 7. Native CapCut Draft project check
        capcut_dir = ws / "capcut"
        artifacts_checked["capcut_draft"] = capcut_dir.is_dir()
        if not capcut_dir.is_dir():
            hard_blockers.append("Missing capcut draft directory")
            scores["capcut_integrity"] = 0.0
        else:
            val_rep = self.capcut_validator.validate_draft(capcut_dir)
            if not val_rep.is_valid:
                hard_blockers.extend([f"CapCut validation: {err}" for err in val_rep.errors])
                scores["capcut_integrity"] = 40.0
            else:
                scores["capcut_integrity"] = 100.0

        # 8. Manifest check
        manifest_p = ws / "manifest.json"
        artifacts_checked["manifest"] = manifest_p.is_file()
        if not manifest_p.is_file():
            warnings.append("manifest.json missing at time of QA")

        # Soft score calculation
        score_values = list(scores.values())
        overall_score = sum(score_values) / len(score_values) if score_values else 50.0

        # Verdict calculation
        if hard_blockers:
            verdict = QAVerdict.BLOCKED.value
            is_publishable = False
        elif overall_score >= 80.0 and len(warnings) == 0:
            verdict = QAVerdict.PUBLISH_READY.value
            is_publishable = True
        elif overall_score >= 70.0:
            verdict = QAVerdict.MINOR_EDIT.value
            is_publishable = True
        else:
            verdict = QAVerdict.NEEDS_REVIEW.value
            is_publishable = False

        return FinalQAReport(
            verdict=verdict,
            is_publishable=is_publishable,
            overall_quality_score=overall_score,
            hard_blockers=hard_blockers,
            warnings=warnings,
            artifacts_checked=artifacts_checked,
            dimensional_scores=scores,
            media_coverage_pct=coverage_pct,
        )
