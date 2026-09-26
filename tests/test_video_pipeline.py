"""
tests/test_video_pipeline.py
=============================
Unit and integration tests for the automated video production pipeline:
  - ScriptParser: narrative markdown parsing and timecode extraction
  - VisualRequirementsGenerator: mini-documentary visual shot design
  - SRTGenerator: subtitle cue generation and wrapping
  - KdenliveExporter: MLT XML validity and timeline.json generation
  - VideoPipeline: end-to-end execution
"""

import json
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.pipeline.kdenlive_exporter import KdenliveExporter, TimelineClip, TimelineData
from engine.pipeline.script_parser import NarasiScript, ScriptParser, ScriptSection, parse_timecode_to_seconds
from engine.pipeline.srt_generator import SRTGenerator
from engine.pipeline.video_pipeline import VideoPipeline
from engine.pipeline.visual_requirements import VisualRequirementsGenerator


SAMPLE_SCRIPT = """# 5 Narasi Konten
## 📽️ NARASI 1: AI × HUMAN
### *Mengapa AI Bikin Cepat, tapi Kita Justru Makin Capek?*
- **Pilar DNA:** `AI × HUMAN × WHY`

#### NASKAH TALKING-HEAD (Durasi ~65 Detik | 158 Kata)

```text
[00:00 - 00:05] HOOK
Pernah sadar nggak, kenapa semakin canggih AI yang kita pakai di kantor, jam kerja kita rasanya justru makin berantakan?

[00:05 - 00:18] TENSION & PARADOX
Secara logika, kalau mesin bisa ngerjain tugas dua jam jadi dua menit, kita harusnya punya waktu luang lebih banyak buat istirahat.

[00:18 - 00:40] CONTEXT & THE REAL DATA
Kenapa bisa begitu? Karena dalam ekonomi modern, efisiensi nggak pernah dihadiahkan dalam bentuk waktu santai.

[00:40 - 00:62] THE REVELATION (THE WHY)
Jadi masalah sebenarnya bukan AI yang mengambil alih hidup kita.

[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)
Kalau mesin memang diciptakan untuk bekerja tanpa henti, bukankah yang membedakan kita sebagai manusia adalah keberanian untuk tahu kapan harus berhenti?
```
"""


class TestScriptParser(unittest.TestCase):

    def setUp(self):
        self.parser = ScriptParser()

    def test_parse_timecode_formats(self):
        self.assertEqual(parse_timecode_to_seconds("00:05"), 5.0)
        self.assertEqual(parse_timecode_to_seconds("00:62"), 62.0)
        self.assertEqual(parse_timecode_to_seconds("01:15"), 75.0)
        self.assertEqual(parse_timecode_to_seconds("00:01:15"), 75.0)
        self.assertEqual(parse_timecode_to_seconds("30"), 30.0)

    def test_parse_text(self):
        narratives = self.parser.parse_text(SAMPLE_SCRIPT)
        self.assertEqual(len(narratives), 1)
        narasi = narratives[0]

        self.assertEqual(narasi.index, 1)
        self.assertEqual(narasi.id, "narasi-01")
        self.assertEqual(narasi.title, "Mengapa AI Bikin Cepat, tapi Kita Justru Makin Capek?")
        self.assertIn("AI", narasi.dna)
        self.assertEqual(narasi.total_duration_seconds, 75.0)
        self.assertEqual(len(narasi.sections), 5)

        # Check section timecodes
        hook = narasi.sections[0]
        self.assertEqual(hook.section_type, "hook")
        self.assertEqual(hook.start_seconds, 0.0)
        self.assertEqual(hook.end_seconds, 5.0)
        self.assertEqual(hook.duration_seconds, 5.0)

        tension = narasi.sections[1]
        self.assertEqual(tension.section_type, "tension")
        self.assertEqual(tension.start_seconds, 5.0)
        self.assertEqual(tension.end_seconds, 18.0)
        self.assertEqual(tension.duration_seconds, 13.0)

        revelation = narasi.sections[3]
        self.assertEqual(revelation.section_type, "revelation")
        self.assertEqual(revelation.start_seconds, 40.0)
        self.assertEqual(revelation.end_seconds, 62.0)


class TestVisualRequirementsGenerator(unittest.TestCase):

    def setUp(self):
        self.parser = ScriptParser()
        self.gen = VisualRequirementsGenerator()
        self.narratives = self.parser.parse_text(SAMPLE_SCRIPT)

    def test_generate_shots_curated(self):
        shots = self.gen.generate_shots_for_narrative(self.narratives[0])
        self.assertEqual(len(shots), 11)
        total_duration = sum(s.duration_seconds for s in shots)
        self.assertAlmostEqual(total_duration, 75.0, places=1)

        # First shot should have text overlay and query
        self.assertTrue(shots[0].text_overlay)
        self.assertTrue(shots[0].search_query)
        self.assertEqual(shots[0].start_seconds, 0.0)
        self.assertEqual(shots[0].end_seconds, 5.0)

    def test_generate_shots_heuristic_fallback(self):
        # Narrative index 99 uses heuristic fallback
        custom_narasi = NarasiScript(
            index=99,
            id="narasi-99",
            title="Custom Script",
            pillar="TECH",
            dna="TECH x FUTURE",
            total_duration_seconds=30.0,
            sections=[
                ScriptSection(1, "HOOK", "hook", 0.0, 5.0, 5.0, "Pernahkah Anda berpikir tentang AI?", "[00:00 - 00:05] HOOK"),
                ScriptSection(2, "CONTEXT", "context", 5.0, 30.0, 25.0, "Dunia data sedang berkembang sangat cepat setiap hari.", "[00:05 - 00:30] CONTEXT"),
            ]
        )
        shots = self.gen.generate_shots_for_narrative(custom_narasi)
        self.assertGreaterEqual(len(shots), 2)
        total_duration = sum(s.duration_seconds for s in shots)
        self.assertAlmostEqual(total_duration, 30.0, places=1)


class TestSRTGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = SRTGenerator()

    def test_generate_srt_format(self):
        sections = [
            ScriptSection(1, "HOOK", "hook", 0.0, 5.0, 5.0, "Pernah sadar nggak?", "[00:00 - 00:05] HOOK"),
            ScriptSection(2, "TENSION", "tension", 5.0, 10.0, 5.0, "Secara logika mesin lebih cepat.", "[00:05 - 00:10] TENSION"),
        ]
        srt_text = self.gen.generate_srt_content(sections, split_long_lines=False)
        self.assertIn("1\n00:00:00,000 --> 00:00:05,000", srt_text)
        self.assertIn("Pernah sadar nggak?", srt_text)
        self.assertIn("2\n00:00:05,000 --> 00:00:10,000", srt_text)
        self.assertIn("Secara logika mesin lebih cepat.", srt_text)


class TestKdenliveExporter(unittest.TestCase):

    def setUp(self):
        self.exporter = KdenliveExporter()
        self.timeline = TimelineData(
            project_name="Nugi_Narasi_01",
            narrative_id="narasi-01",
            title="Test Project",
            pillar="AI x HUMAN",
            dna="AI x HUMAN",
            aspect_ratio="9:16",
            width=1080,
            height=1920,
            fps=30,
            total_duration_seconds=10.0,
            total_frames=300,
            clips=[
                TimelineClip(
                    clip_id="clip_01",
                    section_index=1,
                    section_name="HOOK",
                    section_type="hook",
                    start_seconds=0.0,
                    end_seconds=5.0,
                    duration_seconds=5.0,
                    start_frame=0,
                    end_frame=149,
                    duration_frames=150,
                    media_type="color_placeholder",
                    asset_filename="",
                    asset_local_path="",
                    text_overlay="Test Hook",
                ),
                TimelineClip(
                    clip_id="clip_02",
                    section_index=2,
                    section_name="TENSION",
                    section_type="tension",
                    start_seconds=5.0,
                    end_seconds=10.0,
                    duration_seconds=5.0,
                    start_frame=150,
                    end_frame=299,
                    duration_frames=150,
                    media_type="color_placeholder",
                    asset_filename="",
                    asset_local_path="",
                    text_overlay="Test Tension",
                ),
            ]
        )

    def test_generate_xml_contains_vertical_profile_and_tracks(self):
        xml_str = self.exporter.generate_kdenlive_xml(self.timeline)
        self.assertIn("<profile", xml_str)
        self.assertIn('width="1080"', xml_str)
        self.assertIn('height="1920"', xml_str)
        self.assertIn('display_aspect_num="9"', xml_str)
        self.assertIn('display_aspect_den="16"', xml_str)
        self.assertIn('id="playlist_video"', xml_str)
        self.assertIn('id="playlist_audio"', xml_str)
        self.assertIn('id="maintractor"', xml_str)

    def test_melt_validation_if_available(self):
        melt_path = r"C:\Program Files\kdenlive\bin\melt.exe"
        if not Path(melt_path).exists():
            self.skipTest("melt.exe not found on system")

        with tempfile.TemporaryDirectory() as tmpdir:
            kdenlive_file = Path(tmpdir) / "test.kdenlive"
            self.exporter.export_project(kdenlive_file, self.timeline)
            cmd = [melt_path, str(kdenlive_file), "-consumer", "null", "count=1"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"melt failed with error: {res.stderr}")


class TestVideoPipelineDryRun(unittest.TestCase):

    def test_pipeline_dry_run_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "test_script.md"
            script_file.write_text(SAMPLE_SCRIPT, encoding="utf-8")

            out_dir = Path(tmpdir) / "output"
            pipeline = VideoPipeline()
            report = pipeline.run(script_path=script_file, output_dir=out_dir, dry_run=True)

            self.assertEqual(len(report.successful_narratives), 1)
            res = report.successful_narratives[0]

            self.assertTrue(res.kdenlive_file.exists())
            self.assertTrue(res.timeline_file.exists())
            self.assertTrue(res.subtitles_file.exists())
            self.assertTrue(res.sources_file.exists())
            self.assertTrue((res.output_dir / "assets").exists())

            # Verify timeline JSON structure
            timeline_data = json.loads(res.timeline_file.read_text(encoding="utf-8"))
            self.assertEqual(timeline_data["video_format"]["aspect_ratio"], "9:16")
            self.assertEqual(timeline_data["video_format"]["width"], 1080)
            self.assertEqual(timeline_data["video_format"]["height"], 1920)
            self.assertEqual(timeline_data["video_format"]["fps"], 30)
            self.assertIn("video_track_main", timeline_data["tracks"])
            self.assertIn("audio_track_placeholder", timeline_data["tracks"])
            self.assertEqual(len(timeline_data["tracks"]["video_track_main"]["clips"]), 11)


if __name__ == "__main__":
    unittest.main()
