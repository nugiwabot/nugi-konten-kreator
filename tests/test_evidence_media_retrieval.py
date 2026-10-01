"""
tests/test_evidence_media_retrieval.py
=======================================
Comprehensive test suite verifying the Evidence-Based B-Roll & Visual Retrieval System.

Covers the 8 mandatory test cases from prompt Section 32 plus hard gate,
insufficient evidence, downloader, and preview formatting tests.
"""

import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.pipeline.media_downloader import DownloadReport, DownloadedFile, MediaDownloader
from engine.pipeline.media_finder import MediaFinder, MediaFinderItem, MediaFinderResult
from engine.pipeline.media_query_expander import MediaQueryExpander
from engine.pipeline.media_ranker import MediaRanker
from engine.pipeline.visual_requirements import (
    GENERIC_ALLOWED,
    NO_BROLL,
    REAL_PREFERRED,
    REAL_REQUIRED,
    REMOTION_REQUIRED,
    PRIMARY_EVIDENCE,
    DIRECT_CONTEXT,
    GENERIC_ATMOSPHERE,
    MOTION_GRAPHICS,
    NO_VISUAL,
    classify_visual_requirement,
    extract_entities,
)
from engine.providers.embedding import FallbackEmbeddingProvider
from engine.providers.media import MediaItem, MediaProvider
from engine.providers.reranker import FallbackRerankerProvider


# ------------------------------------------------------------------------------
# Test Fixtures & Mocks
# ------------------------------------------------------------------------------

class MockProvider(MediaProvider):
    """Controllable mock media provider."""

    def __init__(self, name: str, items: Optional[List[MediaItem]] = None):
        self.PROVIDER_NAME = name
        self._items = items or []
        self.searches: List[Dict[str, Any]] = []

    def search_media(
        self, query: str, media_type: str = "any", max_results: int = 20
    ) -> List[MediaItem]:
        self.searches.append({"query": query, "media_type": media_type})
        results = []
        for it in self._items:
            if media_type == "any" or it.media_type == media_type:
                results.append(it)
        return results[:max_results]

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        for it in self._items:
            if it.id == item_id:
                return it
        return None


def make_item(
    provider: str,
    title: str,
    description: str = "",
    media_type: str = "video",
    date: str = "",
    url: str = "https://example.com/item.mp4",
) -> MediaItem:
    return MediaItem(
        provider=provider,
        id=url,
        title=title,
        description=description or title,
        media_type=media_type,
        source_url=f"https://example.com/{title}",
        download_url=url,
        thumbnail_url=f"{url}.jpg",
        creator="Archivist",
        date=date,
        license="Public Domain",
        file_size_bytes=1048576,
    )


# ------------------------------------------------------------------------------
# Test Suite: Evidence-Based B-Roll System
# ------------------------------------------------------------------------------

class TestEvidenceMediaRetrieval(unittest.TestCase):
    """Verifies all evidence-based retrieval rules and mandatory test cases."""

    def setUp(self):
        self.expander = MediaQueryExpander()
        self.ranker = MediaRanker(
            embedding_provider=FallbackEmbeddingProvider(dim=64),
            reranker_provider=FallbackRerankerProvider(),
        )

    # --------------------------------------------------------------------------
    # TEST 1: Steve Jobs iPhone 2007
    # --------------------------------------------------------------------------
    def test_1_steve_jobs_iphone_2007(self):
        """
        Input: 'Steve Jobs memperkenalkan iPhone pada 2007.'
        Expected:
        - Requirement: REAL_REQUIRED
        - Query must preserve: Steve Jobs, iPhone, 2007
        - Pexafy is DISABLED (not primary, completely excluded for REAL_REQUIRED)
        """
        text = "Steve Jobs memperkenalkan iPhone pada 2007."

        # 1. Classification
        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, REAL_REQUIRED)
        ent_names = [e["name"] for e in entities]
        self.assertTrue(any("Steve Jobs" in e for e in ent_names))
        self.assertTrue(any("iPhone" in e for e in ent_names))
        self.assertTrue(any("2007" in e for e in ent_names))

        # 2. Query expansion entity preservation
        eq = self.expander.expand(text)
        self.assertEqual(eq.visual_requirement, REAL_REQUIRED)
        all_queries_text = " ".join(eq.all_queries).lower()
        self.assertIn("steve jobs", all_queries_text)
        self.assertIn("iphone", all_queries_text)
        self.assertIn("2007", all_queries_text)

        # Ensure no generic replacement like "technology presentation smartphone" without entities
        for q in eq.primary_queries:
            q_lower = q.lower()
            self.assertTrue("steve jobs" in q_lower or "iphone" in q_lower)

        # 3. Provider Routing: Pexafy must be DISABLED
        pexafy = MockProvider("pexafy")
        wikimedia = MockProvider("wikimedia")
        ia = MockProvider("internet_archive")
        finder = MediaFinder(providers=[pexafy, wikimedia, ia], ranker=self.ranker)

        routed = finder._route_providers(era="historical", media="video", visual_requirement=REAL_REQUIRED)
        routed_names = [p.PROVIDER_NAME for p in routed]
        self.assertNotIn("pexafy", routed_names)
        self.assertIn("internet_archive", routed_names)

    # --------------------------------------------------------------------------
    # TEST 2: D-Day 6 June 1944 Normandy
    # --------------------------------------------------------------------------
    def test_2_d_day_1944_normandy(self):
        """
        Input: 'Pada 6 Juni 1944, pasukan Sekutu mendarat di Normandia.'
        Expected:
        - Requirement: REAL_REQUIRED
        - visual_type: EVENT
        - era: historical
        - Provider priority: Internet Archive, Wikimedia. Pexafy DISABLED.
        """
        text = "Pada 6 Juni 1944, pasukan Sekutu mendarat di Normandia."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, REAL_REQUIRED)
        self.assertEqual(v_type, "EVENT")
        self.assertEqual(s_role, PRIMARY_EVIDENCE)

        ent_names = [e["name"] for e in entities]
        self.assertTrue(any("Normandia" in e or "Normandy" in e for e in ent_names))
        self.assertTrue(any("1944" in e for e in ent_names))

        pexafy = MockProvider("pexafy")
        wikimedia = MockProvider("wikimedia")
        ia = MockProvider("internet_archive")
        finder = MediaFinder(providers=[pexafy, wikimedia, ia], ranker=self.ranker)

        routed = finder._route_providers(era="historical", media="video", visual_requirement=REAL_REQUIRED)
        routed_names = [p.PROVIDER_NAME for p in routed]

        self.assertNotIn("pexafy", routed_names)
        self.assertEqual(routed_names[0], "internet_archive")
        self.assertEqual(routed_names[1], "wikimedia")

    # --------------------------------------------------------------------------
    # TEST 3: Pagi hari, kota mulai bergerak
    # --------------------------------------------------------------------------
    def test_3_pagi_hari_kota_bergerak(self):
        """
        Input: 'Pagi hari, kota mulai bergerak.'
        Expected:
        - Requirement: GENERIC_ALLOWED
        - Pexafy is ALLOWED
        """
        text = "Pagi hari, kota mulai bergerak."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, GENERIC_ALLOWED)
        self.assertEqual(s_role, GENERIC_ATMOSPHERE)

        pexafy = MockProvider("pexafy")
        wikimedia = MockProvider("wikimedia")
        ia = MockProvider("internet_archive")
        finder = MediaFinder(providers=[pexafy, wikimedia, ia], ranker=self.ranker)

        routed = finder._route_providers(era="present", media="photo", visual_requirement=GENERIC_ALLOWED)
        routed_names = [p.PROVIDER_NAME for p in routed]
        self.assertIn("pexafy", routed_names)

    # --------------------------------------------------------------------------
    # TEST 4: Tapi di sinilah semuanya berubah (NO_BROLL)
    # --------------------------------------------------------------------------
    def test_4_tapi_di_sinilah_semuanya_berubah(self):
        """
        Input: 'Tapi di sinilah semuanya berubah.'
        Expected:
        - Requirement: NO_BROLL
        - Zero media search calls made
        """
        text = "Tapi di sinilah semuanya berubah."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, NO_BROLL)
        self.assertEqual(s_role, NO_VISUAL)

        pexafy = MockProvider("pexafy")
        wikimedia = MockProvider("wikimedia")
        ia = MockProvider("internet_archive")
        finder = MediaFinder(providers=[pexafy, wikimedia, ia], ranker=self.ranker)

        result = finder.find(request=text)
        self.assertEqual(result.status, "NO_BROLL")
        self.assertEqual(result.usable_results, 0)
        self.assertEqual(len(result.results), 0)
        self.assertEqual(len(result.queries), 0)
        # Ensure none of the providers were queried
        self.assertEqual(len(pexafy.searches), 0)
        self.assertEqual(len(wikimedia.searches), 0)
        self.assertEqual(len(ia.searches), 0)

    # --------------------------------------------------------------------------
    # TEST 5: Populasi Tokyo meningkat (REMOTION_REQUIRED)
    # --------------------------------------------------------------------------
    def test_5_populasi_tokyo_meningkat(self):
        """
        Input: 'Populasi Tokyo meningkat dari 3 juta menjadi lebih dari 10 juta.'
        Expected:
        - Requirement: REMOTION_REQUIRED
        - visual_type = STATISTIC
        - motion_spec generated
        - Zero media provider calls
        """
        text = "Populasi Tokyo meningkat dari 3 juta menjadi lebih dari 10 juta."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, REMOTION_REQUIRED)
        self.assertEqual(v_type, "STATISTIC")
        self.assertIsNotNone(motion_spec)
        self.assertEqual(s_role, MOTION_GRAPHICS)

        pexafy = MockProvider("pexafy")
        wikimedia = MockProvider("wikimedia")
        finder = MediaFinder(providers=[pexafy, wikimedia], ranker=self.ranker)

        result = finder.find(request=text)
        self.assertEqual(result.status, "REMOTION_REQUIRED")
        self.assertEqual(result.usable_results, 0)
        self.assertEqual(len(result.results), 0)
        self.assertIsNotNone(result.motion_spec)
        self.assertEqual(len(pexafy.searches), 0)
        self.assertEqual(len(wikimedia.searches), 0)

    # --------------------------------------------------------------------------
    # TEST 6: Jakarta awal abad ke-20
    # --------------------------------------------------------------------------
    def test_6_jakarta_awal_abad_20(self):
        """
        Input: 'Pada awal abad ke-20, Jakarta masih sangat berbeda.'
        Expected:
        - Requirement: REAL_PREFERRED
        - Historical context requiring genuine Batavia/Jakarta visuals if available
        """
        text = "Pada awal abad ke-20, Jakarta masih sangat berbeda."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, REAL_PREFERRED)
        self.assertEqual(s_role, DIRECT_CONTEXT)
        ent_names = [e["name"] for e in entities]
        self.assertTrue(any("Jakarta" in e for e in ent_names))

    # --------------------------------------------------------------------------
    # TEST 7: Harga rumah meningkat dua kali lipat dalam 20 tahun
    # --------------------------------------------------------------------------
    def test_7_harga_rumah_meningkat(self):
        """
        Input: 'Harga rumah meningkat dua kali lipat dalam 20 tahun.'
        Expected:
        - Requirement: REMOTION_REQUIRED
        - Not generic house stock footage
        """
        text = "Harga rumah meningkat dua kali lipat dalam 20 tahun."

        req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        self.assertEqual(req, REMOTION_REQUIRED)
        self.assertEqual(v_type, "STATISTIC")
        self.assertIsNotNone(motion_spec)

    # --------------------------------------------------------------------------
    # TEST 8: Hard Gate — Generic candidate cannot beat exact candidate
    # --------------------------------------------------------------------------
    def test_8_hard_gate_generic_vs_authentic(self):
        """
        Under REAL_REQUIRED:
        - Candidate A (Authentic): 'D-Day Normandy Landing 1944'
        - Candidate B (Generic): 'Soldiers on beach'
        Even if Candidate B is given a higher initial embedding similarity,
        Candidate A must rank #1 and Candidate B must be rejected/gated.
        """
        item_authentic = make_item(
            provider="internet_archive",
            title="D-Day Normandy Landing 1944",
            description="Allied forces landing on Normandy beaches on 6 June 1944",
            media_type="video",
            date="1944-06-06",
            url="https://archive.org/d-day-1944.mp4",
        )
        item_authentic.embedding_similarity = 0.70  # Lower initial embedding
        item_authentic.reranker_score = 0.72

        item_generic = make_item(
            provider="pexafy",
            title="Soldiers on beach",
            description="Military soldiers near ocean sunset cinematic",
            media_type="video",
            date="2022",
            url="https://example.com/soldiers-beach.mp4",
        )
        item_generic.embedding_similarity = 0.95  # Artificially high semantic similarity
        item_generic.reranker_score = 0.94

        ranked, _ = self.ranker.rank(
            original_request="D-Day Normandy 1944",
            candidates=[item_generic, item_authentic],
            entities=["D-Day", "Normandy", "1944"],
            visual_requirement=REAL_REQUIRED,
            era="historical",
        )

        # Authentic candidate must win #1
        self.assertEqual(ranked[0].title, "D-Day Normandy Landing 1944")
        self.assertGreater(ranked[0].authenticity_score, 0.7)
        self.assertFalse(bool(ranked[0].rejection_reason))

        # Generic candidate must be penalized/rejected by the hard gate
        self.assertTrue(bool(item_generic.rejection_reason))
        self.assertIn("hard gate", item_generic.rejection_reason.lower())
        self.assertEqual(len(ranked), 1)

    # --------------------------------------------------------------------------
    # TEST 9: Insufficient evidence status
    # --------------------------------------------------------------------------
    def test_9_insufficient_evidence_status(self):
        """
        When only generic candidates are returned for REAL_REQUIRED:
        - System outputs status='INSUFFICIENT_EVIDENCE'
        - usable_results=0
        - fallback_allowed=False
        """
        generic_item = make_item(
            provider="internet_archive",
            title="Random soldiers marching in forest",
            description="Troops marching in woodland area",
            media_type="video",
            date="2010",
            url="https://archive.org/troops-forest.mp4",
        )
        ia_provider = MockProvider("internet_archive", [generic_item])
        finder = MediaFinder(providers=[ia_provider], ranker=self.ranker)

        result = finder.find(
            request="Steve Jobs memperkenalkan iPhone pada 2007",
            visual_requirement=REAL_REQUIRED,
        )

        self.assertEqual(result.visual_requirement, REAL_REQUIRED)
        self.assertEqual(result.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.usable_results, 0)
        self.assertFalse(result.fallback_allowed)
        self.assertEqual(len(result.results), 0)

    # --------------------------------------------------------------------------
    # TEST 10: Downloader skips rejected items & applies evidence naming
    # --------------------------------------------------------------------------
    def test_10_downloader_evidence_behavior(self):
        """
        Downloader must:
        - Skip items with rejection_reason under REAL_REQUIRED
        - Use evidence naming format: 001_REAL_REQUIRED_<title>.ext
        """
        downloader = MediaDownloader()

        # Filename helper test with visual_requirement tag
        safe_name = downloader._safe_filename(
            title="D-Day Normandy 1944",
            ext=".mp4",
            index=1,
            visual_requirement=REAL_REQUIRED,
        )
        self.assertTrue(safe_name.startswith("001_REAL_REQUIRED_"))
        self.assertTrue(safe_name.endswith(".mp4"))
        self.assertIn("d-day-normandy-1944", safe_name)

        # Rejected item skip test
        rejected_item = make_item(
            provider="internet_archive",
            title="Generic Soldiers",
            url="https://archive.org/gen.mp4",
        )
        rejected_item.visual_requirement = REAL_REQUIRED
        rejected_item.rejection_reason = "REAL_REQUIRED hard gate: 0 entity matches"

        # Attempt download of rejected item
        download_result = downloader._download_item(rejected_item, Path("/tmp"), 1)
        self.assertIsNone(download_result)

    # --------------------------------------------------------------------------
    # TEST 11: Result preview displays evidence metadata
    # --------------------------------------------------------------------------
    def test_11_preview_displays_evidence_metadata(self):
        """
        MediaFinderResult.preview() must display:
        - [REAL_REQUIRED] [PRIMARY_EVIDENCE]
        - Event Match, Entity Match, Authenticity scores
        """
        item = MediaFinderItem(
            rank=1,
            title="D-Day Normandy Landing 1944",
            provider="internet_archive",
            media_type="video",
            score=0.95,
            source_url="https://archive.org/details/dday1944",
            download_url="https://archive.org/download/dday1944.mp4",
            visual_requirement=REAL_REQUIRED,
            source_role=PRIMARY_EVIDENCE,
            authenticity_score=0.94,
            entity_match_score=0.98,
            event_match_score=0.97,
            matched_entities=["D-Day", "Normandy", "1944"],
        )
        result = MediaFinderResult(
            request="D-Day Normandy 1944",
            media_type="video",
            era="historical",
            style="archival",
            queries=["D-Day Normandy 1944 archival footage"],
            providers_contacted=["internet_archive"],
            results=[item],
            total_candidates_found=1,
            visual_requirement=REAL_REQUIRED,
            source_role=PRIMARY_EVIDENCE,
            status="OK",
            usable_results=1,
        )
        preview_text = result.preview()
        self.assertIn("[REAL_REQUIRED] [PRIMARY_EVIDENCE]", preview_text)
        self.assertIn("Event Match: 0.97", preview_text)
        self.assertIn("Entity Match: 0.98", preview_text)
        self.assertIn("Authenticity: 0.94", preview_text)

    # --------------------------------------------------------------------------
    # TEST 12: Microbeat evidence integration
    # --------------------------------------------------------------------------
    def test_12_microbeat_evidence_integration(self):
        """
        find_from_microbeat accepts visual_requirement, entities, source_role.
        """
        authentic_item = make_item(
            provider="internet_archive",
            title="Apollo 11 Moon Landing 1969",
            description="Neil Armstrong Apollo 11 lunar module landing on the Moon July 1969",
            media_type="video",
            date="1969-07-20",
            url="https://archive.org/apollo11.mp4",
        )
        ia_provider = MockProvider("internet_archive", [authentic_item])
        finder = MediaFinder(providers=[ia_provider], ranker=self.ranker)

        microbeat = {
            "visual_concept": "Apollo 11 mendarat di bulan",
            "search_query": "Apollo 11 Moon Landing 1969",
            "preferred_media_type": "video",
            "era": "historical",
            "visual_requirement": REAL_REQUIRED,
            "visual_type": "EVENT",
            "entities": ["Apollo 11", "Moon", "1969"],
            "source_role": PRIMARY_EVIDENCE,
        }

        result = finder.find_from_microbeat(microbeat)
        self.assertEqual(result.visual_requirement, REAL_REQUIRED)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.usable_results, 1)
        self.assertEqual(result.results[0].title, "Apollo 11 Moon Landing 1969")


if __name__ == "__main__":
    unittest.main()
