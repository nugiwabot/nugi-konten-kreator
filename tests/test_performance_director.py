import unittest

from engine.performance.performance_director import annotate_script, render_annotated, render_clean


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

    def test_clean_output_preserves_wording(self):
        source = "Kenapa kita masih tinggal di kota?\nPadahal kita bisa bekerja dari mana saja."
        clean = render_clean(annotate_script(source))
        self.assertIn("Kenapa kita masih tinggal di kota?", clean)
        self.assertIn("Padahal kita bisa bekerja dari mana saja.", clean)

    def test_learning_layer_is_explained(self):
        rendered = render_annotated(annotate_script("Rumah semakin mahal."))
        self.assertIn("Pitch", rendered)
        self.assertIn("Pace", rendered)
        self.assertIn("Emphasis", rendered)
        self.assertIn("Kenapa", rendered)

    def test_not_every_line_is_forced_emphasis(self):
        source = "Rumah semakin mahal.\nOrang mulai pindah ke pinggiran kota.\nWaktu perjalanan semakin panjang."
        cues = annotate_script(source).cues
        self.assertLessEqual(sum(1 for c in cues if c.emphasis), 2)


if __name__ == "__main__":
    unittest.main()
