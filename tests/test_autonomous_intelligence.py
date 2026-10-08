import unittest
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from engine.editorial.idea_discovery import IdeaDiscoveryEngine
from engine.intelligence.request_intent import resolve_request


@dataclass
class FakeFeedItem:
    title: str
    source_name: str = "Test Feed"
    canonical_url: str = "https://example.com/story"
    published_at: str = ""


class FakeRSS:
    def __init__(self, items):
        self.items = items

    def discover(self, query, max_items=25):
        return self.items[:max_items]


class TestAutonomousRequestResolution(unittest.TestCase):
    def test_minimal_create_request_defaults_to_end_to_end(self):
        result = resolve_request("Buat video tentang kenapa rumah makin jauh dari pusat kota")
        self.assertEqual(result.intent, "CREATE_CONTENT")
        self.assertIn("kenapa rumah", result.topic.lower())
        self.assertTrue(result.needs_research)
        self.assertTrue(result.needs_broll)
        self.assertTrue(result.needs_capcut)
        self.assertEqual(result.research_depth, "deep")

    def test_longform_is_inferred(self):
        result = resolve_request("Buat long-form YouTube tentang sejarah KPR")
        self.assertEqual(result.format, "longform")
        self.assertEqual(result.duration_seconds, 600.0)

    def test_discovery_request_does_not_become_a_fake_topic(self):
        result = resolve_request("Cari 5 topik terbaik minggu ini")
        self.assertEqual(result.intent, "DISCOVER_CONTENT")
        self.assertEqual(result.topic, "")
        self.assertEqual(result.requested_count, 5)
        self.assertTrue(result.needs_idea_discovery)

    def test_topicless_batch_request_requires_discovery_first(self):
        result = resolve_request("Buat 10 short video")
        self.assertEqual(result.intent, "CREATE_CONTENT")
        self.assertEqual(result.topic, "")
        self.assertEqual(result.requested_count, 10)
        self.assertTrue(result.needs_idea_discovery)


class TestIdeaDiscovery(unittest.TestCase):

    def test_niche_qualification_accepts_clear_human_system_topic(self):
        from engine.editorial.idea_discovery import evaluate_niche_alignment

        result = evaluate_niche_alignment(
            "Kenapa banyak minimarket berdiri berdekatan dan memengaruhi pilihan konsumen?"
        )
        self.assertEqual(result["decision"], "QUALIFIED")
        self.assertGreaterEqual(result["score"], 55)
        self.assertTrue(result["has_place_connection"])
        self.assertTrue(result["has_human_relevance"])

    def test_niche_qualification_rejects_off_niche_celebrity_gossip(self):
        from engine.editorial.idea_discovery import evaluate_niche_alignment

        result = evaluate_niche_alignment("Skandal asmara selebritas viral minggu ini")
        self.assertEqual(result["decision"], "REJECTED")
        self.assertEqual(result["score"], 0)

    def test_niche_qualification_marks_broad_topic_for_scoping(self):
        from engine.editorial.idea_discovery import evaluate_niche_alignment

        result = evaluate_niche_alignment("Kenapa ekonomi dunia terus berubah?")
        self.assertEqual(result["decision"], "NEEDS_SCOPING")
        self.assertGreaterEqual(result["score"], 25)
        self.assertFalse(result["has_place_connection"])
        self.assertTrue(result["has_system_connection"])

    def test_niche_qualification_keeps_borderline_historical_topic_for_scoping(self):
        from engine.editorial.idea_discovery import evaluate_niche_alignment

        result = evaluate_niche_alignment("Sejarah ekonomi Indonesia")
        self.assertEqual(result["decision"], "NEEDS_SCOPING")
        self.assertGreaterEqual(result["score"], 25)
        self.assertLess(result["score"], 55)

    def test_discovery_filters_rejected_candidates_but_keeps_evidence_boundary(self):
        rss = FakeRSS([
            FakeFeedItem(
                title="Skandal asmara selebritas viral minggu ini",
                canonical_url="https://example.com/off-niche",
            ),
            FakeFeedItem(
                title="Kenapa banyak minimarket berdiri berdekatan dan memengaruhi pilihan konsumen?",
                canonical_url="https://example.com/in-niche",
            ),
        ])
        with TemporaryDirectory() as td:
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(
                count=2, include_evergreen_fallback=False
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["count_returned"], 1)
        self.assertEqual(result["candidates"][0]["niche_decision"], "QUALIFIED")
        self.assertTrue(result["safety"]["feed_items_are_discovery_only"])

    def test_scoping_generates_bounded_question_and_competing_angles(self):
        from engine.editorial.idea_discovery import build_story_scope

        result = build_story_scope(
            "Kenapa harga rumah di Bandung berubah pada 2024?",
            {"primary_domain": "property", "lens": "economics"},
            "QUALIFIED",
        )
        self.assertEqual(result["scoping_status"], "READY_FOR_RESEARCH")
        self.assertIn("Bandung", result["central_question"])
        self.assertTrue(result["concrete_case"])
        self.assertEqual(len(result["angle_options"]), 3)
        self.assertEqual(
            {angle["id"] for angle in result["angle_options"]},
            {"mechanism", "human_tradeoff", "change_over_time"},
        )
        self.assertGreaterEqual(len(result["evidence_needed"]), 4)

    def test_scoping_keeps_broad_topic_in_needs_scoping(self):
        from engine.editorial.idea_discovery import build_story_scope

        result = build_story_scope(
            "Kenapa ekonomi dunia terus berubah?",
            {"primary_domain": "economy", "lens": "economics"},
            "NEEDS_SCOPING",
        )
        self.assertEqual(result["scoping_status"], "NEEDS_SCOPING")
        self.assertIn("Belum ada kasus spesifik", result["concrete_case"])
        self.assertIn("maksimal dua lokasi", result["scope_geography"])
        self.assertEqual(len(result["alternative_explanations"]), 4)

    def test_discovery_candidates_include_scoping_brief_without_claiming_verified_status(self):
        rss = FakeRSS([FakeFeedItem(
            title="Kenapa harga rumah di Bandung berubah pada 2024?",
            canonical_url="https://example.com/scoping",
        )])
        with TemporaryDirectory() as td:
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(
                count=1, include_evergreen_fallback=False
            )
        candidate = result["candidates"][0]
        self.assertIn(candidate["scoping_status"], {"READY_FOR_RESEARCH", "NEEDS_SCOPING"})
        self.assertTrue(candidate["central_question"])
        self.assertEqual(len(candidate["angle_options"]), 3)
        self.assertEqual(candidate["epistemic_role"], "discovery_only")
        self.assertEqual(candidate["status"], "DISCOVERY_ONLY")

    def test_topic_memory_indexes_more_than_120_markdown_files(self):
        from engine.editorial.idea_discovery import _read_existing_content

        with TemporaryDirectory() as td:
            output = Path(td) / "output"
            output.mkdir()
            for index in range(125):
                (output / f"topic-{index:03d}.md").write_text(
                    f"# Historical topic {index}\n\nContent for topic {index}.",
                    encoding="utf-8",
                )
            indexed = _read_existing_content(Path(td))
        self.assertEqual(len(indexed), 125)
        self.assertIn("Historical topic 124", indexed)

    def test_discovery_exposes_duplicate_reason_in_memory_summary(self):
        rss = FakeRSS([FakeFeedItem(title="Kenapa harga rumah di pinggiran kota terus berubah?")])
        with TemporaryDirectory() as td:
            output = Path(td) / "output"
            output.mkdir()
            (output / "old-topic.md").write_text(
                "# Kenapa harga rumah di pinggiran kota terus berubah?\n", encoding="utf-8"
            )
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(
                count=1, include_evergreen_fallback=False
            )
        self.assertEqual(result["count_returned"], 0)
        self.assertEqual(result["topic_memory"]["indexed_titles"], 1)
        self.assertEqual(result["topic_memory"]["omitted_candidates"], 1)
        duplicate = result["topic_memory"]["examples"][0]
        self.assertGreaterEqual(duplicate["similarity"], 0.72)
        self.assertIn("Near-duplicate", duplicate["reason"])

    def test_candidate_serializes_discovery_provenance_and_overlap_fields(self):
        rss = FakeRSS([FakeFeedItem(
            title="Kenapa banyak minimarket berdiri berdekatan dan memengaruhi pilihan konsumen?",
            source_name="Test Feed",
            canonical_url="https://example.com/provenance",
        )])
        with TemporaryDirectory() as td:
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(
                count=1, include_evergreen_fallback=False
            )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["origin_kind"], "rss_feed")
        self.assertEqual(candidate["epistemic_role"], "discovery_only")
        self.assertIn("memory_overlap_reason", candidate)
        self.assertIn("source_url", candidate)

    def test_discovery_ranks_candidates_and_preserves_evidence_boundary(self):
        published = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        rss = FakeRSS([
            FakeFeedItem(
                title="Harga rumah pinggiran kota berubah karena pola kerja baru",
                source_name="ANTARA",
                canonical_url="https://example.com/a",
                published_at=published,
            )
        ])
        with TemporaryDirectory() as td:
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(count=3)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["count_returned"], 1)
        self.assertTrue(result["safety"]["feed_items_are_discovery_only"])
        self.assertTrue(result["safety"]["deep_research_required_before_script_claims"])
        self.assertTrue(result["candidates"][0]["suggested_title"])
        self.assertIsInstance(result["candidates"][0]["story_type"], str)


class TestVisualFeasibilityPreflight(unittest.TestCase):
    def test_specific_scoped_case_has_routes_without_claiming_assets_exist(self):
        from engine.editorial.idea_discovery import build_story_scope
        from engine.editorial.visual_feasibility import assess_visual_feasibility

        topic = "Kenapa harga rumah di Bandung berubah pada 2024?"
        scope = build_story_scope(topic, {"primary_domain": "property", "lens": "economics"}, "QUALIFIED")
        result = assess_visual_feasibility(topic, scope)

        self.assertEqual(result["status"], "VISUALS_FEASIBLE")
        route_ids = {route["id"] for route in result["visual_routes"]}
        self.assertIn("place_and_geography", route_ids)
        self.assertIn("data_and_charts", route_ids)
        self.assertFalse(result["asset_search_performed"])
        self.assertFalse(result["asset_availability_verified"])
        self.assertFalse(result["download_performed"])
        self.assertTrue(all(route["availability"] == "NOT_CHECKED" for route in result["visual_routes"]))

    def test_broad_topic_is_partial_and_surfaces_missing_specific_location(self):
        from engine.editorial.visual_feasibility import assess_visual_feasibility

        result = assess_visual_feasibility(
            "Kenapa ekonomi dunia terus berubah?",
            {"scoping_status": "NEEDS_SCOPING", "concrete_case": "Belum ada kasus spesifik"},
        )

        self.assertEqual(result["status"], "VISUALS_PARTIAL")
        self.assertIn("specific_location_not_identified", result["risk_flags"])
        self.assertTrue(result["recommended_next_step"])
        self.assertFalse(result["asset_availability_verified"])

    def test_discovery_candidate_serializes_visual_preflight_separately_from_asset_search(self):
        rss = FakeRSS([FakeFeedItem(
            title="Kenapa harga rumah di Bandung berubah pada 2024?",
            canonical_url="https://example.com/visual-preflight",
        )])
        with TemporaryDirectory() as td:
            result = IdeaDiscoveryEngine(rss_service=rss, repo_root=Path(td)).discover(
                count=1, include_evergreen_fallback=False
            )

        preflight = result["candidates"][0]["visual_preflight"]
        self.assertIn(preflight["status"], {"VISUALS_FEASIBLE", "VISUALS_PARTIAL"})
        self.assertFalse(preflight["asset_search_performed"])
        self.assertEqual(preflight["confidence"], "LOW")


class TestEvidenceAwareStoryPlanning(unittest.TestCase):
    def test_story_plan_uses_story_type_and_keeps_unverified_claims_as_gaps(self):
        from types import SimpleNamespace
        from engine.editorial.story_planner import build_story_plan
        from engine.editorial.story_type import classify_story_type

        dossier = SimpleNamespace(
            topic="Kenapa sistem transportasi kota berubah?",
            research_question="Apa yang mendorong perubahan sistem transportasi kota?",
            claims=[
                SimpleNamespace(
                    id="c1", text="Sebuah klaim yang belum terverifikasi.",
                    status="UNVERIFIED", confidence_score=0.1, independent_sources_count=0,
                )
            ],
            narrative_angles=[{"human_dilemma": "Bagaimana perubahan ini memengaruhi perjalanan harian?"}],
            causal_relationships=[],
            evidence_gaps=[{"gap": "Tidak ada sumber primer"}],
            epistemic_status="UNVERIFIED",
            evidence_strength=0.1,
        )
        story_type = classify_story_type(dossier.topic)
        plan = build_story_plan(dossier, story_type, duration_seconds=75)

        self.assertEqual(plan["story_type"], story_type["primary_type"])
        self.assertTrue(plan["beats"])
        self.assertEqual(plan["evidence_summary"]["supported_claims_used"], 0)
        self.assertEqual(plan["evidence_summary"]["unresolved_claims"], 1)
        self.assertFalse(plan["evidence_summary"]["publication_approval"])
        self.assertTrue(any("belum terverifikasi" in beat["narration_seed"].lower()
                            for beat in plan["beats"]))

    def test_script_synthesis_uses_story_plan_and_keeps_uncertainty_note(self):
        from types import SimpleNamespace
        from engine.editorial.script_synthesizer import DynamicScriptSynthesizer

        dossier = SimpleNamespace(topic="Uji topik")
        plan = {
            "topic": "Uji topik",
            "story_type": "hidden_system",
            "story_type_name": "HIDDEN SYSTEM STORY",
            "narrative_device": "expose_mechanism",
            "epistemic_status": "UNVERIFIED",
            "evidence_summary": {"supported_claims_used": 0},
            "beats": [{
                "stage": "HOOK",
                "narration_seed": "Apa yang benar-benar diketahui tentang topik ini?",
                "evidence_status": "GAP_OR_QUESTION",
            }, {
                "stage": "EVIDENCE",
                "narration_seed": "Bukti spesifik belum tersedia.",
                "evidence_status": "GAP_OR_QUESTION",
            }],
        }

        script = DynamicScriptSynthesizer().synthesize_script(
            dossier, target_duration_seconds=60, story_plan=plan
        )

        self.assertIn("STORY PLAN / DRAFT NARASI", script)
        self.assertIn("Apa yang benar-benar diketahui", script)
        self.assertIn("kerangka investigasi", script)
        self.assertNotIn("data menunjukkan sebaliknya", script)


if __name__ == "__main__":
    unittest.main()
