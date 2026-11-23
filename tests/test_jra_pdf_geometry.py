import unittest

from scripts.jra_pdf_geometry import PositionedWord, group_words_into_rows


class CoordinateRowGroupingTests(unittest.TestCase):
    def test_groups_same_baseline_and_sorts_left_to_right(self):
        words = [
            PositionedWord(80, 20, 95, 30, "騎手"),
            PositionedWord(10, 20, 20, 30, "1"),
            PositionedWord(35, 21, 60, 29, "馬名"),
        ]
        rows = group_words_into_rows(words)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].text, "1 馬名 騎手")

    def test_keeps_distinct_baselines_separate(self):
        words = [
            PositionedWord(10, 10, 20, 18, "1"),
            PositionedWord(10, 18, 20, 26, "2"),
        ]
        rows = group_words_into_rows(words, baseline_tolerance=2.0)
        self.assertEqual([row.text for row in rows], ["1", "2"])

    def test_uses_closest_row_within_tolerance(self):
        words = [
            PositionedWord(0, 0, 5, 8, "A"),
            PositionedWord(0, 4, 5, 12, "B"),
            PositionedWord(0, 7, 5, 15, "C"),
        ]
        rows = group_words_into_rows(words, baseline_tolerance=4.0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].text, "A B C")

    def test_ignores_blank_words(self):
        words = [
            PositionedWord(0, 0, 5, 8, " "),
            PositionedWord(10, 0, 15, 8, "馬"),
        ]
        rows = group_words_into_rows(words)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].text, "馬")

    def test_rejects_negative_tolerance(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            group_words_into_rows([], baseline_tolerance=-1)

    def test_rejects_inverted_bbox(self):
        with self.assertRaisesRegex(ValueError, "inverted"):
            group_words_into_rows([PositionedWord(5, 0, 1, 8, "bad")])


if __name__ == "__main__":
    unittest.main()
