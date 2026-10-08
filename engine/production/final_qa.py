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
import re
from math import isfinite
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

        # The manifest is the production state source of truth, so it is a hard
        # requirement before any output can be called publishable.
        manifest_p = ws / "manifest.json"
        artifacts_checked["manifest"] = manifest_p.is_file()
        manifest_data: Dict[str, Any] = {}
        if not manifest_p.is_file():
            hard_blockers.append("Missing manifest.json")
        else:
            try:
                manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
                if not isinstance(manifest_data, dict) or not manifest_data.get("run_id"):
                    hard_blockers.append("manifest.json is missing a valid run_id")
                    manifest_data = {}
                elif not manifest_data.get("topic"):
                    hard_blockers.append("manifest.json is missing the production topic")
                completed = set(manifest_data.get("completed_stages", []))
                required_stages = {
                    "plan", "qualify", "research", "script", "fact_check",
                    "visual_plan", "media", "subtitle", "capcut",
                }
                missing_stages = sorted(required_stages - completed)
                if missing_stages:
                    hard_blockers.append(
                        "ProductionManifest does not mark required stages complete: "
                        + ", ".join(missing_stages)
                    )
            except Exception as exc:
                hard_blockers.append(f"Corrupt manifest.json: {exc}")

        # 1. Production Plan artifact check, including its explicit narration
        # pacing contract.
        plan_p = ws / "production_plan.json"
        artifacts_checked["production_plan"] = plan_p.is_file()
        target_dur = 0.0
        spoken_wpm = 0.0
        if not plan_p.is_file():
            hard_blockers.append("Missing production_plan.json")
        else:
            try:
                p_data = json.loads(plan_p.read_text(encoding="utf-8"))
                target_dur = float(p_data.get("duration_seconds", 0))
                spoken_wpm = float(p_data.get("spoken_words_per_minute", 0))
                target_words = int(p_data.get("target_spoken_words", 0))
                if not isfinite(target_dur) or target_dur <= 0:
                    hard_blockers.append("production_plan.json has no valid positive duration_seconds")
                if not isfinite(spoken_wpm) or spoken_wpm <= 0:
                    hard_blockers.append("production_plan.json has no valid positive spoken_words_per_minute")
                expected_target_words = int(round(target_dur * spoken_wpm / 60)) if target_dur > 0 and spoken_wpm > 0 else 0
                if target_words != expected_target_words:
                    hard_blockers.append("production_plan.json target_spoken_words does not match its duration and pacing")
                if manifest_data.get("topic") and p_data.get("topic") != manifest_data.get("topic"):
                    hard_blockers.append("production_plan.json topic does not match manifest.json")
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
                if manifest_data.get("topic") and dossier_data.get("topic") != manifest_data.get("topic"):
                    hard_blockers.append("research_dossier.json topic does not match manifest.json")
                dossier_verdict = str(dossier_data.get("epistemic_status", "UNVERIFIED")).upper()
                if dossier_verdict != "VERIFIED":
                    hard_blockers.append(f"Research dossier is {dossier_verdict}; publishability requires VERIFIED evidence.")
                dossier_claims = dossier_data.get("claims", [])
                if not dossier_claims:
                    hard_blockers.append("Research dossier contains no evidence-mapped claims")
                elif any(str(claim.get("status", "UNVERIFIED")).upper() != "VERIFIED" for claim in dossier_claims):
                    hard_blockers.append("Research dossier contains claims that are not independently VERIFIED")
                evidence_items = dossier_data.get("evidence_items", dossier_data.get("sources", []))
                usable_evidence = [
                    item for item in evidence_items
                    if item.get("is_supporting", True) and (item.get("exact_quote") or item.get("retrieved_snippet"))
                ]
                ev_count = len(usable_evidence) + len(dossier_data.get("data_points", []))
                if ev_count < 2:
                    warnings.append(f"Low empirical evidence count ({ev_count} items)")
                    scores["evidence_depth"] = 60.0
                else:
                    scores["evidence_depth"] = min(100.0, 70.0 + ev_count * 5.0)

                # Check for fabricated quotes
                for item in evidence_items:
                    quote = item.get("exact_quote", "")
                    source = item.get("source", item)
                    title = source.get("title", "")
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
                if fact_data.get("production_run_id") != manifest_data.get("run_id"):
                    hard_blockers.append("fact_check_report.json does not belong to the current ProductionManifest run")
                if fact_data.get("topic") != manifest_data.get("topic"):
                    hard_blockers.append("fact_check_report.json topic does not match manifest.json")
                disputed = [
                    c for c in fact_data.get("claims", [])
                    if c.get("status", c.get("verdict")) == "DISPUTED"
                ]
                verdict = str(fact_data.get("overall_verdict", "UNKNOWN")).upper()
                fact_status = {
                    "VERIFIED": "PASS",
                    "DISPUTED": "FAIL",
                    "PROBABLE": "NEEDS_REVIEW",
                    "UNVERIFIED": "NEEDS_REVIEW",
                }.get(verdict, "UNKNOWN")
                if disputed:
                    hard_blockers.append(f"Script contains {len(disputed)} DISPUTED factual claims: {[c.get('claim', '')[:30] for c in disputed[:2]]}")
                    scores["fact_integrity"] = 40.0
                elif fact_status == "PASS" and fact_data.get("pass_gate") is True:
                    scores["fact_integrity"] = 95.0
                elif fact_status == "NEEDS_REVIEW":
                    hard_blockers.append("Fact check requires review; it is not a PASS result")
                    scores["fact_integrity"] = 60.0
                else:
                    hard_blockers.append(f"Fact check report is {fact_status}")
                    scores["fact_integrity"] = 0.0
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
                words = self._spoken_word_count(script_txt)
                expected_words = int(round(target_dur * spoken_wpm / 60.0))
                tolerance = max(25, int(round(expected_words * 0.25)))

                if abs(words - expected_words) > tolerance:
                    warnings.append(f"Script word count ({words} words) deviates from target for {target_dur}s (~{expected_words} words)")
                    scores["script_pacing"] = 70.0
                else:
                    scores["script_pacing"] = 92.0
            except Exception as e:
                hard_blockers.append(f"Error reading script.md: {e}")

        # 5. Visual Plan & shot-to-media coverage check.  Files in footage/ do
        # not establish coverage: each required shot needs a real/reused asset.
        broll_plan_p = ws / "broll_plan.json"
        artifacts_checked["broll_plan"] = broll_plan_p.is_file()
        media_manifest_p = ws / "media_manifest.json"
        artifacts_checked["media_manifest"] = media_manifest_p.is_file()
        coverage_pct = 0.0
        if not broll_plan_p.is_file():
            hard_blockers.append("Missing broll_plan.json")
            scores["visual_coverage"] = 0.0
        elif not media_manifest_p.is_file():
            hard_blockers.append("Missing media_manifest.json")
            scores["visual_coverage"] = 0.0
        else:
            try:
                broll_plan = json.loads(broll_plan_p.read_text(encoding="utf-8"))
                media_data = json.loads(media_manifest_p.read_text(encoding="utf-8"))
                if not isinstance(broll_plan, list) or not isinstance(media_data.get("shots"), list):
                    raise ValueError("broll_plan.json and media_manifest.json shots must be lists")
                media_entries = media_data["shots"]
                shot_statuses = {entry.get("shot_id"): entry for entry in media_entries if entry.get("shot_id")}
                assets_by_shot = {
                    asset.get("shot_id"): asset
                    for asset in media_data.get("assets", [])
                    if isinstance(asset, dict) and asset.get("shot_id")
                }
                planned_ids = {shot.get("shot_id") for shot in broll_plan if shot.get("shot_id")}
                if len(shot_statuses) != len(media_entries) or set(shot_statuses) != planned_ids:
                    hard_blockers.append("media_manifest.json shot mapping does not exactly match broll_plan.json")
                if media_data.get("production_run_id") != manifest_data.get("run_id"):
                    hard_blockers.append("media_manifest.json does not belong to the current ProductionManifest run")
                if media_data.get("topic") != manifest_data.get("topic"):
                    hard_blockers.append("media_manifest.json topic does not match manifest.json")
                expected_mode = manifest_data.get("run_mode")
                if expected_mode not in {"DRY_RUN", "REAL_RUN"} or media_data.get("run_mode") != expected_mode:
                    hard_blockers.append("media_manifest.json run mode does not match manifest.json")
                non_required = {"NO_BROLL", "NO_VISUAL", "REMOTION_REQUIRED"}
                required = [
                    shot for shot in broll_plan
                    if shot.get("search_required", True) and shot.get("visual_requirement") not in non_required
                ]
                valid_statuses = {"REAL_DOWNLOADED", "LOCAL_REUSED"}
                covered = []
                for shot in required:
                    shot_entry = shot_statuses.get(shot.get("shot_id"), {})
                    local_path = Path(shot_entry.get("local_path", ""))
                    asset = assets_by_shot.get(shot.get("shot_id"), {})
                    if (
                        shot_entry.get("required") is True
                        and shot_entry.get("status") in valid_statuses
                        and local_path.is_file()
                        and local_path.stat().st_size > 0
                        and self.media_asset_matches_topic(
                            shot,
                            {**asset, **shot_entry},
                            str(manifest_data.get("topic", "")),
                        )
                    ):
                        covered.append(shot)
                missing = [shot for shot in required if shot not in covered]
                coverage_pct = 100.0 if not required else (len(covered) / len(required)) * 100.0
                placeholder_count = sum(1 for shot in required if shot_statuses.get(shot.get("shot_id"), {}).get("status") == "PLACEHOLDER")
                if placeholder_count:
                    warnings.append(f"{placeholder_count} required shot(s) use PLACEHOLDER and do not count as B-roll coverage")
                if missing:
                    missing_ids = [str(shot.get("shot_id", "unknown")) for shot in missing]
                    hard_blockers.append(f"Missing real B-roll for required shot(s): {', '.join(missing_ids[:5])}")
                scores["visual_coverage"] = coverage_pct
            except Exception as e:
                hard_blockers.append(f"Error parsing B-roll/media manifests: {e}")

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
        capcut_validation_p = ws / "capcut_validation.json"
        artifacts_checked["capcut_structural_validation"] = capcut_validation_p.is_file()
        if not capcut_dir.is_dir():
            hard_blockers.append("Missing capcut draft directory")
            scores["capcut_integrity"] = 0.0
        else:
            val_rep = self.capcut_validator.validate_draft(capcut_dir)
            if not capcut_validation_p.is_file():
                hard_blockers.append("Missing capcut_validation.json")
            else:
                try:
                    saved_validation = json.loads(capcut_validation_p.read_text(encoding="utf-8"))
                    if not saved_validation.get("is_valid") or saved_validation.get("status") not in {"VALIDATED", "APP_VERIFIED"}:
                        hard_blockers.append("Saved CapCut structural validation did not pass")
                    elif saved_validation.get("project_path") != val_rep.project_path:
                        hard_blockers.append("Saved CapCut validation does not match the current draft path")
                    recorded_validation = manifest_data.get("artifacts", {}).get("capcut_validation")
                    if not recorded_validation or Path(recorded_validation).resolve() != capcut_validation_p.resolve():
                        hard_blockers.append("ProductionManifest CapCut validation path does not match this workspace")
                except Exception as exc:
                    hard_blockers.append(f"Corrupt capcut_validation.json: {exc}")
            if not val_rep.is_valid:
                hard_blockers.extend([f"CapCut validation: {err}" for err in val_rep.errors])
                scores["capcut_integrity"] = 40.0
            elif val_rep.status not in ("VALIDATED", "APP_VERIFIED"):
                hard_blockers.append(f"CapCut structural validation is not complete (status: {val_rep.status})")
                scores["capcut_integrity"] = 0.0
            else:
                scores["capcut_integrity"] = 100.0

        # Final QA consumes the separate editorial score; it does not recreate
        # the same quality model from production-gate inputs.
        content_quality = manifest_data.get("content_quality", {})
        if isinstance(content_quality, dict) and isinstance(content_quality.get("overall_score"), (int, float)):
            scores["editorial_quality"] = float(content_quality["overall_score"])

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

    @staticmethod
    def _spoken_word_count(script_text: str) -> int:
        """Count narration only, excluding common production metadata and labels."""
        narration: List[str] = []
        ignored_prefixes = ("#", "---", "shot", "scene", "catatan", "note", "metadata", "durasi", "title:", "judul:")
        lines = script_text.splitlines()
        narration_fence_types = {"text", "txt", "narration", "spoken"}
        has_narration_fence = any(
            line.strip().startswith("```")
            and line.strip()[3:].strip().lower() in narration_fence_types
            for line in lines
        )
        in_fence = False
        count_fence = False
        for raw_line in lines:
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                if not in_fence:
                    in_fence = True
                    count_fence = stripped[3:].strip().lower() in narration_fence_types
                else:
                    in_fence = False
                    count_fence = False
                continue
            if in_fence:
                if not count_fence:
                    continue
            elif has_narration_fence:
                continue
            line = stripped
            if not line or line.lower().startswith(ignored_prefixes):
                continue
            if line.startswith("[") and (line.endswith("]") or re.match(r"^\[[^]]+\]\s+[A-Z][A-Z &/\-]*$", line)):
                continue
            narration.append(line)
        return len(" ".join(narration).split())

    @staticmethod
    def media_asset_matches_topic(shot: Dict[str, Any], asset: Dict[str, Any], topic: str) -> bool:
        """Require topic-specific evidence before counting a downloaded asset as shot coverage."""
        status = str(asset.get("media_status", asset.get("status", ""))).upper()
        if asset.get("rejection_reason") or asset.get("is_generic"):
            return False
        if status == "REAL_DOWNLOADED" and not str(asset.get("source_url", "")).startswith(("http://", "https://")):
            return False

        words = set(re.findall(r"[a-z0-9]+", topic.lower()))
        generic = {
            "about", "and", "atau", "bagaimana", "banyak", "dampak", "data", "dalam", "dan",
            "dari", "dengan", "di", "documentary", "document", "footage", "foto", "gambar",
            "how", "ini", "ke", "kenapa", "mengapa", "people", "photo", "place", "real",
            "scene", "shot", "tentang", "the", "untuk", "video", "waktu", "yang",
        }
        words = {word for word in words if len(word) >= 3 and word not in generic}
        expansions = {
            "transportasi": {"transport", "transit", "train", "bus", "rail", "mrt", "lrt", "transjakarta"},
            "transport": {"transportasi", "transit", "train", "bus", "rail", "mrt", "lrt", "transjakarta"},
            "publik": {"public"}, "public": {"publik"},
            "komuter": {"commuter", "commuting"}, "commuter": {"komuter", "commuting"},
            "rumah": {"housing", "home"}, "housing": {"rumah", "home"},
            "kecerdasan": {"artificial", "intelligence", "ai"},
            "buatan": {"artificial", "intelligence", "ai"},
            "kerja": {"work", "worker", "labor", "employment"},
            "pekerja": {"worker", "labor", "employment"},
            "tanah": {"land", "property"}, "harga": {"price", "cost"},
        }
        topic_terms = set(words)
        for word in list(words):
            topic_terms.update(expansions.get(word, set()))
        candidate_text = " ".join([
            str(asset.get("title", "")),
            " ".join(str(item) for item in asset.get("matched_entities", []) if item),
        ]).lower()
        candidate_terms = set(re.findall(r"[a-z0-9]+", candidate_text))
        matches = topic_terms & candidate_terms
        minimum_matches = 1 if len(words) <= 2 else 2
        return bool(words) and len(matches) >= minimum_matches
