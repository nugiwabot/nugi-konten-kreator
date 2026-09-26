"""
tests/test_media_query_expander.py
====================================
Unit tests for MediaQueryExpander.
No external dependencies — fully offline.
"""

import unittest
from engine.pipeline.media_query_expander import MediaQueryExpander, ExpandedQuery


class TestMediaQueryExpander(unittest.TestCase):

    def setUp(self):
        self.expander = MediaQueryExpander()

    # ------------------------------------------------------------------
    # Media type detection
    # ------------------------------------------------------------------

    def test_detect_video_type_from_footage(self):
        eq = self.expander.expand("cari footage D-Day 1944")
        self.assertEqual(eq.detected_media_type, "video")

    def test_detect_video_type_from_video(self):
        eq = self.expander.expand("cari video suasana New York 1950an")
        self.assertEqual(eq.detected_media_type, "video")

    def test_detect_image_type_from_foto(self):
        eq = self.expander.expand("cari foto Albert Einstein")
        self.assertEqual(eq.detected_media_type, "image")

    def test_detect_image_type_from_gambar(self):
        eq = self.expander.expand("cari gambar Napoleon Bonaparte")
        self.assertEqual(eq.detected_media_type, "image")

    def test_detect_any_type_from_visual(self):
        eq = self.expander.expand("cari visual untuk video tentang revolusi industri")
        # "visual" alone → "any"
        self.assertIn(eq.detected_media_type, ["any", "image", "video"])

    def test_detect_any_when_no_cues(self):
        eq = self.expander.expand("D-Day Normandy landing 1944")
        self.assertIn(eq.detected_media_type, ["any", "image", "video"])

    # ------------------------------------------------------------------
    # Historical detection
    # ------------------------------------------------------------------

    def test_historical_detected_from_year(self):
        eq = self.expander.expand("foto tentara sekutu 1944")
        self.assertTrue(eq.is_historical)
        self.assertEqual(eq.year_hint, "1944")

    def test_historical_detected_from_keyword_asli(self):
        eq = self.expander.expand("cari foto asli Albert Einstein")
        self.assertTrue(eq.is_historical)

    def test_historical_detected_from_archival_keyword(self):
        eq = self.expander.expand("archival footage World War II")
        self.assertTrue(eq.is_historical)

    def test_not_historical_for_modern_query(self):
        eq = self.expander.expand("orang sedang bekerja di kantor modern")
        self.assertFalse(eq.is_historical)

    def test_year_hint_extracted_correctly(self):
        eq = self.expander.expand("footage Bandung 1950")
        self.assertEqual(eq.year_hint, "1950")

    # ------------------------------------------------------------------
    # Query generation
    # ------------------------------------------------------------------

    def test_primary_queries_not_empty(self):
        eq = self.expander.expand("Albert Einstein portrait")
        self.assertGreater(len(eq.primary_queries), 0)

    def test_expanded_queries_not_empty(self):
        eq = self.expander.expand("Albert Einstein portrait 1921")
        self.assertGreater(len(eq.expanded_queries), 0)

    def test_all_queries_deduplicated(self):
        eq = self.expander.expand("D-Day Normandy 1944 historical footage")
        # No duplicates in all_queries
        self.assertEqual(len(eq.all_queries), len(set(eq.all_queries)))

    def test_all_queries_non_empty_strings(self):
        eq = self.expander.expand("World War II soldiers")
        for q in eq.all_queries:
            self.assertIsInstance(q, str)
            self.assertGreater(len(q.strip()), 0)

    def test_year_included_in_primary_query(self):
        eq = self.expander.expand("tentara sekutu mendarat 1944")
        # At least one primary query should contain the year
        has_year = any("1944" in q for q in eq.primary_queries)
        self.assertTrue(has_year)

    def test_empty_request_returns_empty_queries(self):
        eq = self.expander.expand("")
        self.assertEqual(eq.all_queries, [])
        self.assertEqual(eq.detected_media_type, "any")

    def test_whitespace_only_request_returns_empty(self):
        eq = self.expander.expand("   ")
        self.assertEqual(eq.all_queries, [])

    def test_media_type_override(self):
        eq = self.expander.expand("Albert Einstein", media_type_override="video")
        self.assertEqual(eq.detected_media_type, "video")

    # ------------------------------------------------------------------
    # Abstract / conceptual queries
    # ------------------------------------------------------------------

    def test_abstract_concept_kesepian(self):
        eq = self.expander.expand("cari foto orang kesepian di keramaian")
        self.assertGreater(len(eq.all_queries), 0)
        # Should include loneliness/crowd related queries
        all_q_combined = " ".join(eq.all_queries).lower()
        self.assertTrue(
            any(w in all_q_combined for w in ["lonely", "loneliness", "crowd", "alone"])
        )

    def test_generic_query_any_topic(self):
        """The expander must handle any topic, not just hardcoded ones."""
        random_topics = [
            "quantum computing laboratory",
            "seorang atlit berlari marathon",
            "jembatan emas San Francisco",
            "gajah di savanna Afrika",
            "konser musik klasik di Vienna",
        ]
        for topic in random_topics:
            eq = self.expander.expand(topic)
            self.assertGreater(len(eq.all_queries), 0, f"No queries for topic: {topic}")

    # ------------------------------------------------------------------
    # Script-to-visual mode
    # ------------------------------------------------------------------

    def test_expand_script_returns_list(self):
        script = """
        Pada tanggal 6 Juni 1944, ribuan tentara Sekutu mendarat di pantai Normandy.
        
        Operasi D-Day adalah salah satu operasi militer terbesar dalam sejarah.
        
        Pasukan Amerika mendarat di Omaha Beach sementara Inggris dan Kanada di Gold Beach.
        """
        results = self.expander.expand_script(script)
        self.assertIsInstance(results, list)
        # Should detect at least some scenes
        self.assertGreater(len(results), 0)

    def test_expand_script_each_result_has_queries(self):
        script = """
        Para tentara Soviet mengepung Berlin pada April 1945.
        
        Perang Dunia Kedua berakhir dengan penyerahan Jerman pada Mei 1945.
        """
        results = self.expander.expand_script(script)
        for eq in results:
            self.assertIsInstance(eq, ExpandedQuery)
            self.assertTrue(eq.is_script_mode)
            self.assertGreater(len(eq.all_queries), 0)

    def test_expand_script_empty_text(self):
        results = self.expander.expand_script("")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
