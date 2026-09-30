"""
tests/test_media_finder.py
==========================
Unit tests for engine/pipeline/media_finder.py.

All tests use mock providers, mock ranker, and mock downloader:
- NO network calls
- NO external API tokens required
- Deterministic and fast
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.pipeline.media_downloader import DownloadReport, DownloadedFile
from engine.pipeline.media_finder import (
    MediaFinder,
    MediaFinderItem,
    MediaFinderResult,
)
from engine.providers.media import MediaItem, MediaProvider


# ==============================================================================
# Test Fixtures & Mocks
# ==============================================================================

class FakeProvider(MediaProvider):
    """Controllable in-memory provider for unit testing."""

    def __init__(self, name: str, items: Optional[List[MediaItem]] = None, fail: bool = False):
        self.PROVIDER_NAME = name
        self._items = items or []
        self._fail = fail
        self.searches: List[Dict[str, Any]] = []

    def search_media(
        self, query: str, media_type: str = "any", max_results: int = 20
    ) -> List[MediaItem]:
        self.searches.append({"query": query, "media_type": media_type})
        if self._fail:
            raise ConnectionError(f"Provider {self.PROVIDER_NAME} network failure")
        results = []
        for it in self._items:
            # Match media_type filter
            if media_type == "any" or it.media_type == media_type:
                results.append(it)
        return results[:max_results]

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        for it in self._items:
            if it.id == item_id:
                return it
        return None


def make_test_item(
    provider: str = "wikimedia",
    title: str = "Test Image",
    media_type: str = "image",
    date: str = "2024",
    creator: str = "Photographer",
    url: str = "https://example.com/item.jpg",
) -> MediaItem:
    return MediaItem(
        provider=provider,
        id=url,
        title=title,
        description=f"Description of {title}",
        media_type=media_type,
        source_url=f"https://commons.example.com/{title}",
        download_url=url,
        thumbnail_url=f"{url}_thumb.jpg",
        creator=creator,
        date=date,
        license="CC BY-SA 4.0",
        file_size_bytes=1024,
        metadata={"license_url": "https://creativecommons.org/licenses/by-sa/4.0/"},
    )


class FakeRanker:
    """Mock ranker returning deterministic scores."""

    def rank(self, original_request: str, candidates: List[MediaItem], top_n: int = 10):
        ranked = []
        for i, item in enumerate(candidates, 1):
            item.reranker_score = round(1.0 - (i * 0.05), 3)
            item.final_rank = i
            ranked.append(item)
        return ranked[:top_n], ""


class FakeDownloader:
    """Mock downloader returning simulated successful downloads."""

    def download_batch(self, items: List[MediaItem], folder: str, count: int = 5) -> DownloadReport:
        successful = []
        for idx, item in enumerate(items[:count], 1):
            ext = ".mp4" if getattr(item, "media_type", "image") == "video" else ".jpg"
            successful.append(
                DownloadedFile(
                    filename=f"file_{idx:03d}{ext}",
                    local_path=f"assets/media/{folder}/file_{idx:03d}{ext}",
                    provider=item.provider,
                    source_url=item.source_url,
                    download_url=item.download_url,
                    title=item.title,
                    creator=item.creator,
                    date=item.date,
                    license=item.license,
                    retrieved_at="2026-09-28T00:00:00Z",
                    media_type=item.media_type,
                )
            )
        return DownloadReport(
            total_attempted=len(items[:count]),
            successful=successful,
            failed=[],
            folder=Path(f"assets/media/{folder}"),
        )


# ==============================================================================
# Test Cases
# ==============================================================================

class TestMediaFinder(unittest.TestCase):

    def setUp(self):
        self.pexafy = FakeProvider(
            "pexafy",
            items=[
                make_test_item("pexafy", "Modern Office Worker", "image", "2024", "John Doe", "https://pex.com/1.jpg"),
                make_test_item("pexafy", "Corporate Meeting Room", "image", "2024", "Jane Smith", "https://pex.com/2.jpg"),
            ],
        )
        self.wikimedia = FakeProvider(
            "wikimedia",
            items=[
                make_test_item("wikimedia", "Prehistoric Settlement Reconstruction", "image", "1990", "Museum", "https://wiki.com/settle.jpg"),
                make_test_item("wikimedia", "Normandy Beach 1944", "image", "1944", "Army", "https://wiki.com/dday.jpg"),
                make_test_item("wikimedia", "Historical City Harbor 1920", "image", "1920", "Archivist", "https://wiki.com/harbor.jpg"),
                make_test_item("wikimedia", "Archival Newsreel Footage", "video", "1945", "Newsreel Corp", "https://wiki.com/news.mp4"),
            ],
        )
        self.archive = FakeProvider(
            "internet_archive",
            items=[
                make_test_item("internet_archive", "Ancient Civilization Documentary Film", "video", "1952", "Prelinger", "https://archive.org/ancient.mp4"),
                make_test_item("internet_archive", "Early Human Settlements Artifacts", "image", "1930", "Library", "https://archive.org/artifact.jpg"),
            ],
        )
        self.finder = MediaFinder(
            providers=[self.pexafy, self.wikimedia, self.archive],
            ranker=FakeRanker(),
            downloader=FakeDownloader(),
        )

    # 1. Empty request
    def test_empty_request(self):
        res = self.finder.find("")
        self.assertEqual(len(res.results), 0)
        self.assertEqual(res.total_candidates_found, 0)
        self.assertEqual(len(res.queries), 0)

    # 2. Formal photo request
    def test_formal_photo_request(self):
        res = self.finder.find(
            request="manusia bekerja di kantor modern",
            media="photo",
            era="present",
            style="formal",
            count=5,
        )
        self.assertEqual(res.media_type, "photo")
        self.assertEqual(res.era, "present")
        self.assertEqual(res.style, "formal")
        self.assertGreater(len(res.results), 0)
        for item in res.results:
            self.assertEqual(item.media_type, "image")
        # Check that query intelligence generated formal cues
        combined_queries = " ".join(res.queries).lower()
        self.assertIn("editorial", combined_queries)
        self.assertIn("professional", combined_queries)

    # 3. Neutral photo request
    def test_neutral_photo_request(self):
        res = self.finder.find(
            request="orang berjalan di jalan kota",
            media="photo",
            era="present",
            style="neutral",
            count=5,
        )
        self.assertEqual(res.style, "neutral")
        combined_queries = " ".join(res.queries).lower()
        self.assertTrue("documentary" in combined_queries or "observational" in combined_queries or "everyday" in combined_queries)

    # 4. Documentary request
    def test_documentary_request(self):
        res = self.finder.find(
            request="kehidupan pasar tradisional",
            media="photo",
            era="present",
            style="documentary",
            count=5,
        )
        self.assertEqual(res.style, "documentary")
        combined_queries = " ".join(res.queries).lower()
        self.assertTrue("candid" in combined_queries or "documentary" in combined_queries or "authentic" in combined_queries)

    # 5. Historical request
    def test_historical_request(self):
        res = self.finder.find(
            request="manusia mulai hidup menetap pada zaman prasejarah",
            media="any",
            era="historical",
            style="documentary",
            count=5,
        )
        self.assertEqual(res.era, "historical")
        # Historical should contact Wikimedia and Internet Archive first
        self.assertIn("wikimedia", res.providers_contacted)
        self.assertIn("internet_archive", res.providers_contacted)

    # 6. Present request
    def test_present_request(self):
        res = self.finder.find(
            request="kantor modern saat ini",
            media="photo",
            era="present",
            style="formal",
            count=5,
        )
        self.assertEqual(res.era, "present")
        self.assertIn("pexafy", res.providers_contacted)

    # 7. Future request
    def test_future_request(self):
        res = self.finder.find(
            request="rumah masa depan dengan AI",
            media="photo",
            era="future",
            style="conceptual",
            count=5,
        )
        self.assertEqual(res.era, "future")
        self.assertEqual(res.style, "conceptual")
        combined_queries = " ".join(res.queries).lower()
        self.assertTrue("conceptual" in combined_queries or "speculative" in combined_queries or "future" in combined_queries)

    # 8. Video request (TEST A)
    def test_video_request(self):
        """TEST A: Explicit video request.
        assert:
        - result.media_type == 'video'
        - pexafy not called
        - internet_archive called
        - wikimedia can be called
        - all result.media_type == 'video'
        """
        res = self.finder.find(
            request="rekaman sejarah perang dunia",
            media="video",
            era="historical",
            style="archival",
            count=5,
        )
        self.assertEqual(res.media_type, "video")
        # Pexafy MUST NOT be contacted for video
        self.assertNotIn("pexafy", res.providers_contacted)
        # Providers returning video
        self.assertIn("internet_archive", res.providers_contacted)
        self.assertIn("wikimedia", res.providers_contacted)
        self.assertGreater(len(res.results), 0)
        for item in res.results:
            self.assertEqual(item.media_type, "video")

    def test_test_b_microbeat_video(self):
        """TEST B: Microbeat with preferred_media_type='video' preserves video media_type,
        returns only video candidates, and generated queries contain video terminology cues."""
        microbeat = {
            "visual_concept": "Pendaratan pasukan di Normandia",
            "search_query": "D-Day Normandy landing",
            "preferred_media_type": "video",
            "era": "historical",
            "style": "archival",
        }
        res = self.finder.find_from_microbeat(microbeat)
        self.assertEqual(res.media_type, "video")
        self.assertGreater(len(res.results), 0)
        for item in res.results:
            self.assertEqual(item.media_type, "video")
        # Check generated query cues
        combined_queries = " ".join(res.queries).lower()
        video_cues = ["footage", "film", "newsreel", "archival footage", "motion picture"]
        self.assertTrue(
            any(cue in combined_queries for cue in video_cues),
            f"Expected video cue in queries, got: {res.queries}"
        )

    def test_test_c_video_query_generation(self):
        """TEST C: Video query generation for video + archival must NOT generate
        'historical photograph' as the only signal; it must include video intent cues."""
        queries = self.finder._generate_query_intelligence(
            request="rekaman sejarah perang dunia",
            era="historical",
            style="archival",
            media="video",
        )
        combined = " ".join(queries).lower()
        self.assertNotIn("historical photograph", combined)
        self.assertNotIn("photograph", combined)
        video_cues = ["footage", "film", "newsreel", "motion picture", "video"]
        self.assertTrue(
            any(cue in combined for cue in video_cues),
            f"Expected video cue in query generation, got: {queries}"
        )

    def test_test_d_photo_regression(self):
        """TEST D: Photo request must produce media_type == 'image' and not be broken by video fixes."""
        res = self.finder.find(
            request="foto tentara sekutu di normandia",
            media="photo",
            era="historical",
            style="archival",
            count=5,
        )
        self.assertEqual(res.media_type, "photo")
        self.assertGreater(len(res.results), 0)
        for item in res.results:
            self.assertEqual(item.media_type, "image")

    def test_test_e_any_behavior(self):
        """TEST E: media='any' can accept both image and video candidates; do not force video-only."""
        res = self.finder.find(
            request="sejarah peradaban kuno",
            media="any",
            era="historical",
            style="documentary",
            count=10,
        )
        self.assertEqual(res.media_type, "any")
        types_in_results = {item.media_type for item in res.results}
        self.assertIn("video", types_in_results)
        self.assertIn("image", types_in_results)

    # 9. Auto detection
    def test_auto_detection_historical(self):
        res = self.finder.find("manusia prasejarah mulai hidup menetap")
        self.assertEqual(res.era, "historical")
        self.assertEqual(res.style, "documentary")

    def test_auto_detection_future(self):
        res = self.finder.find("rumah masa depan ketika AI mengubah pekerjaan")
        self.assertEqual(res.era, "future")
        self.assertEqual(res.style, "conceptual")

    def test_auto_detection_present_formal(self):
        res = self.finder.find("karyawan profesional di kantor modern")
        self.assertEqual(res.era, "present")
        self.assertEqual(res.style, "formal")

    # 10. Provider routing rules
    def test_provider_routing_rules(self):
        # Video: only archive and wikimedia
        providers_video = self.finder._route_providers(era="present", media="video")
        names_video = [p.PROVIDER_NAME for p in providers_video]
        self.assertNotIn("pexafy", names_video)
        self.assertIn("internet_archive", names_video)
        self.assertIn("wikimedia", names_video)

        # Historical photo: archive and wikimedia prioritized
        providers_hist = self.finder._route_providers(era="historical", media="photo")
        names_hist = [p.PROVIDER_NAME for p in providers_hist]
        self.assertIn("wikimedia", names_hist)
        self.assertIn("internet_archive", names_hist)

    # 11. Query generation variants (4 variants, distinct, non-empty)
    def test_query_generation_variants(self):
        queries = self.finder._generate_query_intelligence(
            request="manusia bekerja di kantor modern",
            era="present",
            style="formal",
        )
        self.assertEqual(len(queries), 4)
        for q in queries:
            self.assertTrue(len(q) > 5)
        # All variants should be distinct
        self.assertEqual(len(set(queries)), 4)

    # 12. Explicit search_query preservation in microbeat
    def test_explicit_search_query_preservation(self):
        microbeat = {
            "visual_concept": "Orang bekerja kelelahan di depan layar komputer",
            "search_query": "exhausted programmer staring at glowing computer screen late night",
            "preferred_media_type": "photo",
            "era": "present",
            "style": "documentary",
        }
        res = self.finder.find_from_microbeat(microbeat)
        self.assertEqual(res.request, "exhausted programmer staring at glowing computer screen late night")

    # 13. Derive search from visual_concept when search_query is missing
    def test_derive_from_visual_concept(self):
        microbeat = {
            "visual_concept": "Pekerja kantor modern berdiskusi di ruang rapat",
            "search_query": "",
            "preferred_media_type": "photo",
        }
        res = self.finder.find_from_microbeat(microbeat)
        self.assertEqual(res.request, "Pekerja kantor modern berdiskusi di ruang rapat")

    # 14. No-provider result / empty candidates gracefully handled
    def test_no_provider_result(self):
        empty_finder = MediaFinder(
            providers=[FakeProvider("empty_provider", items=[])],
            ranker=FakeRanker(),
            downloader=FakeDownloader(),
        )
        res = empty_finder.find("sesuatu yang tidak ada")
        self.assertEqual(len(res.results), 0)
        self.assertIn("No candidates", res.fallback_reason)

    # 15. Metadata & provenance preservation
    def test_metadata_provenance_preservation(self):
        res = self.finder.find(
            request="manusia bekerja di kantor modern",
            media="photo",
            era="present",
            style="formal",
            count=2,
        )
        self.assertGreater(len(res.results), 0)
        first = res.results[0]
        self.assertTrue(bool(first.title))
        self.assertTrue(bool(first.provider))
        self.assertTrue(bool(first.source_url))
        self.assertTrue(bool(first.download_url))
        self.assertTrue(bool(first.license))
        self.assertTrue(isinstance(first.score, float))
        self.assertEqual(first.rank, 1)

    # 16. Download mode does not break search mode
    def test_download_mode_does_not_break_search_mode(self):
        # Search-only mode
        res_search = self.finder.find("manusia bekerja di kantor modern", count=2)
        self.assertEqual(res_search.downloaded_count, 0)
        for item in res_search.results:
            self.assertIsNone(item.local_path)

        # Download mode
        res_down = self.finder.find_and_download("manusia bekerja di kantor modern", count=2, folder="test_run")
        self.assertGreater(res_down.downloaded_count, 0)
        for item in res_down.results:
            self.assertIsNotNone(item.local_path)
            self.assertIn("test_run", item.local_path)

    # 17. Preview formatting
    def test_preview_formatting(self):
        res = self.finder.find("manusia bekerja di kantor modern", count=3)
        preview_text = res.preview(max_items=3)
        self.assertIn("NUGI MEDIA FINDER", preview_text)
        self.assertIn("SEARCH QUERIES USED:", preview_text)
        self.assertIn("TOP CANDIDATES:", preview_text)


if __name__ == "__main__":
    unittest.main()
