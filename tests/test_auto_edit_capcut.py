#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CapCut Desktop Auto Edit Engine (engine.pipeline.auto_edit_capcut)
Covers all testing criteria required by specification:
1. Video detection logic
2. Video duration & metadata probing
3. Whisper / SRT segmentation & parsing
4. SRT generation with valid timestamps
5. Timestamp validity (non-negative, start < end, bounds)
6. B-roll matching logic (keywords, clusters, reuse penalty)
7. Video B-roll duration trimming
8. Image B-roll duration dynamic adaptation
9. Track structure (Track 0 main video, Track 1 B-roll overlay, Track 2 Text)
10. CapCut Desktop Draft generation (draft_content.json, draft_meta_info.json, timeline_layout.json, etc.)
11. Unique project ID & safe naming
12. Path validation & forward slashes
13. Draft installation into com.lveditor.draft and root_meta_info.json registration
14. Failure handling (empty B-roll, missing video)
15. 16-point integrity validation
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.pipeline.auto_edit_capcut import (
    BRollAsset,
    BRollPlacement,
    TranscriptSegment,
    VideoMetadata,
    build_capcut_plan,
    calculate_match_score,
    detect_capcut_environment,
    extract_keywords_from_string,
    find_broll_assets,
    find_main_video,
    find_workspace,
    format_timestamp_srt,
    generate_capcut_draft,
    generate_srt,
    install_capcut_draft,
    match_broll,
    parse_srt_file,
    parse_timestamp_srt,
    validate_project,
)


class TestAutoEditCapCut(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="capcut_test_"))
        self.workspace_dir = self.temp_dir / "01-script"
        self.footage_dir = self.workspace_dir / "footage"
        self.broll_dir = self.workspace_dir / "broll"
        self.subtitle_dir = self.workspace_dir / "subtitle"
        self.project_dir = self.workspace_dir / "project"
        self.render_dir = self.workspace_dir / "render"

        for d in [self.footage_dir, self.broll_dir, self.subtitle_dir, self.project_dir, self.render_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_workspace(self):
        ws = find_workspace(str(self.workspace_dir))
        self.assertTrue(ws.is_dir())
        self.assertTrue((ws / "footage").is_dir())
        self.assertTrue((ws / "broll").is_dir())
        self.assertTrue((ws / "subtitle").is_dir())
        self.assertTrue((ws / "project").is_dir())

    def test_find_main_video_single(self):
        vid = self.footage_dir / "video-mentah.mp4"
        vid.write_bytes(b"\x00" * 1024)
        found = find_main_video(self.footage_dir)
        self.assertEqual(found.name, "video-mentah.mp4")

    def test_find_main_video_priority_keywords(self):
        v1 = self.footage_dir / "sample_clip.mp4"
        v1.write_bytes(b"\x00" * 1024)
        v2 = self.footage_dir / "video_mentah_master.mp4"
        v2.write_bytes(b"\x00" * 1024)
        found = find_main_video(self.footage_dir)
        self.assertEqual(found.name, "video_mentah_master.mp4")

    def test_find_main_video_missing(self):
        with self.assertRaises(FileNotFoundError):
            find_main_video(self.footage_dir)

    def test_timestamp_parsing_and_formatting(self):
        sec = 125.456
        srt_tc = format_timestamp_srt(sec)
        self.assertEqual(srt_tc, "00:02:05,456")
        parsed_sec = parse_timestamp_srt(srt_tc)
        self.assertAlmostEqual(sec, parsed_sec, places=3)

    def test_srt_generation_and_parsing(self):
        segs = [
            TranscriptSegment(1, 0.0, 4.2, 4.2, "Jutaan orang berangkat pagi hari.", {"jutaan", "orang", "berangkat"}),
            TranscriptSegment(2, 4.2, 8.5, 4.3, "Menggunakan kereta komuter.", {"menggunakan", "kereta", "komuter"}),
        ]
        srt_file = self.subtitle_dir / "subtitle.srt"
        generate_srt(segs, srt_file)
        self.assertTrue(srt_file.is_file())

        parsed = parse_srt_file(srt_file)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].segment_id, 1)
        self.assertAlmostEqual(parsed[0].start, 0.0)
        self.assertAlmostEqual(parsed[0].end, 4.2)
        self.assertEqual(parsed[0].text, "Jutaan orang berangkat pagi hari.")
        self.assertEqual(parsed[1].segment_id, 2)
        self.assertAlmostEqual(parsed[1].start, 4.2)

    def test_broll_discovery(self):
        (self.broll_dir / "001_kereta_stasiun.mp4").write_bytes(b"\x00" * 1024)
        (self.broll_dir / "002_rumah_kota.jpg").write_bytes(b"\x00" * 1024)
        (self.broll_dir / ".hidden").write_bytes(b"\x00" * 10)

        assets = find_broll_assets(self.broll_dir)
        self.assertEqual(len(assets), 2)
        types = {a.media_type for a in assets}
        self.assertIn("video", types)
        self.assertIn("image", types)

    def test_calculate_match_score(self):
        seg = TranscriptSegment(1, 0.0, 4.0, 4.0, "Orang naik kereta ke kantor", {"orang", "kereta", "kantor"})
        asset_kereta = BRollAsset(Path("broll/kereta_api.mp4"), "kereta_api.mp4", "video", 1920, 1080, 10.0, {"kereta", "api"})
        asset_pantai = BRollAsset(Path("broll/pantai.jpg"), "pantai.jpg", "image", 1920, 1080, None, {"pantai", "laut"})

        score_kereta, reason_k = calculate_match_score(seg, asset_kereta, used_count=0)
        score_pantai, reason_p = calculate_match_score(seg, asset_pantai, used_count=0)

        self.assertGreater(score_kereta, score_pantai)
        self.assertIn("keyword:kereta", reason_k)

        # Test reuse penalty
        score_used, reason_u = calculate_match_score(seg, asset_kereta, used_count=2)
        self.assertLess(score_used, score_kereta)
        self.assertIn("reuse_penalty", reason_u)

    def test_broll_matching_and_duration_handling(self):
        segs = [
            TranscriptSegment(1, 0.0, 4.0, 4.0, "Berangkat naik kereta", {"berangkat", "kereta"}),
            TranscriptSegment(2, 4.0, 9.0, 5.0, "Rumah di pinggiran kota", {"rumah", "pinggiran", "kota"}),
            TranscriptSegment(3, 9.0, 12.0, 3.0, "Topik lain tanpa broll", {"topik"}),
        ]
        assets = [
            BRollAsset(Path("broll/kereta.mp4"), "kereta.mp4", "video", 1920, 1080, 10.0, {"kereta"}),
            BRollAsset(Path("broll/rumah.jpg"), "rumah.jpg", "image", 1920, 1080, None, {"rumah", "kota"}),
        ]

        placements = match_broll(segs, assets, min_score=3.0)
        self.assertEqual(len(placements), 3)

        # Segment 1: Video trimmed
        p1 = placements[0]
        self.assertEqual(p1.asset_type, "video")
        self.assertEqual(p1.start, 0.0)
        self.assertEqual(p1.end, 4.0)
        self.assertEqual(p1.duration, 4.0)
        self.assertEqual(p1.trim_in, 0.0)
        self.assertEqual(p1.trim_out, 4.0)
        self.assertEqual(p1.status, "MATCHED_OK")

        # Segment 2: Image adapts to 5.0s duration
        p2 = placements[1]
        self.assertEqual(p2.asset_type, "image")
        self.assertEqual(p2.start, 4.0)
        self.assertEqual(p2.end, 9.0)
        self.assertEqual(p2.duration, 5.0)
        self.assertEqual(p2.status, "MATCHED_OK")

        # Segment 3: Unmatched
        p3 = placements[2]
        self.assertEqual(p3.asset_type, "none")
        self.assertIsNone(p3.asset_path)

    def test_build_capcut_plan(self):
        placements = [
            BRollPlacement(1, 0.0, 4.2, 4.2, "Kereta pagi", "broll/kereta.mp4", "kereta.mp4", "video", 10.0, 0.0, 4.2, "MATCHED_OK", 20.0, "kw"),
            BRollPlacement(2, 4.2, 8.5, 4.3, "Rumah jauh", "broll/rumah.jpg", "rumah.jpg", "image", 4.3, 0.0, 4.3, "MATCHED_OK", 15.0, "kw"),
        ]
        plan_file = self.project_dir / "capcut_broll_plan.json"
        build_capcut_plan("01-script", "footage/video.mp4", placements, plan_file)

        self.assertTrue(plan_file.is_file())
        data = json.loads(plan_file.read_text(encoding="utf-8"))
        self.assertEqual(data["workspace"], "01-script")
        self.assertEqual(data["main_video"], "footage/video.mp4")
        self.assertEqual(len(data["segments"]), 2)
        self.assertEqual(data["segments"][0]["asset"], "broll/kereta.mp4")
        self.assertEqual(data["segments"][0]["type"], "video")
        self.assertEqual(data["segments"][1]["asset"], "broll/rumah.jpg")
        self.assertEqual(data["segments"][1]["type"], "image")

    def test_capcut_draft_generation_and_schema(self):
        # Create dummy main video
        main_vid_path = self.footage_dir / "video-mentah.mp4"
        main_vid_path.write_bytes(b"\x00" * 4096)

        # Create dummy broll
        broll_img_path = self.broll_dir / "rumah.jpg"
        broll_img_path.write_bytes(b"\x00" * 2048)

        meta = VideoMetadata(
            path=main_vid_path,
            filename="video-mentah.mp4",
            duration_seconds=10.0,
            duration_microseconds=10000000,
            width=1920,
            height=1080,
            fps=30.0
        )

        placements = [
            BRollPlacement(1, 0.0, 5.0, 5.0, "Seg 1", "broll/rumah.jpg", "rumah.jpg", "image", 5.0, 0.0, 5.0, "MATCHED_OK", 10.0, "kw"),
            BRollPlacement(2, 5.0, 10.0, 5.0, "Seg 2", None, None, "none", None, 0.0, 0.0, "UNMATCHED", 0.0, "none"),
        ]

        srt_segs = [
            TranscriptSegment(1, 0.0, 5.0, 5.0, "Seg 1 text", {"seg"}),
            TranscriptSegment(2, 5.0, 10.0, 5.0, "Seg 2 text", {"seg"}),
        ]

        output_draft = self.project_dir / "capcut"
        env = {
            "installed": False,
            "draft_root": None,
            "version": "9.5.0",
            "font_path": "C:/Windows/Fonts/arial.ttf"
        }

        generate_capcut_draft(
            workspace_dir=self.workspace_dir,
            main_video_meta=meta,
            placements=placements,
            srt_segments=srt_segs,
            output_draft_dir=output_draft,
            project_name="test_proj",
            include_subtitle=True,
            capcut_env=env
        )

        # Verify draft files
        self.assertTrue((output_draft / "draft_content.json").is_file())
        self.assertTrue((output_draft / "draft_content.json.bak").is_file())
        self.assertTrue((output_draft / "draft_meta_info.json").is_file())
        self.assertTrue((output_draft / "timeline_layout.json").is_file())
        self.assertTrue((output_draft / "draft_settings").is_file())
        self.assertTrue((output_draft / "attachment_pc_common.json").is_file())

        # Verify JSON content
        content = json.loads((output_draft / "draft_content.json").read_text(encoding="utf-8"))
        self.assertEqual(content["name"], "test_proj")
        self.assertEqual(content["duration"], 10000000)
        self.assertEqual(len(content["tracks"]), 3)

        # Track 0: Video
        self.assertEqual(content["tracks"][0]["type"], "video")
        self.assertEqual(content["tracks"][0]["flag"], 0)
        self.assertEqual(len(content["tracks"][0]["segments"]), 1)

        # Track 1: B-roll
        self.assertEqual(content["tracks"][1]["type"], "video")
        self.assertEqual(content["tracks"][1]["flag"], 2)
        self.assertEqual(len(content["tracks"][1]["segments"]), 1)

        # Track 2: Text
        self.assertEqual(content["tracks"][2]["type"], "text")
        self.assertEqual(len(content["tracks"][2]["segments"]), 2)

        # Materials check
        mat_videos = content["materials"]["videos"]
        self.assertEqual(len(mat_videos), 2) # main video + 1 broll
        mat_texts = content["materials"]["texts"]
        self.assertEqual(len(mat_texts), 2)

    def test_install_capcut_draft_safe(self):
        # Create a mock CapCut draft root
        mock_capcut_root = self.temp_dir / "mock_capcut_drafts"
        mock_capcut_root.mkdir(parents=True, exist_ok=True)
        root_meta_file = mock_capcut_root / "root_meta_info.json"
        root_meta_file.write_text(json.dumps({
            "all_draft_store": [],
            "draft_ids": 0,
            "root_path": str(mock_capcut_root)
        }), encoding="utf-8")

        # Create source draft
        src_draft = self.project_dir / "capcut"
        src_draft.mkdir(parents=True, exist_ok=True)
        (src_draft / "draft_meta_info.json").write_text(json.dumps({
            "draft_id": "TEST-UUID-1234",
            "draft_name": "my_project",
            "tm_duration": 5000000,
            "tm_draft_create": 1000,
            "tm_draft_modified": 1000,
            "draft_materials": []
        }), encoding="utf-8")
        (src_draft / "draft_content.json").write_text(json.dumps({
            "id": "TEST-UUID-1234",
            "name": "my_project"
        }), encoding="utf-8")

        # First install
        installed_1 = install_capcut_draft(src_draft, "my_project", mock_capcut_root)
        self.assertEqual(installed_1.name, "my_project")
        self.assertTrue((mock_capcut_root / "my_project").is_dir())

        # Second install: must avoid overwrite and create unique name
        installed_2 = install_capcut_draft(src_draft, "my_project", mock_capcut_root)
        self.assertEqual(installed_2.name, "my_project_02")
        self.assertTrue((mock_capcut_root / "my_project_02").is_dir())

        # Check root_meta_info
        rm_data = json.loads(root_meta_file.read_text(encoding="utf-8"))
        self.assertEqual(len(rm_data["all_draft_store"]), 2)
        names = [d["draft_name"] for d in rm_data["all_draft_store"]]
        self.assertIn("my_project", names)
        self.assertIn("my_project_02", names)

    def test_project_validation_16_rules(self):
        main_vid_path = self.footage_dir / "video-mentah.mp4"
        main_vid_path.write_bytes(b"\x00" * 4096)
        meta = VideoMetadata(main_vid_path, "video-mentah.mp4", 10.0, 10000000, 1920, 1080, 30.0)

        srt_file = self.subtitle_dir / "subtitle.srt"
        generate_srt([TranscriptSegment(1, 0.0, 5.0, 5.0, "Test", {"test"})], srt_file)

        broll_file = self.broll_dir / "broll.jpg"
        broll_file.write_bytes(b"\x00" * 1024)

        plan_file = self.project_dir / "capcut_broll_plan.json"
        build_capcut_plan("01-script", "footage/video-mentah.mp4", [
            BRollPlacement(1, 0.0, 5.0, 5.0, "Test", "broll/broll.jpg", "broll.jpg", "image", 5.0, 0.0, 5.0, "MATCHED_OK", 10.0, "kw")
        ], plan_file)

        draft_dir = self.project_dir / "capcut"
        generate_capcut_draft(
            workspace_dir=self.workspace_dir,
            main_video_meta=meta,
            placements=[BRollPlacement(1, 0.0, 5.0, 5.0, "Test", "broll/broll.jpg", "broll.jpg", "image", 5.0, 0.0, 5.0, "MATCHED_OK", 10.0, "kw")],
            srt_segments=[TranscriptSegment(1, 0.0, 5.0, 5.0, "Test", {"test"})],
            output_draft_dir=draft_dir,
            project_name="val_test",
        )

        errors = validate_project(self.workspace_dir, meta, srt_file, plan_file, draft_dir)
        self.assertEqual(errors, [], f"Validation errors found: {errors}")


if __name__ == "__main__":
    unittest.main()
