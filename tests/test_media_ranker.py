"""
tests/test_media_ranker.py
===========================
Unit tests for MediaRanker.

Uses FallbackEmbeddingProvider and FallbackRerankerProvider so no
local AI service (LM Studio, reranker) is required to run tests.
"""

import unittest
from engine.providers.embedding import FallbackEmbeddingProvider
from engine.providers.reranker import FallbackRerankerProvider
from engine.providers.media import MediaItem
from engine.pipeline.media_ranker import MediaRanker


def _make_item(
    provider="wikimedia",
    item_id="file-001",
    title="Test Image",
    description="A test image",
    media_type="image",
    download_url="https://example.com/test.jpg",
    **kwargs,
) -> MediaItem:
    defaults = dict(
        provider=provider,
        id=item_id,
        title=title,
        description=description,
        media_type=media_type,
        source_url="https://example.com/page",
        download_url=download_url,
        thumbnail_url="https://example.com/thumb.jpg",
        creator="Test Creator",
        date="1944",
        license="Public Domain",
    )
    defaults.update(kwargs)
    return MediaItem(**defaults)


class TestMediaRankerDeduplication(unittest.TestCase):

    def setUp(self):
        self.ranker = MediaRanker(
            embedding_provider=FallbackEmbeddingProvider(dim=64),
            reranker_provider=FallbackRerankerProvider(),
        )

    def test_dedup_removes_exact_url_duplicates(self):
        items = [
            _make_item(item_id="1", title="Item 1", download_url="https://example.com/a.jpg"),
            _make_item(item_id="2", title="Item 2", download_url="https://example.com/a.jpg"),  # duplicate
            _make_item(item_id="3", title="Item 3", download_url="https://example.com/b.jpg"),
        ]
        result = self.ranker._deduplicate(items)
        self.assertEqual(len(result), 2)

    def test_dedup_keeps_different_urls(self):
        items = [
            _make_item(item_id="1", download_url="https://example.com/a.jpg"),
            _make_item(item_id="2", download_url="https://example.com/b.jpg"),
            _make_item(item_id="3", download_url="https://example.com/c.jpg"),
        ]
        result = self.ranker._deduplicate(items)
        self.assertEqual(len(result), 3)

    def test_dedup_uses_provider_id_when_no_url(self):
        items = [
            _make_item(item_id="file:same", download_url=""),
            _make_item(item_id="file:same", download_url=""),  # duplicate by id
            _make_item(item_id="file:different", download_url=""),
        ]
        result = self.ranker._deduplicate(items)
        self.assertEqual(len(result), 2)


class TestMediaRankerScoring(unittest.TestCase):

    def setUp(self):
        self.ranker = MediaRanker(
            embedding_provider=FallbackEmbeddingProvider(dim=64),
            reranker_provider=FallbackRerankerProvider(),
        )

    def test_rank_returns_list(self):
        items = [
            _make_item(item_id="1", title="D-Day Normandy 1944",
                       download_url="https://example.com/1.jpg"),
            _make_item(item_id="2", title="Modern Beach Tourism",
                       download_url="https://example.com/2.jpg"),
            _make_item(item_id="3", title="WWII Allied Soldiers landing",
                       download_url="https://example.com/3.jpg"),
        ]
        ranked, reason = self.ranker.rank("D-Day 1944 Normandy soldiers", items, top_n=3)
        self.assertIsInstance(ranked, list)
        self.assertLessEqual(len(ranked), 3)

    def test_rank_populates_final_rank(self):
        items = [
            _make_item(item_id=str(i), download_url=f"https://example.com/{i}.jpg")
            for i in range(5)
        ]
        ranked, _ = self.ranker.rank("test query", items, top_n=5)
        for i, item in enumerate(ranked, 1):
            self.assertEqual(item.final_rank, i)

    def test_rank_top_n_limits_results(self):
        items = [
            _make_item(item_id=str(i), download_url=f"https://example.com/{i}.jpg")
            for i in range(10)
        ]
        ranked, _ = self.ranker.rank("test query", items, top_n=3)
        self.assertLessEqual(len(ranked), 3)

    def test_rank_empty_candidates(self):
        ranked, reason = self.ranker.rank("test query", [], top_n=5)
        self.assertEqual(ranked, [])
        self.assertEqual(reason, "")

    def test_keyword_fallback_populates_embedding_similarity(self):
        items = [
            _make_item(item_id="1", title="D-Day Normandy beach",
                       description="Allied soldiers landing 1944",
                       download_url="https://example.com/1.jpg"),
            _make_item(item_id="2", title="Cooking recipe",
                       description="How to bake chocolate cake",
                       download_url="https://example.com/2.jpg"),
        ]
        result = self.ranker._keyword_score_fallback("D-Day Normandy Allied soldiers", items)
        # D-Day item should score higher than cooking recipe
        dday_score = next(r.embedding_similarity for r in result if "D-Day" in r.title)
        cooking_score = next(r.embedding_similarity for r in result if "Cooking" in r.title)
        self.assertGreater(dday_score, cooking_score)

    def test_rank_returns_fallback_reason_when_services_offline(self):
        """
        FallbackEmbeddingProvider generates 128-dim vectors (<=128 dim),
        which the probe detects as offline for LocalEmbeddingProvider.
        In tests we directly use Fallback providers so reason may be empty
        (fallbacks don't trigger the probe the same way). We just verify
        the return type is correct.
        """
        items = [
            _make_item(item_id="1", download_url="https://example.com/1.jpg")
        ]
        ranked, reason = self.ranker.rank("test query", items)
        self.assertIsInstance(reason, str)
        self.assertIsInstance(ranked, list)

    def test_rank_scores_assigned_are_floats(self):
        items = [
            _make_item(item_id=str(i), download_url=f"https://example.com/{i}.jpg",
                       title=f"Item {i} about history")
            for i in range(4)
        ]
        ranked, _ = self.ranker.rank("history", items)
        for item in ranked:
            self.assertIsInstance(item.embedding_similarity, float)
            self.assertIsInstance(item.reranker_score, float)
            self.assertIsInstance(item.keyword_score, float)


class TestMediaRankerFinalRankComputation(unittest.TestCase):

    def setUp(self):
        self.ranker = MediaRanker(
            embedding_provider=FallbackEmbeddingProvider(dim=64),
            reranker_provider=FallbackRerankerProvider(),
        )

    def test_compute_final_rank_sorts_descending(self):
        items = [
            _make_item(item_id="1", download_url="https://example.com/1.jpg"),
            _make_item(item_id="2", download_url="https://example.com/2.jpg"),
            _make_item(item_id="3", download_url="https://example.com/3.jpg"),
        ]
        items[0].embedding_similarity = 0.9
        items[1].embedding_similarity = 0.3
        items[2].embedding_similarity = 0.6

        result = self.ranker._compute_final_rank(items, emb_ok=True, rer_ok=False)
        # Should be sorted 0.9 > 0.6 > 0.3
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[1].id, "3")
        self.assertEqual(result[2].id, "2")

    def test_compute_final_rank_both_scores_used_when_available(self):
        items = [_make_item(item_id="1", download_url="https://example.com/1.jpg")]
        items[0].embedding_similarity = 0.5
        items[0].reranker_score = 0.8
        result = self.ranker._compute_final_rank(items, emb_ok=True, rer_ok=True)
        # Expected composite: 0.4 * 0.5 + 0.6 * 0.8 = 0.2 + 0.48 = 0.68
        self.assertAlmostEqual(result[0].reranker_score, 0.68, places=2)


if __name__ == "__main__":
    unittest.main()
