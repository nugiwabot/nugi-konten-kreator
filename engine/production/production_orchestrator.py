"""
engine/production/production_orchestrator.py
============================================
Master Autonomous Content Production Orchestrator for Nugi Konten Kreator.
Location: engine/production/production_orchestrator.py

Single canonical orchestrator replacing all fragmented workflow runners.
Executes the unified 12-stage production pipeline:
  PLAN -> QUALIFY -> RESEARCH -> STORY/SCRIPT -> FACT_CHECK ->
  VISUAL_PLAN -> MEDIA -> SUBTITLE -> CAPCUT -> FINAL_QA -> COMPLETE

Runtime contract:
  - Resumes only manifest-linked artifacts that pass stage-specific checks.
  - External research and media results are not deterministic; provenance and
    current status are recorded rather than assumed.
  - Missing or irrelevant real media remains MISSING and blocks Final QA.
  - CapCut output is structurally validated; Desktop use is not inferred.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from engine.editorial.content_scorer import ContentQualityEvaluator
from engine.editorial.quality_gate import check_quality_gates
from engine.editorial.script_auditor import audit_script_with_dossier
from engine.editorial.script_synthesizer import DynamicScriptSynthesizer
from engine.editorial.story_type import classify_story_type
from engine.editorial.story_planner import build_story_plan
from engine.pipeline.capcut_engine import CapCutDraftGenerator
from engine.pipeline.capcut_validator import CapCutValidator
import engine.pipeline.media_finder as media_finder_mod
from engine.pipeline.research_dossier import DossierGenerator, ResearchDossier
from engine.pipeline.script_parser import NarasiScript, ScriptParser
from engine.pipeline.srt_generator import SRTGenerator
from engine.pipeline.timeline_model import SubtitleCue, TimelineClip, TimelineData
from engine.pipeline.visual_requirements import VisualRequirementsGenerator, VisualShotRequirement
from engine.production.executive_producer import ExecutiveProducer, ProductionPlan
from engine.production.final_qa import FinalQAEngine, FinalQAReport, QAVerdict
from engine.production.production_manifest import ProductionManifest, ProductionStage

logger = logging.getLogger("production_orchestrator")


@dataclass
class ProductionRunResult:
    """Outcome of an autonomous content production run."""
    status: str  # "PUBLISH_READY", "MINOR_EDIT", "NEEDS_REVIEW", "BLOCKED", "REJECTED_BY_EDITORIAL_GATE"
    topic: str
    workspace_folder: str
    run_id: str
    plan: Dict[str, Any]
    artifacts: Dict[str, str]
    quality_score: float
    qa_report: Dict[str, Any]
    manifest: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        out_status = "ok" if self.status in ("PUBLISH_READY", "MINOR_EDIT", "STAGE_LIMITED", "ok") else self.status
        content_q = self.manifest.get("content_quality", {})
        cq_score = content_q.get("overall_score", round(self.quality_score, 1))
        dim_scores = content_q.get("dimension_scores", self.qa_report.get("dimensional_scores", {}))
        fact_check_status = self.manifest.get("fact_check_status", "UNKNOWN")

        return {
            "status": out_status,
            "production_status": self.status,
            "topic": self.topic,
            "workspace_folder": self.workspace_folder,
            "run_id": self.run_id,
            "plan": self.plan,
            "artifacts": self.artifacts,
            "quality_score": round(self.quality_score, 1),
            "content_quality_score": cq_score,
            "content_quality_status": content_q.get("status", self.status),
            "dimension_scores": dim_scores,
            "qa_report": self.qa_report,
            "manifest": self.manifest,
            "stage": self.manifest.get("current_stage", "complete"),
            "total_shots_planned": self.manifest.get("shots_planned", len(self.manifest.get("shots", []))),
            "total_assets_ready": self.manifest.get("real_assets_ready", 0),
            "script_file": self.artifacts.get("script_md", ""),
            "fact_check_verdict": self.manifest.get("fact_check_verdict", "UNKNOWN"),
            "fact_check_status": fact_check_status,
            "fact_check_pass": fact_check_status == "PASS",
        }


class ProductionOrchestrator:
    """Master production engine coordinating research, editorial, media, and CapCut."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        media_finder: Optional[Any] = None,
    ):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.qa_engine = FinalQAEngine()
        self.capcut_gen = CapCutDraftGenerator()
        self.capcut_val = CapCutValidator()
        self.script_parser = ScriptParser()
        self.visual_gen = VisualRequirementsGenerator()
        self.srt_gen = SRTGenerator()
        self.media_finder = media_finder

    def run(
        self,
        topic_or_prompt: str,
        output_folder: Optional[str] = None,
        format_hint: str = "short",
        duration_hint: Optional[float] = None,
        depth: str = "deep",
        dry_run: bool = False,
        stage_limit: Optional[str] = None,
        max_broll_shots: Optional[int] = None,
        install_to_capcut: bool = False,
        recency: Optional[str] = None,
        request_plan: Optional[Dict[str, Any]] = None,
    ) -> ProductionRunResult:
        """
        Executes end-to-end production autonomously.
        """
        # 1. Establish workspace
        clean_topic_slug = re.sub(r"[^a-zA-Z0-9_]", "_", topic_or_prompt.lower()[:35]).strip("_")
        folder_name = output_folder or f"prod_{clean_topic_slug}"
        work_dir = (self.repo_root / "output" / folder_name).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

        # 2. State manifest
        manifest_path = work_dir / "manifest.json"
        if manifest_path.is_file():
            manifest = ProductionManifest.load(manifest_path)
            logger.info(f"Loaded existing production state manifest from {manifest_path} (Run ID: {manifest.run_id})")
            original_topic = manifest.extra_fields.get("input_topic", manifest.topic)
            if original_topic != topic_or_prompt:
                raise ValueError(
                    "Output folder already belongs to a different production topic. "
                    "Choose a new output_folder rather than reusing stale artifacts."
                )
            requested_contract = {
                "format": format_hint,
                "duration_hint": duration_hint,
                "depth": depth,
                "recency": recency,
                "max_broll_shots": max_broll_shots,
            }
            previous_contract = manifest.extra_fields.get("input_contract")
            if previous_contract != requested_contract:
                if previous_contract is None or any(
                    previous_contract.get(key) != requested_contract.get(key)
                    for key in ("format", "duration_hint", "max_broll_shots")
                ):
                    manifest.invalidate_from(ProductionStage.PLAN)
                else:
                    manifest.invalidate_from(ProductionStage.RESEARCH)
        else:
            manifest = ProductionManifest(topic=topic_or_prompt, format=format_hint)
        manifest.extra_fields["input_topic"] = topic_or_prompt
        manifest.extra_fields["input_contract"] = {
            "format": format_hint,
            "duration_hint": duration_hint,
            "depth": depth,
            "recency": recency,
            "max_broll_shots": max_broll_shots,
        }
        manifest.extra_fields["run_mode"] = "DRY_RUN" if dry_run else "REAL_RUN"
        manifest.extra_fields["research_recency"] = recency
        if request_plan is not None:
            manifest.extra_fields["request_plan"] = request_plan

        # ----------------------------------------------------------------------
        # STAGE 1: PLAN (Executive Producer Contract)
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.PLAN.value
        plan_file = work_dir / "production_plan.json"
        if self._stage_artifact_valid(
            manifest,
            ProductionStage.PLAN,
            "production_plan",
            plan_file,
            lambda: ProductionPlan.load(plan_file).topic == manifest.topic,
        ):
            plan = ProductionPlan.load(plan_file)
            logger.info("Resuming: Existing production plan reused.")
        else:
            manifest.invalidate_from(ProductionStage.PLAN)
            plan = ExecutiveProducer.parse_user_request(
                topic_or_prompt=topic_or_prompt,
                format_hint=format_hint,
                duration_hint=duration_hint,
                depth_hint=depth,
                workspace_dir=work_dir,
            )
            if max_broll_shots is not None:
                plan.max_broll_shots = max_broll_shots
            plan.save(work_dir)
            manifest.mark_stage_completed(ProductionStage.PLAN, {"production_plan": str(plan_file)})
            manifest.save(work_dir)

        manifest.topic = plan.topic
        manifest.target_duration_seconds = plan.duration_seconds

        # ----------------------------------------------------------------------
        # STAGE 2: QUALIFY (Editorial Quality Gate)
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.QUALIFY.value
        gate_check = check_quality_gates({"title": plan.topic, "human_question": plan.topic})
        if not gate_check.get("passed", True) and gate_check.get("hard_rejection", False):
            manifest.mark_failed(ProductionStage.QUALIFY, "Rejected by editorial quality gate")
            manifest.save(work_dir)
            return ProductionRunResult(
                status="REJECTED_BY_EDITORIAL_GATE",
                topic=plan.topic,
                workspace_folder=f"output/{folder_name}",
                run_id=manifest.run_id,
                plan=plan.to_dict(),
                artifacts={"manifest": str(manifest_path)},
                quality_score=gate_check.get("fit_score", 0),
                qa_report={"violations": gate_check.get("violations", [])},
                manifest=manifest.to_dict(),
            )
        manifest.mark_stage_completed(ProductionStage.QUALIFY)
        manifest.save(work_dir)

        # ----------------------------------------------------------------------
        # STAGE 3: RESEARCH & EVIDENCE DOSSIER
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.RESEARCH.value
        dossier_json_p = work_dir / "research_dossier.json"
        dossier_md_p = work_dir / "research_dossier.md"

        if self._stage_artifact_valid(
            manifest,
            ProductionStage.RESEARCH,
            "dossier_json",
            dossier_json_p,
            lambda: json.loads(dossier_json_p.read_text(encoding="utf-8")).get("topic") == plan.topic
            and isinstance(json.loads(dossier_json_p.read_text(encoding="utf-8")).get("evidence_items", []), list),
        ) and dossier_md_p.is_file():
            logger.info("Resuming: Existing research dossier reused.")
            d_dict = json.loads(dossier_json_p.read_text(encoding="utf-8"))
            dossier = ResearchDossier.from_dict(d_dict)
        else:
            manifest.invalidate_from(ProductionStage.RESEARCH)
            dossier_gen = DossierGenerator()
            dossier = dossier_gen.build_dossier(plan.topic, depth=plan.research_depth, recency=recency)
            dossier_files = dossier_gen.save_dossier_to_workspace(dossier, work_dir)
            manifest.mark_stage_completed(
                ProductionStage.RESEARCH,
                {"dossier_json": str(dossier_json_p), "dossier_md": str(dossier_md_p)}
            )
            manifest.save(work_dir)

        if stage_limit == "research":
            manifest.save(work_dir)
            return self._build_result(manifest, plan, work_dir, folder_name)

        research_intelligence = getattr(dossier, "research_intelligence", {}) or {}

        # ----------------------------------------------------------------------
        # STAGE 4: STORY & SCRIPT SYNTHESIS
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.SCRIPT.value
        script_p = work_dir / "script.md"
        story_plan_p = work_dir / "story_plan.json"

        if self._stage_artifact_valid(
            manifest,
            ProductionStage.SCRIPT,
            "script_md",
            script_p,
            lambda: script_p.read_text(encoding="utf-8").strip() != ""
            and json.loads(story_plan_p.read_text(encoding="utf-8")).get("topic") == plan.topic
            and float(json.loads(story_plan_p.read_text(encoding="utf-8")).get("duration_seconds", -1)) == float(plan.duration_seconds)
            and json.loads(story_plan_p.read_text(encoding="utf-8")).get("schema_version") == 1
            and isinstance(json.loads(story_plan_p.read_text(encoding="utf-8")).get("beats"), list)
            and bool(json.loads(story_plan_p.read_text(encoding="utf-8")).get("beats")),
        ) and story_plan_p.is_file():
            logger.info("Resuming: Existing script reused.")
            script_content = script_p.read_text(encoding="utf-8")
        else:
            manifest.invalidate_from(ProductionStage.SCRIPT)
            # Derive story archetype & narrative devices
            st_info = classify_story_type(plan.topic)
            story_archetype = st_info.get("primary_type", "historical_investigative")

            story_plan = build_story_plan(
                dossier=dossier,
                story_type_info=st_info,
                duration_seconds=plan.duration_seconds,
            )
            # Keep legacy fields for downstream consumers and historical workspaces.
            story_plan.update({
                "story_archetype": story_archetype,
                "narrative_angles": getattr(dossier, "narrative_angles", []),
                "causal_relationships": getattr(dossier, "causal_relationships", []),
                "timeline": getattr(dossier, "timeline", []),
            })
            story_plan_p.write_text(json.dumps(story_plan, indent=2, ensure_ascii=False), encoding="utf-8")

            # The script is rendered from the same outline, with evidence status
            # and uncertainty carried through to the narration draft.
            synthesizer = DynamicScriptSynthesizer()
            script_content = synthesizer.synthesize_script(
                dossier,
                target_duration_seconds=int(plan.duration_seconds),
                story_plan=story_plan,
            )
            script_p.write_text(script_content, encoding="utf-8")

            manifest.mark_stage_completed(
                ProductionStage.SCRIPT,
                {"script_md": str(script_p), "story_plan": str(story_plan_p)}
            )
            manifest.save(work_dir)

        # ----------------------------------------------------------------------
        # STAGE 5: FACT-CHECK AUDIT
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.FACT_CHECK.value
        fact_check_p = work_dir / "fact_check_report.json"

        if self._stage_artifact_valid(
            manifest,
            ProductionStage.FACT_CHECK,
            "fact_check_report",
            fact_check_p,
            lambda: (
                json.loads(fact_check_p.read_text(encoding="utf-8")).get("production_run_id") == manifest.run_id
                and json.loads(fact_check_p.read_text(encoding="utf-8")).get("topic") == plan.topic
                and json.loads(fact_check_p.read_text(encoding="utf-8")).get("overall_verdict") in ("VERIFIED", "PROBABLE", "DISPUTED", "UNVERIFIED", "UNKNOWN")
                and json.loads(fact_check_p.read_text(encoding="utf-8")).get("narrative_integrity", {}).get("schema_version") == 1
            ),
        ):
            logger.info("Resuming: Existing fact check report reused.")
            fact_check_result = json.loads(fact_check_p.read_text(encoding="utf-8"))
        else:
            manifest.invalidate_from(ProductionStage.FACT_CHECK)
            story_plan_data = json.loads(story_plan_p.read_text(encoding="utf-8"))
            fact_check_result = audit_script_with_dossier(
                script_content,
                dossier.to_dict(),
                story_plan=story_plan_data,
            )
            fact_check_result["production_run_id"] = manifest.run_id
            fact_check_result["topic"] = plan.topic
            fact_check_p.write_text(json.dumps(fact_check_result, indent=2, ensure_ascii=False), encoding="utf-8")
            manifest.mark_stage_completed(ProductionStage.FACT_CHECK, {"fact_check_report": str(fact_check_p)})
            manifest.save(work_dir)

        fact_check_verdict = str(fact_check_result.get("overall_verdict", "UNKNOWN")).upper()
        fact_check_status = {
            "VERIFIED": "PASS",
            "DISPUTED": "FAIL",
            "PROBABLE": "NEEDS_REVIEW",
            "UNVERIFIED": "NEEDS_REVIEW",
        }.get(fact_check_verdict, "UNKNOWN")
        integrity_status = str(
            fact_check_result.get("narrative_integrity", {}).get("gate_status", "REVIEW_REQUIRED")
        ).upper()
        if integrity_status == "BLOCKED":
            fact_check_status = "FAIL"
        elif integrity_status != "ELIGIBLE_FOR_EDITORIAL_REVIEW" or fact_check_verdict != "VERIFIED":
            fact_check_status = "NEEDS_REVIEW"
        manifest.extra_fields["fact_check_verdict"] = fact_check_verdict
        manifest.extra_fields["fact_check_status"] = fact_check_status
        manifest.extra_fields["narrative_integrity_status"] = integrity_status

        if stage_limit == "script":
            manifest.current_stage = "script"
            manifest.save(work_dir)
            return self._build_result(manifest, plan, work_dir, folder_name)

        # ----------------------------------------------------------------------
        # STAGE 6: VISUAL SHOT PLANNING
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.VISUAL_PLAN.value
        broll_plan_p = work_dir / "broll_plan.json"
        narratives = self.script_parser.parse_text(script_content)
        shots_data: List[Dict[str, Any]] = []

        if self._stage_artifact_valid(
            manifest,
            ProductionStage.VISUAL_PLAN,
            "broll_plan",
            broll_plan_p,
            lambda: isinstance(json.loads(broll_plan_p.read_text(encoding="utf-8")), list)
            and all(isinstance(shot, dict) and shot.get("shot_id") for shot in json.loads(broll_plan_p.read_text(encoding="utf-8"))),
        ):
            logger.info("Resuming: Existing visual B-roll plan reused.")
            shots_data = json.loads(broll_plan_p.read_text(encoding="utf-8"))
        else:
            manifest.invalidate_from(ProductionStage.VISUAL_PLAN)
            if narratives:
                shots = self.visual_gen.generate_shots_for_narrative(narratives[0])
                shots_data = [s.to_dict() for s in shots]
                broll_plan_p.write_text(json.dumps(shots_data, indent=2, ensure_ascii=False), encoding="utf-8")
                manifest.mark_stage_completed(ProductionStage.VISUAL_PLAN, {"broll_plan": str(broll_plan_p)})
                manifest.save(work_dir)

        # ----------------------------------------------------------------------
        # STAGE 7: MEDIA RETRIEVAL & LOCAL REUSE
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.MEDIA.value
        footage_dir = work_dir / "footage"
        footage_dir.mkdir(parents=True, exist_ok=True)
        media_manifest_p = work_dir / "media_manifest.json"
        downloaded_assets: List[Dict[str, Any]] = []
        media_shots: List[Dict[str, Any]] = []
        reusable_media = self._load_reusable_media(
            manifest=manifest,
            media_manifest_path=media_manifest_p,
            expected_shots=shots_data,
            topic=plan.topic,
            dry_run=dry_run,
        )
        if reusable_media is not None:
            downloaded_assets, media_shots = reusable_media
        else:
            manifest.invalidate_from(ProductionStage.MEDIA)

        # A media file alone is not evidence of coverage.  Track every required
        # shot and its provenance so Final QA can judge the mapping truthfully.
        existing_files = list(footage_dir.glob("*"))
        media_extensions = {".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
        valid_media_files = [
            f for f in existing_files
            if f.suffix.lower() in media_extensions and "_storyboard" not in f.stem.lower()
        ]

        MINIMAL_PNG_BYTES = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xa0"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        if reusable_media is not None:
            logger.info("Resuming: Valid per-shot media manifest reused.")
        elif dry_run and shots_data:
            logger.info("Dry-run mode active: generating storyboard placeholder frames for timeline.")
            for idx, s in enumerate(shots_data, 1):
                s_id = s.get("shot_id", f"shot_{idx:02d}")
                ph_path = footage_dir / f"{s_id}_storyboard.png"
                if not ph_path.is_file():
                    ph_path.write_bytes(MINIMAL_PNG_BYTES)
                downloaded_assets.append({
                    "shot_id": s_id,
                    "local_path": str(ph_path.resolve()),
                    "title": f"Storyboard Frame {s_id}",
                    "media_type": "image",
                    "media_status": "PLACEHOLDER",
                    "dry_run": True,
                })
                media_shots.append({
                    "shot_id": s_id,
                    "required": self._shot_requires_media(s),
                    "status": "PLACEHOLDER" if self._shot_requires_media(s) else "NOT_REQUIRED",
                    "local_path": str(ph_path.resolve()),
                    "reason": "Storyboard placeholder is permitted only for DRY_RUN." if self._shot_requires_media(s) else "Visual plan does not require retrieved B-roll.",
                })
        elif not dry_run and shots_data:
            finder = self.media_finder or media_finder_mod.MediaFinder()
            target_shots = [
                s for s in shots_data
                if self._shot_requires_media(s)
            ]
            if plan.max_broll_shots is not None and plan.max_broll_shots > 0:
                target_shots = target_shots[:plan.max_broll_shots]

            query_cache: Dict[str, Optional[Dict[str, Any]]] = {}
            for s in target_shots:
                # Check if this shot already has a dedicated downloaded file
                s_id = s.get("shot_id", "")
                existing_for_shot = [f for f in valid_media_files if s_id in f.name]
                if existing_for_shot:
                    logger.info(f"Reusing existing local media for shot {s_id}: {existing_for_shot[0].name}")
                    downloaded_assets.append({
                        "shot_id": s_id,
                        "local_path": str(existing_for_shot[0].resolve()),
                        "title": existing_for_shot[0].name,
                        "media_type": "video" if existing_for_shot[0].suffix.lower() in {".mp4", ".mov", ".webm"} else "image",
                        "media_status": "LOCAL_REUSED",
                    })
                    media_shots.append({
                        "shot_id": s_id,
                        "required": True,
                        "status": "LOCAL_REUSED",
                        "local_path": str(existing_for_shot[0].resolve()),
                    })
                    continue

                search_queries = self._build_media_search_queries(s, plan.topic)
                s["query"] = search_queries[0] if search_queries else plan.topic
                s["media_search_attempts"] = []
                vr = s.get("visual_requirement", "GENERIC_ALLOWED")
                media_type = s.get("preferred_media_type", "any")
                if media_type == "image":
                    media_type = "photo"
                era = s.get("era", "auto")
                style = "archival" if era in {"historical", "past"} else ("conceptual" if era == "future" else "documentary")
                accepted = False

                for q in search_queries:
                    query_key = " ".join(q.lower().split())
                    if query_key in query_cache:
                        cached_item = query_cache[query_key]
                        s["media_search_attempts"].append({
                            "query": q,
                            "status": "CACHE_HIT" if cached_item else "CACHE_MISS",
                        })
                        if cached_item is not None:
                            reused = dict(cached_item)
                            reused["shot_id"] = s_id
                            reused["media_status"] = "LOCAL_REUSED"
                            downloaded_assets.append(reused)
                            media_shots.append({
                                "shot_id": s_id,
                                "required": True,
                                "status": "LOCAL_REUSED",
                                "local_path": reused.get("local_path", ""),
                                "source_url": reused.get("source_url", ""),
                                "license": reused.get("license", ""),
                                "rights_status": reused.get("rights_status", "UNKNOWN"),
                                "selected_query": q,
                                "visual_evidence_policy": s.get("visual_evidence_policy", "VISUALS_DO_NOT_SUBSTITUTE_FOR_CLAIM_EVIDENCE"),
                            })
                            accepted = True
                            break
                        continue

                    try:
                        res = finder.find_and_download(
                            request=q,
                            media=media_type,
                            era=era,
                            style=style,
                            count=1,
                            folder=f"{folder_name}/footage",
                            visual_requirement=vr,
                            research_intelligence=research_intelligence,
                        )
                        s["media_search_attempts"].append({
                            "query": q,
                            "status": res.status,
                            "providers_contacted": list(res.providers_contacted),
                            "candidate_count": res.total_candidates_found,
                            "usable_results": res.usable_results,
                        })
                        found = False
                        for item in res.results:
                            if not item.local_path or not Path(item.local_path).is_file() or Path(item.local_path).stat().st_size <= 0:
                                continue
                            d_item = item.to_dict()
                            d_item["shot_id"] = s_id
                            d_item["media_status"] = "REAL_DOWNLOADED"
                            d_item["selected_query"] = q
                            if not self.qa_engine.media_asset_matches_topic(s, d_item, plan.topic):
                                logger.warning(
                                    "Rejected downloaded media for shot %s because its title/entities do not match topic '%s'.",
                                    s_id,
                                    plan.topic,
                                )
                                s["media_search_attempts"][-1]["status"] = "REJECTED_TOPIC_MISMATCH"
                                continue
                            downloaded_assets.append(d_item)
                            valid_media_files.append(Path(item.local_path))
                            media_shots.append({
                                "shot_id": s_id,
                                "required": True,
                                "status": "REAL_DOWNLOADED",
                                "local_path": str(Path(item.local_path).resolve()),
                                "source_url": d_item.get("source_url", ""),
                                "title": d_item.get("title", ""),
                                "provider": d_item.get("provider", ""),
                                "creator": d_item.get("creator", ""),
                                "license": d_item.get("license", ""),
                                "license_url": d_item.get("license_url", ""),
                                "rights_status": d_item.get("rights_status", "UNKNOWN"),
                                "selected_query": q,
                                "visual_evidence_policy": s.get("visual_evidence_policy", "VISUALS_DO_NOT_SUBSTITUTE_FOR_CLAIM_EVIDENCE"),
                            })
                            query_cache[query_key] = d_item
                            accepted = True
                            found = True
                            break
                        if not found:
                            query_cache[query_key] = None
                        if accepted:
                            break
                    except Exception as exc:
                        logger.warning("B-roll search failed for shot %s ('%s'): %s", s_id, q, exc)
                        s["media_search_attempts"].append({"query": q, "status": "SEARCH_ERROR", "error": str(exc)})
                        query_cache[query_key] = None

                if not accepted:
                    s["media_acquisition_status"] = "MISSING"
                    s["media_acquisition_reason"] = "No relevant downloadable asset found after primary and fallback queries."
                else:
                    s["media_acquisition_status"] = "ACQUIRED"


            # Persist the topic-grounded search strings used for media lookup.
            broll_plan_p.write_text(json.dumps(shots_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # Production runs never manufacture coverage with a placeholder.
            # Every required shot remains visibly MISSING when acquisition fails.
            for idx, s in enumerate(shots_data, 1):
                s_id = s.get("shot_id", f"shot_{idx:02d}")
                if self._shot_requires_media(s) and not any(a.get("shot_id") == s_id for a in downloaded_assets):
                    was_attempted = any(target.get("shot_id") == s_id for target in target_shots)
                    media_shots.append({
                        "shot_id": s_id,
                        "required": True,
                        "status": "MISSING",
                        "reason": (
                            "No relevant downloadable or reusable local media was acquired after primary and fallback queries."
                            if was_attempted else "Required shot was skipped by max_broll_shots and has no real media assignment."
                        ),
                        "search_attempts": s.get("media_search_attempts", []),
                        "visual_evidence_policy": s.get(
                            "visual_evidence_policy", "VISUALS_DO_NOT_SUBSTITUTE_FOR_CLAIM_EVIDENCE"
                        ),
                        "rights_status": "NOT_ACQUIRED",
                    })

        # Include shots that do not need B-roll in the manifest rather than
        # treating them as failed coverage requirements.
        recorded_shots = {entry["shot_id"] for entry in media_shots}
        for idx, s in enumerate(shots_data, 1):
            s_id = s.get("shot_id", f"shot_{idx:02d}")
            if s_id not in recorded_shots:
                media_shots.append({
                    "shot_id": s_id,
                    "required": self._shot_requires_media(s),
                    "status": "NOT_REQUIRED",
                    "reason": "The visual plan does not require retrieved B-roll for this shot.",
                })

        # Write media manifest with provenance
        media_manifest_data = {
            "topic": plan.topic,
            "folder": str(footage_dir),
            "total_assets": len(downloaded_assets),
            "assets": downloaded_assets,
            "shots": media_shots,
            "run_mode": "DRY_RUN" if dry_run else "REAL_RUN",
            "production_run_id": manifest.run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        media_manifest_p.write_text(json.dumps(media_manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.mark_stage_completed(ProductionStage.MEDIA, {"media_manifest": str(media_manifest_p)})
        manifest.save(work_dir)

        # Legacy 10-Dimension Content Quality Report & Manifest sync
        quality_evaluator = ContentQualityEvaluator()
        quality_report = quality_evaluator.evaluate(
            topic=plan.topic,
            dossier_data=dossier.to_dict(),
            script_text=script_content,
            fact_check_result=fact_check_result,
            shots_data=shots_data,
            downloaded_assets=downloaded_assets,
        )
        content_quality_p = work_dir / "content_quality_report.json"
        content_quality_p.write_text(json.dumps(quality_report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.artifacts["content_quality_json"] = str(content_quality_p)
        manifest.artifacts["dossier_json"] = str(dossier_json_p)
        manifest.artifacts["dossier_md"] = str(dossier_md_p)
        manifest.extra_fields["content_quality"] = quality_report.to_dict()
        manifest.extra_fields["shots_planned"] = len(shots_data)
        manifest.extra_fields["assets_downloaded"] = len(downloaded_assets)
        manifest.extra_fields["real_assets_ready"] = sum(
            1 for asset in downloaded_assets
            if asset.get("media_status") in {"REAL_DOWNLOADED", "LOCAL_REUSED"}
        )

        # ----------------------------------------------------------------------
        # STAGE 8: SUBTITLE GENERATION
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.SUBTITLE.value
        srt_p = work_dir / "subtitles.srt"
        subtitle_valid = self._stage_artifact_valid(
            manifest,
            ProductionStage.SUBTITLE,
            "subtitles_srt",
            srt_p,
            lambda: bool(srt_p.read_text(encoding="utf-8").strip())
            and "-->" in srt_p.read_text(encoding="utf-8"),
        )
        if not subtitle_valid:
            manifest.invalidate_from(ProductionStage.SUBTITLE)
            if narratives:
                self.srt_gen.write_srt_file(srt_p, narratives[0].sections)
        if not srt_p.is_file() or not srt_p.read_text(encoding="utf-8").strip() or "-->" not in srt_p.read_text(encoding="utf-8"):
            manifest.mark_failed(ProductionStage.SUBTITLE, "Subtitle generation did not produce a non-empty SRT with timecodes")
            manifest.save(work_dir)
            return self._build_result(manifest, plan, work_dir, folder_name)
        manifest.mark_stage_completed(ProductionStage.SUBTITLE, {"subtitles_srt": str(srt_p)})
        manifest.save(work_dir)

        # ----------------------------------------------------------------------
        # STAGE 9: NATIVE CAPCUT DRAFT GENERATION
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.CAPCUT.value
        capcut_draft_dir = work_dir / "capcut"
        timeline_p = work_dir / "timeline.json"

        # Assemble TimelineClips
        timeline_clips: List[TimelineClip] = []
        cues: List[SubtitleCue] = []

        # Read subtitles if available
        if srt_p.is_file():
            srt_lines = srt_p.read_text(encoding="utf-8").strip().split("\n\n")
            for block in srt_lines:
                lines = [l.strip() for l in block.split("\n") if l.strip()]
                if len(lines) >= 3 and "-->" in lines[1]:
                    try:
                        idx = int(lines[0])
                        times = lines[1].split("-->")
                        st = self._parse_srt_timestamp(times[0].strip())
                        en = self._parse_srt_timestamp(times[1].strip())
                        txt = " ".join(lines[2:])
                        cues.append(SubtitleCue(index=idx, start_seconds=st, end_seconds=en, text=txt))
                    except Exception:
                        pass

        # Map shots and downloaded media into TimelineClips
        for idx, shot in enumerate(shots_data, 1):
            s_id = shot.get("shot_id", f"shot_{idx:02d}")
            st = float(shot.get("start_seconds", 0.0))
            en = float(shot.get("end_seconds", st + 5.0))
            dur = max(0.5, en - st)

            # Match with downloaded asset
            matched_asset = next((a for a in downloaded_assets if a.get("shot_id") == s_id), None)
            asset_p = matched_asset.get("local_path") if matched_asset else None
            m_type = matched_asset.get("media_type", "image") if matched_asset else "image"

            timeline_clips.append(TimelineClip(
                clip_id=f"clip_{idx:02d}",
                shot_id=s_id,
                start_seconds=st,
                end_seconds=en,
                duration_seconds=dur,
                file_path=asset_p,
                asset_title=matched_asset.get("title", "") if matched_asset else "",
                media_type=m_type,
                track=0,
                text_overlay=shot.get("text_overlay", ""),
                visual_requirement=shot.get("visual_requirement", "GENERIC_ALLOWED"),
            ))

        timeline_data = TimelineData(
            project_name=f"Nugi_{clean_topic_slug[:25]}",
            aspect_ratio="9:16",
            width=1080,
            height=1920,
            fps=30.0,
            total_duration_seconds=plan.duration_seconds,
            total_frames=int(round(plan.duration_seconds * 30)),
            subtitles_file="subtitles.srt",
            clips=timeline_clips,
            subtitles=cues,
            narrative_id="narasi-01",
            title=plan.topic,
        )
        timeline_data.save(timeline_p)

        # Generate native CapCut draft package
        self.capcut_gen.generate_from_timeline(
            timeline=timeline_data,
            output_draft_dir=capcut_draft_dir,
            project_name=timeline_data.project_name,
            include_subtitles=True,
        )

        # Optional installation to user's CapCut Desktop drafts library
        installed_path = None
        if install_to_capcut:
            try:
                installed_path = self.capcut_gen.install_to_capcut_desktop(
                    draft_dir=capcut_draft_dir,
                    project_name=timeline_data.project_name,
                )
            except Exception as e:
                logger.warning(f"Could not install to CapCut desktop library: {e}")

        capcut_validation = self.capcut_val.validate_draft(capcut_draft_dir)
        capcut_validation_p = work_dir / "capcut_validation.json"
        capcut_validation_p.write_text(
            json.dumps(capcut_validation.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        manifest.extra_fields["capcut_status"] = capcut_validation.status
        manifest.extra_fields["capcut_app_installed_path"] = str(installed_path) if installed_path else ""

        manifest.mark_stage_completed(
            ProductionStage.CAPCUT,
            {
                "capcut_draft": str(capcut_draft_dir),
                "timeline_json": str(timeline_p),
                "capcut_validation": str(capcut_validation_p),
            }
        )

        # ----------------------------------------------------------------------
        # STAGE 10: FINAL QA ENGINE
        # ----------------------------------------------------------------------
        manifest.current_stage = ProductionStage.FINAL_QA.value
        manifest.save(work_dir)
        qa_report = self.qa_engine.evaluate_production(work_dir)
        qa_p = qa_report.save(work_dir)

        manifest.quality = qa_report.to_dict()
        manifest.mark_stage_completed(ProductionStage.FINAL_QA, {"final_qa": str(qa_p)})

        # Complete status
        manifest.current_stage = ProductionStage.COMPLETE.value
        manifest.status = "completed" if qa_report.is_publishable else "needs_review"
        manifest.save(work_dir)

        return self._build_result(manifest, plan, work_dir, folder_name, qa_report)

    @staticmethod
    def _stage_artifact_valid(
        manifest: ProductionManifest,
        stage: ProductionStage,
        artifact_key: str,
        expected_path: Path,
        validator: Any,
    ) -> bool:
        """Reuse only a manifest-linked artifact that passes its stage check."""
        if not manifest.is_stage_done(stage) or not expected_path.is_file():
            return False
        recorded_path = manifest.artifacts.get(artifact_key)
        if not recorded_path:
            return False
        try:
            return Path(recorded_path).resolve() == expected_path.resolve() and bool(validator())
        except Exception as exc:
            logger.info("Cannot reuse %s artifact %s: %s", stage.value, expected_path, exc)
            return False

    @staticmethod
    def _build_media_search_queries(shot: Dict[str, Any], topic: str) -> List[str]:
        """Build deduplicated, topic-grounded queries from a visual plan record."""
        primary = shot.get("query") or shot.get("search_query") or topic
        raw_queries = [primary] + list(shot.get("fallback_queries") or [])
        queries: List[str] = []
        seen: Set[str] = set()
        for raw_query in raw_queries:
            query = str(raw_query or "").strip()
            if not query:
                continue
            if topic and topic.lower() not in query.lower():
                query = f"{query} {topic}".strip()
            normalized = " ".join(query.lower().split())
            if normalized not in seen:
                seen.add(normalized)
                queries.append(query)
        return queries

    @staticmethod
    def _shot_requires_media(shot: Dict[str, Any]) -> bool:
        return bool(shot.get("search_required", True)) and shot.get("visual_requirement") not in {
            "NO_BROLL", "NO_VISUAL", "REMOTION_REQUIRED"
        }

    def _load_reusable_media(
        self,
        manifest: ProductionManifest,
        media_manifest_path: Path,
        expected_shots: List[Dict[str, Any]],
        topic: str,
        dry_run: bool,
    ) -> Optional[tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        expected_mode = "DRY_RUN" if dry_run else "REAL_RUN"

        def valid() -> bool:
            data = json.loads(media_manifest_path.read_text(encoding="utf-8"))
            if (
                data.get("production_run_id") != manifest.run_id
                or data.get("topic") != topic
                or data.get("run_mode") != expected_mode
                or not isinstance(data.get("assets"), list)
                or not isinstance(data.get("shots"), list)
            ):
                return False
            shot_map = {item.get("shot_id"): item for item in data["shots"] if item.get("shot_id")}
            assets_by_shot = {
                item.get("shot_id"): item for item in data["assets"] if isinstance(item, dict) and item.get("shot_id")
            }
            expected_ids = {item.get("shot_id") for item in expected_shots}
            if set(shot_map) != expected_ids:
                return False
            for shot in expected_shots:
                entry = shot_map.get(shot.get("shot_id"), {})
                required = self._shot_requires_media(shot)
                if entry.get("required") != required:
                    return False
                status = entry.get("status")
                if required and dry_run and status != "PLACEHOLDER":
                    return False
                if required and not dry_run and status not in {"REAL_DOWNLOADED", "LOCAL_REUSED"}:
                    # Failed or placeholder assignments should be retried when a
                    # user resumes a real production run.
                    return False
                if status in {"REAL_DOWNLOADED", "LOCAL_REUSED", "PLACEHOLDER"}:
                    local_path = Path(entry.get("local_path", ""))
                    if not local_path.is_file() or local_path.stat().st_size <= 0:
                        return False
                if required and status in {"REAL_DOWNLOADED", "LOCAL_REUSED"}:
                    asset = {**assets_by_shot.get(shot.get("shot_id"), {}), **entry}
                    if not self.qa_engine.media_asset_matches_topic(shot, asset, topic):
                        return False
            return True

        if not self._stage_artifact_valid(
            manifest,
            ProductionStage.MEDIA,
            "media_manifest",
            media_manifest_path,
            valid,
        ):
            return None
        data = json.loads(media_manifest_path.read_text(encoding="utf-8"))
        return data["assets"], data["shots"]

    @staticmethod
    def _parse_srt_timestamp(ts: str) -> float:
        parts = ts.replace(",", ".").split(":")
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s

    def _build_result(
        self,
        manifest: ProductionManifest,
        plan: ProductionPlan,
        work_dir: Path,
        folder_name: str,
        qa_report: Optional[FinalQAReport] = None,
    ) -> ProductionRunResult:
        qa_dict = qa_report.to_dict() if qa_report else {"verdict": "STAGE_LIMITED", "overall_quality_score": 0.0}
        score = qa_report.overall_quality_score if qa_report else 0.0
        verdict = qa_report.verdict if qa_report else "STAGE_LIMITED"

        return ProductionRunResult(
            status=verdict,
            topic=plan.topic,
            workspace_folder=f"output/{folder_name}",
            run_id=manifest.run_id,
            plan=plan.to_dict(),
            artifacts=manifest.artifacts,
            quality_score=score,
            qa_report=qa_dict,
            manifest=manifest.to_dict(),
        )
