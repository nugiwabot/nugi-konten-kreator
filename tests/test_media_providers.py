"""
tests/test_media_providers.py
==============================
Unit tests for MediaItem, MediaProvider abstraction, WikimediaProvider,
and InternetArchiveProvider.

All HTTP calls are mocked — no real internet required.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO

from engine.providers.media import MediaItem, MediaProvider


# ==============================================================================
# MediaItem tests
# ==============================================================================

class TestMediaItem(unittest.TestCase):

    def _make_item(self, **kwargs):
        defaults = dict(
            provider="wikimedia",
            id="File:Test.jpg",
            title="Test Image",
            description="A test photograph",
            media_type="image",
            source_url="https://commons.wikimedia.org/wiki/File:Test.jpg",
            download_url="https://upload.wikimedia.org/wikipedia/commons/test.jpg",
            thumbnail_url="https://upload.wikimedia.org/thumb/test.jpg",
            creator="Test Creator",
            date="1944",
            license="Public Domain",
        )
        defaults.update(kwargs)
        return MediaItem(**defaults)

    def test_media_item_creation(self):
        item = self._make_item()
        self.assertEqual(item.provider, "wikimedia")
        self.assertEqual(item.media_type, "image")
        self.assertEqual(item.keyword_score, 0.0)
        self.assertEqual(item.final_rank, 0)

    def test_build_text_representation_includes_key_fields(self):
        item = self._make_item(
            title="D-Day Landing Omaha Beach",
            description="Allied soldiers landing at Normandy",
            date="1944",
            creator="US Army",
        )
        text = item.build_text_representation()
        self.assertIn("D-Day Landing Omaha Beach", text)
        self.assertIn("Allied soldiers landing at Normandy", text)
        self.assertIn("1944", text)
        self.assertIn("US Army", text)
        self.assertIn("wikimedia", text)

    def test_dedup_key_uses_download_url(self):
        item = self._make_item(download_url="https://example.com/file.jpg")
        self.assertEqual(item.dedup_key(), "https://example.com/file.jpg")

    def test_dedup_key_fallback_to_provider_id(self):
        item = self._make_item(download_url="")
        self.assertEqual(item.dedup_key(), "wikimedia:File:Test.jpg")

    def test_to_dict_returns_dict(self):
        item = self._make_item()
        d = item.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("title", d)
        self.assertIn("download_url", d)

    def test_mime_to_media_type(self):
        self.assertEqual(MediaProvider._mime_to_media_type("image/jpeg"), "image")
        self.assertEqual(MediaProvider._mime_to_media_type("video/mp4"), "video")
        self.assertEqual(MediaProvider._mime_to_media_type("audio/mpeg"), "audio")
        self.assertEqual(MediaProvider._mime_to_media_type("application/pdf"), "document")
        self.assertEqual(MediaProvider._mime_to_media_type(""), "document")


# ==============================================================================
# WikimediaProvider tests (all HTTP mocked)
# ==============================================================================

class TestWikimediaProvider(unittest.TestCase):

    def _make_search_response(self, titles):
        return json.dumps({
            "query": {
                "search": [{"title": t} for t in titles]
            }
        }).encode("utf-8")

    def _make_imageinfo_response(self, title, url, mime, size=0):
        return json.dumps({
            "query": {
                "pages": [
                    {
                        "title": title,
                        "imageinfo": [
                            {
                                "url": url,
                                "mime": mime,
                                "size": size,
                                "width": 800,
                                "height": 600,
                                "thumburl": url + "?thumb",
                                "extmetadata": {
                                    "License": {"value": "Public Domain"},
                                    "Artist": {"value": "Test Author"},
                                    "DateTimeOriginal": {"value": "1944"},
                                    "ImageDescription": {"value": "A historical photo"},
                                }
                            }
                        ]
                    }
                ]
            }
        }).encode("utf-8")

    def test_search_media_returns_items(self):
        from engine.providers.wikimedia_provider import WikimediaProvider

        provider = WikimediaProvider()

        call_count = [0]

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)

            if call_count[0] == 0:
                # First call: search
                resp.read.return_value = self._make_search_response(
                    ["File:D-Day_Omaha_Beach.jpg"]
                )
            else:
                # Second call: imageinfo
                resp.read.return_value = self._make_imageinfo_response(
                    "File:D-Day_Omaha_Beach.jpg",
                    "https://upload.wikimedia.org/dday.jpg",
                    "image/jpeg",
                    size=500000,
                )
            call_count[0] += 1
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            items = provider.search_media("D-Day 1944", media_type="image", max_results=5)

        self.assertGreater(len(items), 0)
        self.assertEqual(items[0].provider, "wikimedia")
        self.assertEqual(items[0].media_type, "image")
        self.assertIn("D-Day", items[0].title)
        self.assertEqual(items[0].date, "1944")
        self.assertEqual(items[0].license, "Public Domain")

    def test_search_media_handles_http_error_gracefully(self):
        from engine.providers.wikimedia_provider import WikimediaProvider
        import urllib.error

        provider = WikimediaProvider()

        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.HTTPError(None, 500, "Server Error", {}, None)):
            items = provider.search_media("anything")

        # Must return empty list — not raise
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)

    def test_search_media_empty_query_returns_empty(self):
        from engine.providers.wikimedia_provider import WikimediaProvider
        provider = WikimediaProvider()
        items = provider.search_media("", media_type="any")
        self.assertEqual(items, [])

    def test_search_media_filters_by_type(self):
        from engine.providers.wikimedia_provider import WikimediaProvider

        provider = WikimediaProvider()

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            # Return a video file
            resp.read.return_value = self._make_imageinfo_response(
                "File:Test.ogv",
                "https://upload.wikimedia.org/test.ogv",
                "video/ogg",
            )
            return resp

        # Search with search returning one result, then imageinfo returning a video
        def mock_urlopen2(req, timeout=None):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            call = getattr(mock_urlopen2, "_call", 0)
            mock_urlopen2._call = call + 1
            if call == 0:
                resp.read.return_value = self._make_search_response(["File:Test.ogv"])
            else:
                resp.read.return_value = self._make_imageinfo_response(
                    "File:Test.ogv",
                    "https://upload.wikimedia.org/test.ogv",
                    "video/ogg",
                )
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen2):
            items = provider.search_media("test", media_type="image", max_results=5)

        # video type should be filtered out when requesting image
        for item in items:
            self.assertEqual(item.media_type, "image")


# ==============================================================================
# InternetArchiveProvider tests (all HTTP mocked)
# ==============================================================================

class TestInternetArchiveProvider(unittest.TestCase):

    def _search_response(self, docs):
        return json.dumps({
            "response": {"docs": docs}
        }).encode("utf-8")

    def _metadata_response(self, identifier, files):
        return json.dumps({
            "metadata": {
                "title": "Test Item",
                "description": "Test description",
                "creator": "Test Creator",
                "date": "1944",
                "licenseurl": "",
                "mediatype": "movies",
            },
            "files": files,
        }).encode("utf-8")

    def test_search_media_returns_items(self):
        from engine.providers.internet_archive_provider import InternetArchiveProvider

        provider = InternetArchiveProvider()

        docs = [{
            "identifier": "test-dday-1944",
            "title": "D-Day Footage 1944",
            "description": "Archival D-Day footage",
            "creator": "US Army Signal Corps",
            "date": "1944",
            "subject": ["D-Day", "World War II"],
            "licenseurl": "",
            "mediatype": "movies",
        }]

        files = [{"name": "dday.mp4", "size": "1000000"}]

        call_count = [0]

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            if call_count[0] == 0:
                resp.read.return_value = self._search_response(docs)
            else:
                resp.read.return_value = self._metadata_response("test-dday-1944", files)
            call_count[0] += 1
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            items = provider.search_media("D-Day 1944", media_type="video", max_results=5)

        self.assertGreater(len(items), 0)
        item = items[0]
        self.assertEqual(item.provider, "internet_archive")
        self.assertEqual(item.media_type, "video")
        self.assertIn("D-Day", item.title)
        self.assertIn("archive.org/download", item.download_url)

    def test_search_media_handles_network_error(self):
        from engine.providers.internet_archive_provider import InternetArchiveProvider
        import urllib.error

        provider = InternetArchiveProvider()

        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("Connection refused")):
            items = provider.search_media("anything")

        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)

    def test_search_empty_query_returns_empty(self):
        from engine.providers.internet_archive_provider import InternetArchiveProvider
        provider = InternetArchiveProvider()
        items = provider.search_media("")
        self.assertEqual(items, [])

    def test_pick_best_file_prefers_mp4(self):
        from engine.providers.internet_archive_provider import InternetArchiveProvider

        provider = InternetArchiveProvider()
        files = [
            {"name": "big_video.avi", "size": "5000000"},
            {"name": "small_video.mp4", "size": "1000000"},
            {"name": "metadata.xml", "size": "1000"},
        ]
        filename, size = provider._pick_best_file(files, "video")
        self.assertEqual(filename, "small_video.mp4")
        self.assertEqual(size, 1000000)

    def test_pick_best_file_returns_empty_when_no_media_files(self):
        from engine.providers.internet_archive_provider import InternetArchiveProvider

        provider = InternetArchiveProvider()
        files = [
            {"name": "metadata.xml", "size": "100"},
            {"name": "torrent.torrent", "size": "200"},
        ]
        filename, size = provider._pick_best_file(files, "video")
        self.assertEqual(filename, "")
        self.assertEqual(size, 0)


if __name__ == "__main__":
    unittest.main()
