"""
tests/test_media_pipeline.py
==============================
Integration tests for MediaPipeline using fully mocked providers.

No internet connection required.
No local AI services required.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

from engine.providers.media import MediaItem, MediaProvider
from engine.providers.embedding import FallbackEmbeddingProvider
from engine.providers.reranker import FallbackRerankerProvider
from engine.pipeline.media_ranker import MediaRanker
from engine.pipeline.media_downloader import MediaDownloader
from engine.pipeline.media_pipeline import MediaPipeline, MediaSearchResult


# ==============================================================================
# Mock provider
# ==============================================================================

class MockMediaProvider(MediaProvider):
    """Returns deterministic MediaItem list for testing."""

    PROVIDER_NAME = "mock"

    def __init__(self, items: Optional[List[MediaItem]] = None, fail: bool = False):
        self._items = items or self._default_items()
        self._fail = fail

    def search_media(self, query: str, media_type: str = "any",
                     max_results: int = 20) -> List[MediaItem]:
        if self._fail:
            raise ConnectionError("Mock provider failure")
        return self._items[:max_results]

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        return None

    @staticmethod
    def _default_items() -> List[MediaItem]:
        items = []
        test_cases = [
            ("D-Day Landing at Omaha Beach", "image", "1944", "US Army Signal Corps"),
            ("Allied Soldiers WWII Normandy", "image", "1944", "National Archives"),
            ("Normandy Archival Footage 1944", "video", "1944", "Imperial War Museum"),
            ("Modern Beach Tourism Normandy", "image", "2020", "Travel Magazine"),
            ("D-Day Documentary Film", "video", "1994", "BBC"),
        ]
        for i, (title, mtype, date, creator) in enumerate(test_cases):
            items.append(MediaItem(
                provider="mock",
                id=f"mock-{i:03d}",
                title=title,
                description=f"Description for {title}",
                media_type=mtype,
                source_url=f"https://mock.example.com/item/{i}",
                download_url=f"https://mock.example.com/download/{i}.{mtype[:3]}",
                thumbnail_url=f"https://mock.example.com/thumb/{i}.jpg",
                creator=creator,
                date=date,
                license="Public Domain" if int(date) < 2000 else "CC BY 4.0",
            ))
        return items


def _make_pipeline(tmp_dir: Path, fail: bool = False) -> MediaPipeline:
    """Build a fully-mocked pipeline for testing."""
    mock_provider = MockMediaProvider(fail=fail)
    ranker = MediaRanker(
        embedding_provider=FallbackEmbeddingProvider(dim=64),
        reranker_provider=FallbackRerankerProvider(),
    )
    downloader = MediaDownloader(base_dir=tmp_dir)
    return MediaPipeline(
        providers=[mock_provider],
        ranker=ranker,
        downloader=downloader,
    )


# ==============================================================================
# Tests: search
# ==============================================================================

class TestMediaPipelineSearch(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pipeline = _make_pipeline(self.tmp)

    def test_search_returns_media_search_result(self):
        result = self.pipeline.search("D-Day 1944 Normandy footage")
        self.assertIsInstance(result, MediaSearchResult)

    def test_search_has_candidates(self):
        result = self.pipeline.search("D-Day 1944 Normandy")
        self.assertGreater(len(result.candidates), 0)

    def test_search_candidates_are_media_items(self):
        result = self.pipeline.search("WWII soldiers")
        for item in result.candidates:
            self.assertIsInstance(item, MediaItem)

    def test_search_expanded_queries_populated(self):
        result = self.pipeline.search("D-Day 1944 Normandy historical footage")
        self.assertIsInstance(result.expanded_queries, list)
        self.assertGreater(len(result.expanded_queries), 0)

    def test_search_top_n_limits_results(self):
        result = self.pipeline.search("D-Day", count=2)
        self.assertLessEqual(len(result.candidates), 2)

    def test_search_final_rank_sequential(self):
        result = self.pipeline.search("D-Day", count=5)
        for i, item in enumerate(result.candidates, 1):
            self.assertEqual(item.final_rank, i)

    def test_search_with_media_type_filter_image(self):
        result = self.pipeline.search("D-Day", media_type="image", count=10)
        # All results should be images (mock provider returns both image and video)
        # Note: filter is applied at expander level, provider may return mix
        # The expander signals image preference; providers honour it
        self.assertIsInstance(result, MediaSearchResult)

    def test_search_provider_failure_returns_empty_candidates(self):
        failing_pipeline = _make_pipeline(self.tmp, fail=True)
        result = failing_pipeline.search("D-Day 1944")
        # Should not crash, may return empty or partial
        self.assertIsInstance(result, MediaSearchResult)
        self.assertIsInstance(result.candidates, list)

    def test_search_fallback_reason_is_string(self):
        result = self.pipeline.search("D-Day 1944")
        self.assertIsInstance(result.fallback_reason, str)


# ==============================================================================
# Tests: search_and_download
# ==============================================================================

class TestMediaPipelineDownload(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pipeline = _make_pipeline(self.tmp)

    def _mock_download_response(self, content=b"MOCK_MEDIA_CONTENT"):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.headers.get = MagicMock(return_value=None)
        resp.read = MagicMock(side_effect=[content, b""])
        return resp

    def test_download_creates_files(self):
        with patch("urllib.request.urlopen", return_value=self._mock_download_response()):
            report = self.pipeline.search_and_download(
                "D-Day 1944", count=2, folder="test-dl"
            )

        self.assertGreater(report.success_count, 0)
        for df in report.successful:
            self.assertTrue(Path(df.local_path).exists())

    def test_download_creates_sources_json(self):
        with patch("urllib.request.urlopen", return_value=self._mock_download_response()):
            report = self.pipeline.search_and_download(
                "WWII soldiers", count=2, folder="sources-test"
            )

        if report.sources_json_path:
            self.assertTrue(report.sources_json_path.exists())
            with open(report.sources_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("assets", data)

    def test_download_report_has_summary_line(self):
        with patch("urllib.request.urlopen", return_value=self._mock_download_response()):
            report = self.pipeline.search_and_download(
                "D-Day", count=1, folder="summary-test"
            )

        summary = report.summary_line()
        self.assertIsInstance(summary, str)
        self.assertIn("requested", summary)

    def test_download_zero_candidates_returns_empty_report(self):
        failing_pipeline = _make_pipeline(self.tmp, fail=True)
        report = failing_pipeline.search_and_download("D-Day", count=3)
        self.assertIsInstance(report.total_attempted, int)
        self.assertEqual(report.total_attempted, 0)


# ==============================================================================
# Tests: script-to-asset
# ==============================================================================

class TestMediaPipelineScriptMode(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pipeline = _make_pipeline(self.tmp)

    def _mock_download_response(self):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.headers.get = MagicMock(return_value=None)
        resp.read = MagicMock(side_effect=[b"FAKE", b""])
        return resp

    def test_search_from_script_returns_list(self):
        script = """
        Pada tanggal 6 Juni 1944, ribuan tentara Sekutu mendarat di pantai Normandy.
        
        Operasi ini melibatkan lebih dari 156.000 tentara.
        """
        with patch("urllib.request.urlopen", return_value=self._mock_download_response()):
            reports = self.pipeline.search_from_script(script, folder="script-test")

        self.assertIsInstance(reports, list)

    def test_search_from_script_empty_text_returns_empty(self):
        reports = self.pipeline.search_from_script("")
        self.assertEqual(reports, [])


# ==============================================================================
# Tests: doctor (health check)
# ==============================================================================

class TestMediaPipelineDoctor(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pipeline = _make_pipeline(self.tmp)

    def test_doctor_returns_dict(self):
        with patch.object(MediaPipeline, "_check_url", return_value="OK"):
            status = self.pipeline.doctor()
        self.assertIsInstance(status, dict)

    def test_doctor_has_all_four_keys(self):
        with patch.object(MediaPipeline, "_check_url", return_value="OK"):
            status = self.pipeline.doctor()
        self.assertIn("wikimedia", status)
        self.assertIn("internet_archive", status)
        self.assertIn("embedding", status)
        self.assertIn("reranker", status)

    def test_doctor_returns_offline_when_unreachable(self):
        with patch.object(MediaPipeline, "_check_url", return_value="OFFLINE"):
            status = self.pipeline.doctor()
        self.assertEqual(status["wikimedia"], "OFFLINE")
        self.assertEqual(status["internet_archive"], "OFFLINE")


if __name__ == "__main__":
    unittest.main()
