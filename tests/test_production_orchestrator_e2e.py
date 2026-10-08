"""
tests/test_production_orchestrator_e2e.py
=========================================
Comprehensive integration tests for the unified autonomous content production engine:
  - Executive Producer contract (production_plan.json)
  - Production Manifest state tracking and stage completion
  - Final QA multi-gate evaluation (Hard Gates vs Soft Scores)
  - CapCut Draft generation & 16-point validator
  - Production Orchestrator end-to-end lifecycle
  - Idempotency and resume-ability
"""

import json
import tempfile
import unittest
from pathlib import Path
import pytest

from engine.pipeline.capcut_engine import CapCutDraftGenerator
from engine.pipeline.capcut_validator import CapCutValidator
from engine.pipeline.timeline_model import SubtitleCue, TimelineClip, TimelineData
from engine.production.executive_producer import ExecutiveProducer, ProductionPlan
from engine.production.final_qa import FinalQAEngine, QAVerdict
from engine.production.production_manifest import ProductionManifest, ProductionStage
from engine.production.production_orchestrator import ProductionOrchestrator

pytestmark = pytest.mark.usefixtures("research_offline")


class TestExecutiveProducerContract(unittest.TestCase):

    def test_parse_duration_and_topic_ranges(self):
        # 60-90 detik -> average 75s
        prompt = "Buat video short 60–90 detik tentang kenapa Jepang punya banyak rumah kosong, gaya dokumenter Nugi."
        plan = ExecutiveProducer.parse_user_request(prompt)

        self.assertEqual(plan.duration_seconds, 75.0)
        self.assertIn("jepang punya banyak rumah kosong", plan.topic.lower())
        self.assertEqual(plan.format, "short")
        self.assertTrue(plan.research_needed)
        self.assertTrue(plan.capcut_needed)
        self.assertTrue(plan.final_qa_needed)

    def test_parse_specific_duration(self):
        prompt = "Riset dan buat video 30 detik tentang inflasi tanah perkotaan"
        plan = ExecutiveProducer.parse_user_request(prompt)

        self.assertEqual(plan.duration_seconds, 30.0)
        self.assertIn("inflasi tanah perkotaan", plan.topic.lower())

    def test_save_and_load_production_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            plan = ExecutiveProducer.parse_user_request("Topik uji coba 60 detik")
            plan_file = plan.save(ws)

            self.assertTrue(plan_file.is_file())
            loaded = ProductionPlan.load(plan_file)
            self.assertEqual(loaded.topic, plan.topic)
            self.assertEqual(loaded.duration_seconds, 60.0)
            self.assertTrue(loaded.research_needed)


class TestProductionManifestState(unittest.TestCase):

    def test_stage_tracking_and_resuming(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            manifest = ProductionManifest(topic="Rumah Kosong Jepang", format="short")

            self.assertFalse(manifest.is_stage_done(ProductionStage.RESEARCH))
            manifest.mark_stage_completed(ProductionStage.PLAN)
            manifest.mark_stage_completed(ProductionStage.RESEARCH, {"dossier_json": "path/to/dossier.json"})

            self.assertTrue(manifest.is_stage_done(ProductionStage.PLAN))
            self.assertTrue(manifest.is_stage_done(ProductionStage.RESEARCH))
            self.assertEqual(manifest.artifacts["dossier_json"], "path/to/dossier.json")

            manifest_file = manifest.save(ws)
            self.assertTrue(manifest_file.is_file())

            loaded = ProductionManifest.load(manifest_file)
            self.assertEqual(loaded.topic, "Rumah Kosong Jepang")
            self.assertTrue(loaded.is_stage_done(ProductionStage.RESEARCH))

    def test_invalidate_from_forgets_downstream_artifact_and_quality_claims(self):
        manifest = ProductionManifest(topic="Topic")
        manifest.completed_stages = ["plan", "research", "media", "capcut", "final_qa"]
        manifest.artifacts = {
            "dossier_json": "dossier.json",
            "media_manifest": "media.json",
            "capcut_validation": "validation.json",
            "final_qa": "qa.json",
            "content_quality_json": "quality.json",
        }
        manifest.extra_fields.update({"content_quality": {"overall_score": 99}, "real_assets_ready": 3})

        manifest.invalidate_from(ProductionStage.MEDIA)

        self.assertEqual(manifest.completed_stages, ["plan", "research"])
        self.assertNotIn("media_manifest", manifest.artifacts)
        self.assertNotIn("content_quality_json", manifest.artifacts)
        self.assertNotIn("content_quality", manifest.extra_fields)
        self.assertEqual(manifest.status, "running")


class TestCapCutDraftAndValidation(unittest.TestCase):

    def test_generate_and_validate_native_draft(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            draft_dir = ws / "capcut"

            # Create dummy media asset file on disk
            media_file = ws / "test_shot_01.mp4"
            media_file.write_text("fake video binary stream", encoding="utf-8")

            timeline = TimelineData(
                project_name="Nugi_Test_Draft",
                aspect_ratio="9:16",
                width=1080,
                height=1920,
                fps=30.0,
                total_duration_seconds=15.0,
                total_frames=450,
                clips=[
                    TimelineClip(
                        clip_id="clip_01",
                        shot_id="shot_01",
                        start_seconds=0.0,
                        end_seconds=7.5,
                        duration_seconds=7.5,
                        file_path=str(media_file),
                        asset_title="Akiya Street View",
                        media_type="video",
                    ),
                    TimelineClip(
                        clip_id="clip_02",
                        shot_id="shot_02",
                        start_seconds=7.5,
                        end_seconds=15.0,
                        duration_seconds=7.5,
                        file_path=str(media_file),
                        asset_title="Vacant House Interior",
                        media_type="video",
                    ),
                ],
                subtitles=[
                    SubtitleCue(index=1, start_seconds=0.0, end_seconds=5.0, text="Di Jepang, jutaan rumah dibiarkan kosong."),
                    SubtitleCue(index=2, start_seconds=5.0, end_seconds=10.0, text="Fenomena ini dikenal sebagai akiya."),
                ]
            )

            generator = CapCutDraftGenerator()
            generator.generate_from_timeline(timeline, draft_dir, project_name="Nugi_Test_Draft")

            validator = CapCutValidator()
            report = validator.validate_draft(draft_dir)

            self.assertTrue(report.is_valid, f"Validation failed: {report.errors}")
            self.assertIn(report.status, ["VALIDATED", "APP_VERIFIED"])
            self.assertEqual(report.metadata["tracks_count"], 2)  # Video track + Text track
            self.assertEqual(report.metadata["subtitle_segments"], 2)


class TestFinalQAEngine(unittest.TestCase):

    def test_final_qa_blocks_on_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            qa = FinalQAEngine()
            report = qa.evaluate_production(ws)

            self.assertFalse(report.is_publishable)
            self.assertEqual(report.verdict, QAVerdict.BLOCKED.value)
            self.assertTrue(len(report.hard_blockers) > 0)
            self.assertIn("Missing production_plan.json", report.hard_blockers)

    def test_spoken_word_counter_counts_only_narration_text(self):
        script = """# Production notes
Metadata: 999 words
```python
this code must not count at all
```
```text
[00:00 - 00:08] HOOK
Satu dua tiga empat lima.
```"""
        self.assertEqual(FinalQAEngine._spoken_word_count(script), 5)

    def test_media_coverage_requires_topic_relevance_not_only_a_file(self):
        shot = {"shot_id": "shot_01", "query": "Jakarta commuter train"}
        generic_asset = {
            "media_status": "REAL_DOWNLOADED",
            "source_url": "https://example.org/photo",
            "title": "Group of people outdoors",
        }
        relevant_asset = {
            "media_status": "REAL_DOWNLOADED",
            "source_url": "https://example.org/photo",
            "title": "Jakarta commuter rail platform",
        }

        self.assertFalse(FinalQAEngine.media_asset_matches_topic(shot, generic_asset, "Jakarta transportasi publik komuter"))
        self.assertTrue(FinalQAEngine.media_asset_matches_topic(shot, relevant_asset, "Jakarta transportasi publik komuter"))

    def test_final_qa_requires_manifest_and_explicit_pacing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            (ws / "production_plan.json").write_text(
                json.dumps({"topic": "uji", "duration_seconds": 60}), encoding="utf-8"
            )

            report = FinalQAEngine().evaluate_production(ws)

            self.assertTrue(any("Missing manifest.json" in item for item in report.hard_blockers))
            self.assertTrue(any("spoken_words_per_minute" in item for item in report.hard_blockers))

    def test_final_qa_blocks_on_disputed_claims(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            (ws / "production_plan.json").write_text(json.dumps({"topic": "test", "duration_seconds": 60}), encoding="utf-8")
            (ws / "research_dossier.json").write_text(json.dumps({"topic": "test", "sources": [{"title": "s1"}], "data_points": []}), encoding="utf-8")
            (ws / "script.md").write_text("Kata satu dua tiga empat lima " * 25, encoding="utf-8")
            (ws / "broll_plan.json").write_text(json.dumps([{"shot_id": "s1"}]), encoding="utf-8")
            (ws / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:05,000\nSub text\n", encoding="utf-8")

            # Fact check report with DISPUTED claim
            (ws / "fact_check_report.json").write_text(json.dumps({
                "pass_gate": False,
                "claims": [{"claim": "Pasti untung 1000%", "status": "DISPUTED"}]
            }), encoding="utf-8")

            # Dummy valid capcut dir
            draft_d = ws / "capcut"
            draft_d.mkdir(parents=True)
            (draft_d / "draft_content.json").write_text(json.dumps({
                "id": "1", "name": "t", "duration": 10000000, "fps": 30,
                "canvas_config": {"width": 1080, "height": 1920},
                "tracks": [{"type": "video", "segments": [{"target_timerange": {"start": 0, "duration": 10000000}}]}]
            }), encoding="utf-8")
            (draft_d / "draft_meta_info.json").write_text(json.dumps({"draft_id": "1"}), encoding="utf-8")
            (draft_d / "draft_settings").write_text("test", encoding="utf-8")
            (draft_d / "timeline_layout.json").write_text("{}", encoding="utf-8")

            qa = FinalQAEngine()
            report = qa.evaluate_production(ws)

            self.assertFalse(report.is_publishable)
            self.assertEqual(report.verdict, QAVerdict.BLOCKED.value)
            self.assertTrue(any("DISPUTED" in b for b in report.hard_blockers))


class TestProductionOrchestratorE2E(unittest.TestCase):

    def test_orchestrator_stage_limited_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            orchestrator = ProductionOrchestrator(repo_root=repo_root)

            result = orchestrator.run(
                topic_or_prompt="Kenapa Jepang punya banyak rumah kosong?",
                output_folder="test_akiya_run",
                duration_hint=75.0,
                stage_limit="script",
                dry_run=True,
            )

            ws = repo_root / "output" / "test_akiya_run"
            self.assertTrue((ws / "production_plan.json").is_file())
            self.assertTrue((ws / "research_dossier.json").is_file())
            self.assertTrue((ws / "script.md").is_file())
            self.assertTrue((ws / "story_plan.json").is_file())
            self.assertTrue((ws / "manifest.json").is_file())

            # Verify plan has duration 75s
            plan_data = json.loads((ws / "production_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan_data["duration_seconds"], 75.0)

    def test_orchestrator_full_dry_run_to_capcut(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            orchestrator = ProductionOrchestrator(repo_root=repo_root)

            result = orchestrator.run(
                topic_or_prompt="Kenapa Jepang punya banyak rumah kosong?",
                output_folder="test_akiya_capcut",
                duration_hint=75.0,
                dry_run=True,
            )

            ws = repo_root / "output" / "test_akiya_capcut"
            self.assertTrue((ws / "production_plan.json").is_file())
            self.assertTrue((ws / "research_dossier.json").is_file())
            self.assertTrue((ws / "script.md").is_file())
            self.assertTrue((ws / "fact_check_report.json").is_file())
            self.assertTrue((ws / "broll_plan.json").is_file())
            self.assertTrue((ws / "subtitles.srt").is_file())
            self.assertTrue((ws / "timeline.json").is_file())
            self.assertTrue((ws / "capcut" / "draft_content.json").is_file())
            self.assertTrue((ws / "capcut" / "draft_meta_info.json").is_file())
            self.assertTrue((ws / "final_qa.json").is_file())
            self.assertTrue((ws / "manifest.json").is_file())

            # Verify CapCut validation
            val_report = CapCutValidator().validate_draft(ws / "capcut")
            self.assertTrue(val_report.is_valid)

            # Test Idempotency: Running again with same output folder reuses existing artifacts
            res2 = orchestrator.run(
                topic_or_prompt="Kenapa Jepang punya banyak rumah kosong?",
                output_folder="test_akiya_capcut",
                duration_hint=75.0,
                dry_run=True,
            )
            self.assertEqual(res2.run_id, result.run_id)


if __name__ == "__main__":
    unittest.main()
