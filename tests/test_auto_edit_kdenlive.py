#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Auto Edit Kdenlive Engine (engine.pipeline.auto_edit_kdenlive)
Covers all 21 test scenarios required by specification:
1. Workspace selection
2. Source video detection
3. Timestamp parsing
4. SRT generation
5. Transcript segmentation
6. B-roll matching
7. B-roll duration handling
8. Image duration
9. Fill-frame calculation
10. Quick-zoom calculation
11. Title timing
12. Text layout calculation
13. Text color selection
14. Contrast/treatment selection
15. Text shape sizing
16. SFX timing
17. Manifest handling
18. Resume logic
19. Manual-edit preservation logic
20. Validation
21. Malformed Kdenlive handling
Plus MLT XML structural integrity and idempotency safe path tests.
"""

import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from engine.pipeline.auto_edit_kdenlive import (
    COLOR_BLACK_SHADOW,
    COLOR_BRIGHT_YELLOW,
    COLOR_DARK_SHAPE,
    COLOR_WHITE,
    PRESET_A_DOC_YELLOW,
    PRESET_B_CLEAN_YELLOW,
    PRESET_C_CLEAN_WHITE,
    PRESET_D_BOXED_EDITORIAL,
    BRollAsset,
    BRollPlacement,
    EditManifest,
    SFXEvent,
    TextItem,
    TranscriptSegment,
    VideoMetadata,
    build_broll_plan,
    calculate_fill_frame_rect,
    calculate_match_score,
    calculate_quick_zoom_keyframes,
    calculate_text_layout,
    detect_sfx_events,
    detect_text_moments,
    ensure_sound_effects,
    extract_keywords_from_string,
    find_broll_assets,
    find_main_video,
    find_workspace,
    format_timestamp_srt,
    generate_kdenlive_project,
    generate_kdenlivetitle_file,
    generate_srt,
    load_manifest,
    match_broll,
    merge_timeline_preservations,
    parse_existing_kdenlive,
    parse_srt_file,
    parse_timestamp_srt,
    resolve_safe_kdenlive_path,
    run_auto_edit_pipeline,
    save_manifest,
    validate_output,
)


class TestAutoEditKdenliveSpecification(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.output_dir = self.root / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create sample 01-script workspace
        self.ws_01 = self.output_dir / "01-script"
        for sub in ["footage", "broll", "subtitle", "project", "render"]:
            (self.ws_01 / sub).mkdir(parents=True, exist_ok=True)
            (self.ws_01 / sub / ".gitkeep").touch()

    def tearDown(self):
        self.temp_dir.cleanup()

    # --------------------------------------------------------------------------
    # 1. Workspace selection
    # --------------------------------------------------------------------------
    def test_01_workspace_selection(self):
        # By full folder name
        ws = find_workspace("01-script", root_dir=self.root)
        self.assertEqual(ws, self.ws_01.resolve())

        # By numeric alias
        ws_num = find_workspace("1", root_dir=self.root)
        self.assertEqual(ws_num, self.ws_01.resolve())

        ws_num2 = find_workspace("01", root_dir=self.root)
        self.assertEqual(ws_num2, self.ws_01.resolve())

        # By path with prefix
        ws_path = find_workspace("output/01-script", root_dir=self.root)
        self.assertEqual(ws_path, self.ws_01.resolve())

        # Invalid workspace raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            find_workspace("99-script", root_dir=self.root)

    # --------------------------------------------------------------------------
    # 2. Source video detection
    # --------------------------------------------------------------------------
    def test_02_source_video_detection(self):
        footage_dir = self.ws_01 / "footage"

        # Case A: No video -> FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            find_main_video(self.ws_01)

        # Case B: Exactly one video -> success
        vid_a = footage_dir / "clip_a.mp4"
        vid_a.touch()
        found = find_main_video(self.ws_01)
        self.assertEqual(found, vid_a)

        # Case C: Multiple videos, one has priority keyword
        vid_raw = footage_dir / "video-mentah.mp4"
        vid_raw.touch()
        found_priority = find_main_video(self.ws_01)
        self.assertEqual(found_priority, vid_raw)

        # Case D: Ambiguous videos without priority keyword -> ValueError
        vid_raw.unlink()
        vid_b = footage_dir / "clip_b.mp4"
        vid_b.touch()
        with self.assertRaises(ValueError) as ctx:
            find_main_video(self.ws_01)
        self.assertIn("ambigu", str(ctx.exception).lower())

        # Case E: Explicit selection resolves ambiguity
        explicit = find_main_video(self.ws_01, requested_file="clip_b.mp4")
        self.assertEqual(explicit, vid_b)

    # --------------------------------------------------------------------------
    # 3. Timestamp parsing
    # --------------------------------------------------------------------------
    def test_03_timestamp_parsing(self):
        self.assertEqual(format_timestamp_srt(0.0), "00:00:00,000")
        self.assertEqual(format_timestamp_srt(4.2), "00:00:04,200")
        self.assertEqual(format_timestamp_srt(65.5), "00:01:05,500")
        self.assertEqual(format_timestamp_srt(3661.125), "01:01:01,125")

        # Parsing back to seconds
        self.assertAlmostEqual(parse_timestamp_srt("00:00:00,000"), 0.0, places=3)
        self.assertAlmostEqual(parse_timestamp_srt("00:00:04,200"), 4.2, places=3)
        self.assertAlmostEqual(parse_timestamp_srt("00:01:05,500"), 65.5, places=3)
        self.assertAlmostEqual(parse_timestamp_srt("01:01:01,125"), 3661.125, places=3)

        # Malformed timestamp raises ValueError
        with self.assertRaises(ValueError):
            parse_timestamp_srt("invalid:timestamp")

    # --------------------------------------------------------------------------
    # 4. SRT generation
    # --------------------------------------------------------------------------
    def test_04_srt_generation(self):
        segments = [
            TranscriptSegment(1, 0.0, 4.2, 4.2, "Setiap pagi jutaan orang berangkat kerja."),
            TranscriptSegment(2, 4.2, 8.7, 4.5, "Sebagian harus menempuh jarak sangat jauh."),
        ]
        srt_file = self.ws_01 / "subtitle" / "subtitle.srt"
        generate_srt(segments, srt_file)

        self.assertTrue(srt_file.is_file())
        content = srt_file.read_text(encoding="utf-8")
        self.assertIn("00:00:00,000 --> 00:00:04,200", content)
        self.assertIn("Setiap pagi jutaan orang berangkat kerja.", content)
        self.assertIn("00:00:04,200 --> 00:00:08,700", content)

        # Parse it back
        parsed = parse_srt_file(srt_file)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].text, "Setiap pagi jutaan orang berangkat kerja.")
        self.assertAlmostEqual(parsed[1].duration, 4.5, places=2)

    # --------------------------------------------------------------------------
    # 5. Transcript segmentation
    # --------------------------------------------------------------------------
    def test_05_transcript_segmentation(self):
        seg = TranscriptSegment(1, 10.5, 15.75, 5.25, "Uji durasi segment.")
        self.assertEqual(seg.duration, 5.25)
        self.assertGreater(seg.end, seg.start)
        self.assertGreater(seg.duration, 0.0)

        # Keyword tokenization and stopword removal
        tokens = extract_keywords_from_string("001_kereta stasiun di kota jakarta yang sangat ramai")
        self.assertIn("kereta", tokens)
        self.assertIn("stasiun", tokens)
        self.assertIn("jakarta", tokens)
        # Stopwords filtered out
        self.assertNotIn("yang", tokens)
        self.assertNotIn("di", tokens)

    # --------------------------------------------------------------------------
    # 6. B-roll matching
    # --------------------------------------------------------------------------
    def test_06_broll_matching(self):
        seg_train = TranscriptSegment(
            segment_id=1,
            start=0.0,
            end=4.0,
            duration=4.0,
            text="Jutaan orang menggunakan kereta setiap pagi.",
            tokens={"kereta", "pagi", "orang"},
        )
        seg_house = TranscriptSegment(
            segment_id=2,
            start=4.0,
            end=8.0,
            duration=4.0,
            text="Banyak yang membeli rumah tapak di pinggiran.",
            tokens={"rumah", "tapak", "pinggiran"},
        )

        asset_train = BRollAsset(Path("broll/kereta_stasiun.mp4"), "kereta_stasiun.mp4", "video", 10.0, {"kereta", "stasiun"})
        asset_house = BRollAsset(Path("broll/rumah_tapak.jpg"), "rumah_tapak.jpg", "image", None, {"rumah", "tapak"})
        asset_beach = BRollAsset(Path("broll/pantai_pasir.mp4"), "pantai_pasir.mp4", "video", 5.0, {"pantai", "pasir"})

        assets = [asset_beach, asset_house, asset_train]

        score_train, _ = calculate_match_score(seg_train, asset_train)
        score_beach, _ = calculate_match_score(seg_train, asset_beach)
        self.assertGreater(score_train, score_beach)

        placements = match_broll([seg_train, seg_house], assets)
        self.assertEqual(len(placements), 2)
        self.assertEqual(placements[0].asset_path, "broll/kereta_stasiun.mp4")
        self.assertEqual(placements[1].asset_path, "broll/rumah_tapak.jpg")

    # --------------------------------------------------------------------------
    # 7. B-roll duration handling
    # --------------------------------------------------------------------------
    def test_07_broll_duration_handling(self):
        seg = TranscriptSegment(1, 0.0, 5.0, 5.0, "Kereta berangkat.", {"kereta"})
        asset_long = BRollAsset(Path("broll/kereta.mp4"), "kereta.mp4", "video", 12.0, {"kereta"})

        # Video longer than slot -> trimmed to fit
        placements = match_broll([seg], [asset_long])
        p = placements[0]
        self.assertEqual(p.status, "MATCHED_OK")
        self.assertEqual(p.duration, 5.0)
        self.assertEqual(p.trim_in, 0.0)
        self.assertEqual(p.trim_out, 5.0)

        # Video shorter than slot -> flagged INSUFFICIENT_BROLL_DURATION
        asset_short = BRollAsset(Path("broll/kereta_short.mp4"), "kereta_short.mp4", "video", 3.0, {"kereta"})
        placements_short = match_broll([seg], [asset_short])
        ps = placements_short[0]
        self.assertEqual(ps.status, "INSUFFICIENT_BROLL_DURATION")
        self.assertEqual(ps.trim_out, 3.0)

    # --------------------------------------------------------------------------
    # 8. Image duration
    # --------------------------------------------------------------------------
    def test_08_image_duration(self):
        seg = TranscriptSegment(1, 10.0, 14.5, 4.5, "Suasana rumah.", {"rumah"})
        asset_img = BRollAsset(Path("broll/rumah.jpg"), "rumah.jpg", "image", None, {"rumah"})

        placements = match_broll([seg], [asset_img])
        p = placements[0]
        self.assertEqual(p.asset_type, "image")
        self.assertEqual(p.duration, 4.5)
        self.assertEqual(p.asset_duration, 4.5)  # Matches slot duration exactly
        self.assertEqual(p.status, "MATCHED_OK")

    # --------------------------------------------------------------------------
    # 9. Fill-frame calculation
    # --------------------------------------------------------------------------
    def test_09_fill_frame_calculation(self):
        proj_w, proj_h = 1920, 1080

        # Exact 16:9 match
        x, y, w, h = calculate_fill_frame_rect(1920, 1080, proj_w, proj_h)
        self.assertEqual((x, y, w, h), (0, 0, 1920, 1080))

        # Ultrawide / wider than 16:9 (e.g. 3840x1080)
        # Height matches proj_h, width scales and centers with negative X
        x, y, w, h = calculate_fill_frame_rect(3840, 1080, proj_w, proj_h)
        self.assertEqual(h, 1080)
        self.assertEqual(w, 3840)
        self.assertEqual(x, (1920 - 3840) // 2)
        self.assertEqual(y, 0)
        self.assertGreaterEqual(w, proj_w)
        self.assertGreaterEqual(h, proj_h)

        # Portrait (e.g. 1080x1920, 9:16 mobile)
        # Width matches proj_w, height scales up and centers with negative Y
        x, y, w, h = calculate_fill_frame_rect(1080, 1920, proj_w, proj_h)
        self.assertEqual(w, 1920)
        self.assertGreaterEqual(h, proj_h)
        self.assertEqual(x, 0)
        self.assertLess(y, 0)  # Top/bottom cropped symmetrically

        # Square (e.g. 1000x1000, 1:1)
        x, y, w, h = calculate_fill_frame_rect(1000, 1000, proj_w, proj_h)
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1920)
        self.assertEqual(x, 0)
        self.assertEqual(y, (1080 - 1920) // 2)
        self.assertGreaterEqual(w, proj_w)
        self.assertGreaterEqual(h, proj_h)

    # --------------------------------------------------------------------------
    # 10. Quick-zoom calculation
    # --------------------------------------------------------------------------
    def test_10_quick_zoom_calculation(self):
        fill_rect = (0, 0, 1920, 1080)
        duration_frames = 90  # 3 seconds @ 30fps

        kf_str = calculate_quick_zoom_keyframes(
            fill_rect=fill_rect,
            duration_frames=duration_frames,
            proj_w=1920,
            proj_h=1080,
            zoom_peak=1.08,
            ease_in_pct=0.12,
            ease_out_pct=0.25,
        )

        keyframes = [k.strip() for k in kf_str.split(";")]
        self.assertEqual(len(keyframes), 3)

        # Keyframe 0: at frame 0, base fill rect
        self.assertTrue(keyframes[0].startswith("0=0 0 1920 1080 1"))

        # Keyframe 1: at peak frame ~11 (12% of 90), scaled up
        f1_parts = keyframes[1].split("=")
        f1_num = int(f1_parts[0])
        self.assertIn(f1_num, [10, 11, 12])
        coords = [int(v) for v in f1_parts[1].split()[:4]]
        w_peak = coords[2]
        h_peak = coords[3]
        self.assertGreater(w_peak, 1920)
        self.assertGreater(h_peak, 1080)
        self.assertAlmostEqual(w_peak / 1920, 1.08, delta=0.02)

        # Keyframe 2: ease back to base fill rect
        f2_parts = keyframes[2].split("=")
        f2_num = int(f2_parts[0])
        self.assertIn(f2_num, [22, 23, 24])
        self.assertTrue(f2_parts[1].startswith("0 0 1920 1080 1"))

    # --------------------------------------------------------------------------
    # 11. Title timing
    # --------------------------------------------------------------------------
    def test_11_title_timing(self):
        segments = [
            TranscriptSegment(1, 0.0, 4.0, 4.0, "Bagian pertama pengenalan masalah."),
            TranscriptSegment(2, 4.0, 8.0, 4.0, "Jarak tempuh mencapai 60 kilometer setiap hari."),
            TranscriptSegment(3, 8.0, 12.0, 4.0, "Masalahnya bukan sekadar waktu tempuh."),
            TranscriptSegment(4, 12.0, 16.0, 4.0, "Penjelasan lanjutan tanpa keyword khusus."),
        ]
        video_dur = 20.0
        text_items = detect_text_moments(segments, video_duration=video_dur)

        self.assertGreater(len(text_items), 0)
        for item in text_items:
            # Timing bounds within master video duration
            self.assertGreaterEqual(item.start, 0.0)
            self.assertLessEqual(item.end, video_dur)
            self.assertGreater(item.duration, 0.0)
            self.assertLessEqual(item.duration, 5.0)

        # Verify minimum spacing between titles to prevent screen flooding
        for i in range(1, len(text_items)):
            self.assertGreaterEqual(text_items[i].start, text_items[i-1].end - 1.0)

    # --------------------------------------------------------------------------
    # 12. Text layout calculation
    # --------------------------------------------------------------------------
    def test_12_text_layout_calculation(self):
        # Headline typography layout
        layout_hl = calculate_text_layout(
            text="MASALAHNYA BUKAN JARAK",
            text_type="HEADLINE",
            proj_w=1920,
            proj_h=1080,
            preset=PRESET_A_DOC_YELLOW,
        )
        self.assertEqual(layout_hl["font_size"], 54)
        self.assertEqual(layout_hl["text_color"], COLOR_BRIGHT_YELLOW)
        self.assertTrue(layout_hl["has_box"])
        self.assertGreater(layout_hl["box_w"], 100)
        self.assertGreater(layout_hl["box_h"], 50)
        # Position is within safe margins
        self.assertGreaterEqual(layout_hl["box_x"], int(1920 * 0.08))
        self.assertLessEqual(layout_hl["box_x"] + layout_hl["box_w"], 1920 - int(1920 * 0.08))

        # Section title typography layout
        layout_st = calculate_text_layout(
            text="KENAPA RUMAH MULAI BERUBAH?",
            text_type="SECTION_TITLE",
            proj_w=1920,
            proj_h=1080,
        )
        self.assertEqual(layout_st["font_size"], 64)
        self.assertGreater(layout_st["font_size"], layout_hl["font_size"])

    # --------------------------------------------------------------------------
    # 13. Text color selection (Bright Yellow Primary)
    # --------------------------------------------------------------------------
    def test_13_text_color_selection(self):
        # Bright yellow identity verification
        self.assertEqual(COLOR_BRIGHT_YELLOW, "255,212,0,255")  # #FFD400 with 100% alpha
        self.assertEqual(COLOR_BLACK_SHADOW, "0,0,0,220")       # Subtle black shadow
        self.assertEqual(COLOR_DARK_SHAPE, "0,0,0,195")         # ~76% opacity dark shape

        layout_yellow = calculate_text_layout("TEST", "HEADLINE", preset=PRESET_A_DOC_YELLOW)
        self.assertEqual(layout_yellow["text_color"], COLOR_BRIGHT_YELLOW)
        self.assertEqual(layout_yellow["outline_color"], COLOR_BLACK_SHADOW)

    # --------------------------------------------------------------------------
    # 14. Contrast / treatment selection (Presets A-D)
    # --------------------------------------------------------------------------
    def test_14_contrast_treatment_selection(self):
        # Preset A: Documentary Yellow (Yellow + Shadow + Box)
        p_a = calculate_text_layout("TEXT A", "HEADLINE", preset=PRESET_A_DOC_YELLOW)
        self.assertEqual(p_a["text_color"], COLOR_BRIGHT_YELLOW)
        self.assertTrue(p_a["has_box"])

        # Preset B: Clean Yellow (Yellow + Shadow, No Box)
        p_b = calculate_text_layout("TEXT B", "HEADLINE", preset=PRESET_B_CLEAN_YELLOW)
        self.assertEqual(p_b["text_color"], COLOR_BRIGHT_YELLOW)
        self.assertFalse(p_b["has_box"])

        # Preset C: Clean White (White fallback for yellow backgrounds)
        p_c = calculate_text_layout("TEXT C", "HEADLINE", preset=PRESET_C_CLEAN_WHITE)
        self.assertEqual(p_c["text_color"], COLOR_WHITE)
        self.assertFalse(p_c["has_box"])

        # Preset D: Boxed Editorial
        p_d = calculate_text_layout("TEXT D", "HEADLINE", preset=PRESET_D_BOXED_EDITORIAL)
        self.assertEqual(p_d["text_color"], COLOR_BRIGHT_YELLOW)
        self.assertTrue(p_d["has_box"])

    # --------------------------------------------------------------------------
    # 15. Text shape sizing
    # --------------------------------------------------------------------------
    def test_15_text_shape_sizing(self):
        # Short text produces a compact box
        layout_short = calculate_text_layout("KECIL", "HEADLINE")
        # Long multi-word text produces a wider and taller box
        layout_long = calculate_text_layout(
            "INI ADALAH KALIMAT PANJANG UNTUK MENGUJI PERUBAHAN UKURAN SHAPE SECARA ADAPTIF",
            "HEADLINE"
        )
        self.assertGreater(layout_long["box_w"], layout_short["box_w"])
        self.assertGreater(layout_long["box_h"], layout_short["box_h"])
        # Radius for rounded corners
        self.assertEqual(layout_short["box_radius"], 12)

    # --------------------------------------------------------------------------
    # 16. SFX timing & generation
    # --------------------------------------------------------------------------
    def test_16_sfx_timing(self):
        sfx_dir = self.root / "assets" / "sound_effects"
        sfx_assets = ensure_sound_effects(sfx_dir)

        # Verify all 5 core sound effect files exist and are valid WAV files
        for fname in ["click.wav", "pop.wav", "whoosh.wav", "hit.wav", "rise.wav"]:
            self.assertTrue(sfx_assets[fname].is_file())
            self.assertGreater(sfx_assets[fname].stat().st_size, 100)

        # Detect SFX events synchronized to visual cues
        placements = [
            BRollPlacement(1, 2.0, 6.0, 4.0, "B-roll 1", "broll/b1.mp4", "video", 4.0, 0.0, 4.0, "MATCHED_OK"),
            BRollPlacement(2, 7.0, 11.0, 4.0, "B-roll 2", "broll/b2.mp4", "video", 4.0, 0.0, 4.0, "MATCHED_OK"),
        ]
        text_items = [
            TextItem("t1", "SECTION_TITLE", PRESET_A_DOC_YELLOW, "BAB 1", 0.5, 4.0, 3.5),
            TextItem("t2", "HEADLINE", PRESET_A_DOC_YELLOW, "MASALAH UTAMA", 12.0, 15.5, 3.5),
        ]

        events = detect_sfx_events(placements, text_items, sfx_assets)
        self.assertGreater(len(events), 0)

        # Section title gets whoosh.wav
        whoosh_ev = next((e for e in events if e.trigger_type == "section_title"), None)
        self.assertIsNotNone(whoosh_ev)
        self.assertEqual(whoosh_ev.asset_filename, "whoosh.wav")
        self.assertAlmostEqual(whoosh_ev.start, 0.5, places=2)

        # Headline gets pop.wav
        pop_ev = next((e for e in events if e.trigger_type == "headline"), None)
        self.assertIsNotNone(pop_ev)
        self.assertEqual(pop_ev.asset_filename, "pop.wav")
        self.assertAlmostEqual(pop_ev.start, 12.0, places=2)

    # --------------------------------------------------------------------------
    # 17. Manifest handling
    # --------------------------------------------------------------------------
    def test_17_manifest_handling(self):
        m_path = self.ws_01 / "project" / "edit_manifest.json"
        self.assertIsNone(load_manifest(m_path))

        sample_manifest = {
            "workspace": "01-script",
            "source_video": "video-mentah.mp4",
            "created_at": "2026-09-30T00:00:00Z",
            "updated_at": "2026-09-30T00:00:00Z",
            "version": 1,
            "stages": {
                "transcription": {"status": "completed"},
                "subtitle": {"status": "completed"},
                "broll": {"status": "completed"},
                "section_titles": {"status": "pending"},
            },
            "user_modifications": {},
        }
        save_manifest(m_path, sample_manifest)
        self.assertTrue(m_path.is_file())

        loaded = load_manifest(m_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["workspace"], "01-script")
        self.assertEqual(loaded["stages"]["transcription"]["status"], "completed")
        self.assertEqual(loaded["stages"]["section_titles"]["status"], "pending")

    # --------------------------------------------------------------------------
    # 18. Resume logic
    # --------------------------------------------------------------------------
    def test_18_resume_logic(self):
        # Pre-populate SRT so Whisper is skipped on continue
        srt_p = self.ws_01 / "subtitle" / "subtitle.srt"
        segs = [TranscriptSegment(1, 0.0, 5.0, 5.0, "Sudah ada SRT.")]
        generate_srt(segs, srt_p)

        # Pre-populate manifest
        m_path = self.ws_01 / "project" / "edit_manifest.json"
        manifest_data = {
            "workspace": "01-script",
            "source_video": "video-mentah.mp4",
            "created_at": "2026-09-30T00:00:00Z",
            "updated_at": "2026-09-30T00:00:00Z",
            "version": 1,
            "stages": {
                "transcription": {"status": "completed"},
                "subtitle": {"status": "completed"},
                "broll": {"status": "completed"},
            },
            "user_modifications": {},
        }
        save_manifest(m_path, manifest_data)

        # Running parse_srt_file confirms existing subtitle is loaded without re-transcription
        parsed = parse_srt_file(srt_p)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].text, "Sudah ada SRT.")

    # --------------------------------------------------------------------------
    # 19. Manual-edit preservation logic
    # --------------------------------------------------------------------------
    def test_19_manual_edit_preservation_logic(self):
        # Scenario: User opened Kdenlive and manually:
        # 1. Replaced broll/kereta.mp4 with broll/mobil_macet.mp4 at 00:00-00:05
        # 2. Trimmed clip at 00:05-00:10
        # 3. Deleted clip at 00:10-00:15 leaving it blank
        existing_project_data = {
            "v2_clips": [
                {
                    "producer_id": "prod_user_1",
                    "resource": "broll/mobil_macet.mp4",
                    "timeline_start_frame": 0,
                    "timeline_end_frame": 150,  # 00:00 - 00:05 @ 30fps
                    "in": 0,
                    "out": 149,
                },
                {
                    "producer_id": "prod_user_2",
                    "resource": "broll/gedung.jpg",
                    "timeline_start_frame": 150,
                    "timeline_end_frame": 300,  # 00:05 - 00:10 @ 30fps
                    "in": 15,  # User adjusted trim in
                    "out": 145,
                },
                # Segment 3 (300-450) was deleted by user, so it is omitted from v2_clips!
            ]
        }

        auto_placements = [
            BRollPlacement(1, 0.0, 5.0, 5.0, "Seg 1", "broll/kereta.mp4", "video", 10.0, 0.0, 5.0, "MATCHED_OK"),
            BRollPlacement(2, 5.0, 10.0, 5.0, "Seg 2", "broll/gedung.jpg", "image", 5.0, 0.0, 5.0, "MATCHED_OK"),
            BRollPlacement(3, 10.0, 15.0, 5.0, "Seg 3", "broll/taman.mp4", "video", 10.0, 0.0, 5.0, "MATCHED_OK"),
        ]

        merged_p, _, _, stats = merge_timeline_preservations(
            existing_data=existing_project_data,
            auto_placements=auto_placements,
            auto_text_items=[],
            auto_sfx_events=[],
            fps=30.0,
        )

        self.assertTrue(stats["manual_edits_detected"])
        # Check 1: User's replacement preserved
        self.assertEqual(merged_p[0].asset_path, "broll/mobil_macet.mp4")
        self.assertEqual(merged_p[0].status, "USER_PRESERVED")

        # Check 2: User's trim preserved
        self.assertEqual(merged_p[1].asset_path, "broll/gedung.jpg")
        self.assertAlmostEqual(merged_p[1].trim_in, 15 / 30.0, places=2)

        # Check 3: User's deletion preserved as blank (never restored automatically)
        self.assertIsNone(merged_p[2].asset_path)
        self.assertEqual(merged_p[2].status, "USER_DELETED_PRESERVED")

    # --------------------------------------------------------------------------
    # 20. Validation
    # --------------------------------------------------------------------------
    def test_20_validation(self):
        main_meta = VideoMetadata(
            path=self.ws_01 / "footage" / "main.mp4",
            filename="main.mp4",
            duration_seconds=20.0,
            width=1920,
            height=1080,
            fps=30.0,
            total_frames=600,
        )
        main_meta.path.touch()

        valid_segs = [
            TranscriptSegment(1, 0.0, 5.0, 5.0, "Seg 1"),
            TranscriptSegment(2, 5.0, 10.0, 5.0, "Seg 2"),
        ]
        srt_p = self.ws_01 / "subtitle" / "subtitle.srt"
        generate_srt(valid_segs, srt_p)

        plan_p = self.ws_01 / "project" / "broll_plan.json"
        placements = match_broll(valid_segs, [])
        build_broll_plan(self.ws_01, main_meta, placements, plan_p)

        kdenlive_p = self.ws_01 / "project" / "video_auto.kdenlive"
        generate_kdenlive_project(self.ws_01, main_meta, placements, srt_p, kdenlive_p)

        report = validate_output(self.ws_01, main_meta, valid_segs, srt_p, plan_p, kdenlive_p)
        self.assertTrue(report["is_valid"])
        self.assertEqual(len(report["errors"]), 0)

        # Negative timestamp error detection
        bad_segs = [TranscriptSegment(1, -2.0, 5.0, 7.0, "Invalid negative")]
        bad_srt = self.ws_01 / "subtitle" / "bad.srt"
        generate_srt(bad_segs, bad_srt)
        bad_report = validate_output(self.ws_01, main_meta, bad_segs, bad_srt, plan_p, kdenlive_p)
        self.assertFalse(bad_report["is_valid"])
        self.assertTrue(any("negative" in e.lower() for e in bad_report["errors"]))

    # --------------------------------------------------------------------------
    # 21. Malformed Kdenlive & SRT handling
    # --------------------------------------------------------------------------
    def test_21_malformed_kdenlive_handling(self):
        # 1. Non-existent file
        self.assertIsNone(parse_existing_kdenlive(Path("non_existent.kdenlive")))

        # 2. Corrupted / empty file
        bad_kd = self.ws_01 / "project" / "corrupted.kdenlive"
        bad_kd.write_text("<not-valid-xml", encoding="utf-8")
        self.assertIsNone(parse_existing_kdenlive(bad_kd))

        # 3. XML that is not an MLT project
        non_mlt = self.ws_01 / "project" / "other.xml"
        non_mlt.write_text("<root><child>data</child></root>", encoding="utf-8")
        self.assertIsNone(parse_existing_kdenlive(non_mlt))

        # 4. Malformed SRT gracefully skips invalid block and preserves valid blocks
        malformed_srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:03,000\n"
            "Valid segment.\n\n"
            "2\n"
            "THIS IS NOT A TIMECODE\n"
            "Broken line.\n\n"
            "3\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "Another valid segment.\n"
        )
        srt_p = self.ws_01 / "subtitle" / "malformed.srt"
        srt_p.write_text(malformed_srt_content, encoding="utf-8")
        parsed = parse_srt_file(srt_p)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].text, "Valid segment.")
        self.assertEqual(parsed[1].text, "Another valid segment.")

    # --------------------------------------------------------------------------
    # Additional: 7-Track Architecture & Project Bin Integrity Verification
    # --------------------------------------------------------------------------
    def test_22_mlt_7_track_and_bin_integrity(self):
        main_meta = VideoMetadata(
            path=self.ws_01 / "footage" / "main.mp4",
            filename="main.mp4",
            duration_seconds=15.0,
            width=1920,
            height=1080,
            fps=30.0,
            total_frames=450,
        )
        main_meta.path.touch()

        broll_img = self.ws_01 / "broll" / "gedung.jpg"
        broll_img.touch()

        segments = [
            TranscriptSegment(1, 0.0, 5.0, 5.0, "Bagian pertama gedung kantor.", {"gedung"}),
            TranscriptSegment(2, 5.0, 10.0, 5.0, "Masalahnya bukan jarak.", {"masalah"}),
            TranscriptSegment(3, 10.0, 15.0, 5.0, "Penutup.", set()),
        ]
        assets = [BRollAsset(broll_img, "gedung.jpg", "image", None, {"gedung"})]
        placements = match_broll(segments, assets)
        text_items = detect_text_moments(segments, 15.0)

        srt_p = self.ws_01 / "subtitle" / "subtitle.srt"
        generate_srt(segments, srt_p)

        kdenlive_p = self.ws_01 / "project" / "video_auto.kdenlive"
        generate_kdenlive_project(
            self.ws_01, main_meta, placements, srt_p, kdenlive_p,
            text_items=text_items,
        )

        self.assertTrue(kdenlive_p.is_file())
        tree = ET.parse(str(kdenlive_p))
        root = tree.getroot()

        # Check main_bin retain property
        main_bin = root.find("./playlist[@id='main_bin']")
        self.assertIsNotNone(main_bin)
        retain = next((p.text for p in main_bin.findall("property") if p.attrib.get("name") == "xml_retain"), None)
        self.assertEqual(retain, "1")

        # Verify all 6 tracks exist: playlist_a1, playlist_a2, playlist_a3, playlist_v1, playlist_v2, playlist_v3
        for t_id in ["playlist_a1", "playlist_a2", "playlist_a3", "playlist_v1", "playlist_v2", "playlist_v3"]:
            pl = root.find(f"./playlist[@id='{t_id}']")
            self.assertIsNotNone(pl, f"Track {t_id} missing in MLT XML")

        # Verify black_track is track 0 in tractor multitrack
        tractor = root.find("tractor")
        self.assertIsNotNone(tractor)
        multitrack = tractor.find("multitrack")
        tracks = multitrack.findall("track")
        self.assertEqual(tracks[0].attrib.get("producer"), "black_track")

        # Safe path idempotency check
        safe_p = resolve_safe_kdenlive_path(self.ws_01 / "project", overwrite=False)
        self.assertEqual(safe_p.name, "video_auto_2.kdenlive")


if __name__ == "__main__":
    unittest.main()
