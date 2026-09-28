"""
tests/test_pexafy_provider.py
=============================
Unit tests for engine/providers/pexafy_provider.py.

All tests mock network and Gemini config calls:
- NO real internet required
- Fast and deterministic
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from engine.providers.pexafy_provider import PexafyProvider


class TestPexafyProvider(unittest.TestCase):

    def test_video_request_returns_empty_immediately(self):
        """Pexafy must never be called for video requests."""
        provider = PexafyProvider(token="test_token")
        with patch("urllib.request.urlopen") as mock_url:
            res = provider.search_media(query="office video footage", media_type="video")
            self.assertEqual(res, [])
            mock_url.assert_not_called()

    def test_no_token_returns_empty(self):
        """If no API token is configured, search_media returns empty list."""
        provider = PexafyProvider(token="")
        with patch.dict("os.environ", {}, clear=True), patch("os.path.exists", return_value=False):
            res = provider.search_media(query="modern office", media_type="image")
            self.assertEqual(res, [])

    def test_search_photos_parses_media_items(self):
        """Verify JSON-RPC response from Pexafy is converted into MediaItems."""
        provider = PexafyProvider(token="test_bearer_token")

        fake_rpc_response = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "data": [
                                {
                                    "photo_id": "test-photo-001",
                                    "image_url": "https://images.pexels.com/test.jpg",
                                    "urls": {
                                        "regular": "https://images.pexels.com/test_reg.jpg",
                                        "small": "https://images.pexels.com/test_sm.jpg",
                                    },
                                    "width": 1920,
                                    "height": 1080,
                                    "photographer_full_name": "Jane Doe",
                                    "source": "Pexels",
                                    "license_type": "free",
                                    "description": "Professional modern office space",
                                    "uploaded_on": "2024-05-01",
                                }
                            ]
                        })
                    }
                ]
            }
        }
        sse_body = f"data: {json.dumps(fake_rpc_response)}\n\n".encode("utf-8")

        mock_init = MagicMock()
        mock_init.__enter__.return_value = mock_init
        mock_init.headers.get.return_value = "session-123"
        mock_init.read.return_value = b"{}"

        mock_call = MagicMock()
        mock_call.__enter__.return_value = mock_call
        mock_call.headers.get.return_value = "session-123"
        mock_call.read.return_value = sse_body

        with patch("urllib.request.urlopen", side_effect=[mock_init, mock_call]):
            items = provider.search_media(query="modern office", media_type="photo", max_results=5)
            self.assertEqual(len(items), 1)
            first = items[0]
            self.assertEqual(first.provider, "pexafy")
            self.assertEqual(first.id, "test-photo-001")
            self.assertEqual(first.title, "Professional modern office space")
            self.assertEqual(first.media_type, "image")
            self.assertEqual(first.creator, "Jane Doe")
            self.assertEqual(first.download_url, "https://images.pexels.com/test_reg.jpg")
            self.assertEqual(first.thumbnail_url, "https://images.pexels.com/test_sm.jpg")
            self.assertEqual(first.license, "free")
            self.assertEqual(first.width, 1920)
            self.assertEqual(first.height, 1080)

    def test_network_error_handled_gracefully(self):
        """HTTP or connection errors are caught and return an empty list."""
        provider = PexafyProvider(token="test_bearer_token")
        with patch("urllib.request.urlopen", side_effect=ConnectionResetError("Socket reset")):
            items = provider.search_media(query="modern office", media_type="image")
            self.assertEqual(items, [])

    def test_is_available(self):
        p_with_token = PexafyProvider(token="secret_key")
        self.assertTrue(p_with_token.is_available())

        p_no_token = PexafyProvider(token="")
        with patch.dict("os.environ", {}, clear=True), patch("os.path.exists", return_value=False):
            self.assertFalse(p_no_token.is_available())


if __name__ == "__main__":
    unittest.main()
