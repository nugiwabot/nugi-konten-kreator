import re
import unittest

from engine.performance.performance_director import (
    annotate_script,
    render_annotated,
    render_clean,
    render_inline_script,
)


class PerformanceDirectorTests(unittest.TestCase):
    def test_question_gets_curiosity_direction(self):
        cue = annotate_script("Kenapa kita masih tinggal di kota?").cues[0]
        self.assertEqual(cue.role, "CURIOUS")
        self.assertEqual(cue.pitch, "rising")
        self.assertGreater(cue.pause_after, 0)

    def test_reveal_gets_contrast_and_pause(self):
        cue = annotate_script("Dan ternyata, masalahnya bukan harga rumah.").cues[0]
        self.assertEqual(cue.role, "REVEAL")
        self.assertEqual(cue.pitch, "contrast")
        self.assertGreaterEqual(cue.pause_after, 0.8)

    def test_inline_output_has_visual_performance_cues(self):
        source = "Kenapa gaji naik tapi rumah yang kita mampu beli terasa makin jauh?"
        rendered = render_inline_script(annotate_script(source))
        self.assertIn("↗", rendered)
        self.assertIn("**", rendered)
        self.assertNotIn("Pitch:", rendered)
        self.assertNotIn("Pace:", rendered)
        self.assertIn("Kenapa", rendered)
        self.assertIn("rumah", rendered)

    def test_question_has_hook_and_landing(self):
        source = "Pernah merasa heran: beberapa tahun lalu kamu menabung untuk uang muka rumah, tapi saat gajimu kini meningkat, harga rumah incaranmu justru melesat jauh lebih tinggi?"
        rendered = render_inline_script(annotate_script(source))
        self.assertIn("**PERNAH↗**", rendered)
        self.assertIn("**TINGGI↘**", rendered)

    def test_inline_output_uses_thought_boundaries(self):
        source = "Kita bekerja lebih keras, namun garis finis kepemilikan hunian seolah terus digeser menjauh."
        rendered = render_inline_script(annotate_script(source))
        self.assertIn(" / ", rendered)

    def test_clean_output_preserves_wording(self):
        source = "Kenapa kita masih tinggal di kota?\nPadahal kita bisa bekerja dari mana saja."
        clean = render_clean(annotate_script(source))
        self.assertIn("Kenapa kita masih tinggal di kota?", clean)
        self.assertIn("Padahal kita bisa bekerja dari mana saja.", clean)

    def test_detailed_sheet_remains_available(self):
        rendered = render_annotated(annotate_script("Rumah semakin mahal."))
        self.assertIn("NUGI PERFORMANCE SHEET", rendered)
        self.assertIn("↘", rendered)

    def test_not_every_line_is_forced_emphasis(self):
        source = "Rumah semakin mahal.\nOrang mulai pindah ke pinggiran kota.\nWaktu perjalanan semakin panjang."
        cues = annotate_script(source).cues
        self.assertLessEqual(sum(1 for c in cues if c.emphasis), 2)

    def test_inline_output_preserves_original_words(self):
        source = "Rumah semakin mahal. Orang mulai pindah ke pinggiran kota."
        rendered = render_inline_script(annotate_script(source))
        source_words = re.findall(r"[A-Za-zÀ-ÿ]+", source.lower())
        rendered_words = re.findall(r"[A-Za-zÀ-ÿ]+", rendered.lower())
        for word in source_words:
            self.assertIn(word, rendered_words)


if __name__ == "__main__":
    unittest.main()
