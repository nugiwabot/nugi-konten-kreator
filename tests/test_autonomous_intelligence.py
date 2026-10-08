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
