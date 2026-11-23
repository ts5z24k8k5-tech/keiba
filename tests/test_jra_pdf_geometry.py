import unittest

from scripts.jra_pdf_geometry import (
    PositionedWord,
    group_words_into_rows,
    positioned_words_from_pymupdf,
)


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

    def test_prevents_tolerance_chain_merging_adjacent_rows(self):
        words = [
            PositionedWord(0, 0, 5, 8, "A"),   # center 4
            PositionedWord(0, 4, 5, 12, "B"),  # center 8
            PositionedWord(0, 7, 5, 15, "C"),  # center 11
        ]
        rows = group_words_into_rows(words, baseline_tolerance=5.0)
        self.assertEqual([row.text for row in rows], ["A B", "C"])

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

    def test_converts_pymupdf_word_tuples(self):
        words = positioned_words_from_pymupdf([
            (1, 2, 10, 12, "馬名", 0, 0, 0),
            (10, 2, 11, 12, " ", 0, 0, 1),
        ])
        self.assertEqual(len(words), 1)
        self.assertEqual(words[0].text, "馬名")
        self.assertEqual((words[0].x0, words[0].y1), (1.0, 12.0))

    def test_rejects_short_pymupdf_tuple(self):
        with self.assertRaisesRegex(ValueError, "five fields"):
            positioned_words_from_pymupdf([(1, 2, 3, 4)])

    def test_rejects_non_numeric_coordinates(self):
        with self.assertRaisesRegex(ValueError, "numeric"):
            positioned_words_from_pymupdf([("x", 2, 3, 4, "bad")])


if __name__ == "__main__":
    unittest.main()
