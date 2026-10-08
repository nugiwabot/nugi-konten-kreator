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


if __name__ == "__main__":
    unittest.main()
