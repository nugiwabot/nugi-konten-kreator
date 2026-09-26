"""
tests/test_media_downloader.py
================================
Unit tests for MediaDownloader.

Tests filesystem operations using a real temporary directory.
HTTP download calls are mocked.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from engine.providers.media import MediaItem
from engine.pipeline.media_downloader import (
    DownloadReport,
    DownloadedFile,
    FailedFile,
    MediaDownloader,
)


def _make_item(
    title="D-Day Landing at Omaha Beach",
    download_url="https://example.com/dday.jpg",
    media_type="image",
    provider="wikimedia",
    item_id="file:dday.jpg",
    **kwargs,
) -> MediaItem:
    defaults = dict(
        provider=provider,
        id=item_id,
        title=title,
        description="Historical photo",
        media_type=media_type,
        source_url="https://example.com/page",
        download_url=download_url,
        thumbnail_url="",
        creator="US Army",
        date="1944",
        license="Public Domain",
    )
    defaults.update(kwargs)
    return MediaItem(**defaults)


class TestFilenameHelpers(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dl = MediaDownloader(base_dir=Path(self.tmp))

    def test_safe_filename_basic(self):
        name = self.dl._safe_filename("D-Day Landing at Omaha Beach", ".jpg", 1)
        self.assertEqual(name, "d-day-landing-at-omaha-beach-001.jpg")

    def test_safe_filename_with_index(self):
        name = self.dl._safe_filename("Albert Einstein 1921 portrait", ".jpg", 2)
        self.assertTrue(name.endswith("-002.jpg"))

    def test_safe_filename_no_illegal_chars(self):
        import re
        name = self.dl._safe_filename("File: Test/Image\\Name?", ".jpg", 1)
        # Should not contain filesystem-illegal chars
        self.assertFalse(re.search(r'[<>:"/\\|?*]', name))

    def test_safe_filename_max_length(self):
        long_title = "A" * 200
        name = self.dl._safe_filename(long_title, ".jpg", 1)
        stem = name.rsplit(".", 1)[0]
        # Stem should be under _MAX_FILENAME_LEN + "-NNN" overhead
        self.assertLessEqual(len(stem), 90)

    def test_infer_extension_from_url(self):
        self.assertEqual(MediaDownloader._infer_extension("https://x.com/a.mp4", "video"), ".mp4")
        self.assertEqual(MediaDownloader._infer_extension("https://x.com/a.jpg", "image"), ".jpg")
        self.assertEqual(MediaDownloader._infer_extension("https://x.com/a.jpeg", "image"), ".jpg")
        self.assertEqual(MediaDownloader._infer_extension("https://x.com/a.png", "image"), ".png")

    def test_infer_extension_fallback_by_media_type(self):
        # No extension in URL
        self.assertEqual(
            MediaDownloader._infer_extension("https://x.com/file", "video"), ".mp4"
        )
        self.assertEqual(
            MediaDownloader._infer_extension("https://x.com/file", "image"), ".jpg"
        )

    def test_resolve_collision_no_conflict(self):
        path = Path(self.tmp) / "test-001.jpg"
        result = self.dl._resolve_collision(path)
        self.assertEqual(result, path)

    def test_resolve_collision_creates_new_suffix(self):
        path = Path(self.tmp) / "test-001.jpg"
        path.touch()  # Make it exist
        result = self.dl._resolve_collision(path)
        self.assertNotEqual(result, path)
        self.assertTrue(result.name.endswith(".jpg"))
        self.assertFalse(result.exists())


class TestPathConfinement(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dl = MediaDownloader(base_dir=Path(self.tmp))

    def test_normal_folder_resolves_under_base(self):
        resolved = self.dl._resolve_folder("ww2/d-day")
        self.assertTrue(str(resolved).startswith(self.tmp))

    def test_path_traversal_blocked(self):
        resolved = self.dl._resolve_folder("../../etc/passwd")
        # Should fall back to base_dir/general OR resolve the sanitized components
        # but MUST NOT escape outside base_dir
        base = Path(self.tmp).resolve()
        self.assertTrue(str(resolved).startswith(str(base)),
                        f"Path escaped base_dir: {resolved}")

    def test_empty_folder_gets_default(self):
        resolved = self.dl._resolve_folder("")
        self.assertTrue(str(resolved).startswith(self.tmp))


class TestDownloadBatch(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dl = MediaDownloader(base_dir=Path(self.tmp), timeout=5, max_size_mb=100)

    def _mock_response(self, content=b"FAKE_IMAGE_DATA", content_length=None):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.headers = MagicMock()
        resp.headers.get = MagicMock(return_value=str(content_length) if content_length else None)
        # Simulate streaming: return content then empty bytes
        side_effects = [content, b""]
        resp.read = MagicMock(side_effect=side_effects)
        return resp

    def test_successful_download_creates_file(self):
        item = _make_item(title="D-Day Omaha Beach", download_url="https://example.com/dday.jpg")

        with patch("urllib.request.urlopen", return_value=self._mock_response(b"FAKE_JPEG")):
            report = self.dl.download_batch([item], folder="test-batch", count=1)

        self.assertEqual(report.success_count, 1)
        self.assertEqual(report.fail_count, 0)

        # File should exist
        dl_file = report.successful[0]
        self.assertTrue(Path(dl_file.local_path).exists())
        self.assertIn("d-day-omaha-beach", dl_file.filename)

    def test_sources_json_created(self):
        item = _make_item(title="Test Item", download_url="https://example.com/test.jpg")

        with patch("urllib.request.urlopen", return_value=self._mock_response(b"FAKE_DATA")):
            report = self.dl.download_batch([item], folder="sources-test", count=1)

        self.assertIsNotNone(report.sources_json_path)
        self.assertTrue(report.sources_json_path.exists())

        with open(report.sources_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("assets", data)
        self.assertEqual(len(data["assets"]), 1)
        asset = data["assets"][0]
        self.assertIn("filename", asset)
        self.assertIn("provider", asset)
        self.assertIn("source_url", asset)
        self.assertIn("license", asset)
        self.assertIn("retrieved_at", asset)

    def test_sources_json_contains_license_informatively(self):
        """License must be stored but never filtered on."""
        item = _make_item(
            title="Licensed Item",
            license="CC BY-SA 4.0",
            download_url="https://example.com/item.jpg"
        )

        with patch("urllib.request.urlopen", return_value=self._mock_response(b"DATA")):
            report = self.dl.download_batch([item], folder="license-test", count=1)

        with open(report.sources_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        asset = data["assets"][0]
        self.assertEqual(asset["license"], "CC BY-SA 4.0")

    def test_failed_download_recorded_in_report(self):
        import urllib.error
        item = _make_item(title="Fail Item", download_url="https://example.com/fail.jpg")

        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.HTTPError(None, 404, "Not Found", {}, None)):
            report = self.dl.download_batch([item], folder="fail-test", count=1)

        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.fail_count, 1)
        self.assertEqual(report.failed[0].title, "Fail Item")

    def test_file_too_large_skipped(self):
        dl_small = MediaDownloader(base_dir=Path(self.tmp), max_size_mb=1)
        # Content larger than 1 MB
        big_content = b"X" * (2 * 1024 * 1024)  # 2 MB

        item = _make_item(title="Big File", download_url="https://example.com/big.jpg")

        with patch("urllib.request.urlopen", return_value=self._mock_response(big_content)):
            report = dl_small.download_batch([item], folder="big-test", count=1)

        self.assertEqual(report.success_count, 0)
        self.assertEqual(report.fail_count, 1)

    def test_count_limits_downloads(self):
        items = [
            _make_item(title=f"Item {i}", download_url=f"https://example.com/{i}.jpg",
                       item_id=f"file:{i}")
            for i in range(5)
        ]

        call_count = [0]

        def mock_urlopen(req, timeout=None):
            call_count[0] += 1
            return self._mock_response(b"FAKE_DATA")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            report = self.dl.download_batch(items, folder="count-test", count=2)

        self.assertEqual(report.success_count, 2)
        self.assertEqual(report.total_attempted, 2)

    def test_summary_line_correct(self):
        report = DownloadReport(total_attempted=5)
        report.successful = [MagicMock()] * 4
        report.failed = [MagicMock()] * 1
        summary = report.summary_line()
        self.assertIn("5 requested", summary)
        self.assertIn("4 downloaded successfully", summary)
        self.assertIn("1 failed", summary)

    def test_sources_json_merges_on_rerun(self):
        """Running download twice to same folder should merge sources.json."""
        item1 = _make_item(title="First Item", download_url="https://example.com/1.jpg",
                           item_id="file:1")
        item2 = _make_item(title="Second Item", download_url="https://example.com/2.jpg",
                           item_id="file:2")

        def make_response(content=b"DATA"):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.headers = MagicMock()
            resp.headers.get = MagicMock(return_value=None)
            resp.read = MagicMock(side_effect=[content, b""])
            return resp

        with patch("urllib.request.urlopen", side_effect=lambda *a, **kw: make_response()):
            self.dl.download_batch([item1], folder="merge-test", count=1)
            self.dl.download_batch([item2], folder="merge-test", count=1)

        folder_path = self.dl._resolve_folder("merge-test")
        sources_path = folder_path / "sources.json"
        with open(sources_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Both items should be in sources.json
        self.assertEqual(len(data["assets"]), 2)


if __name__ == "__main__":
    unittest.main()
