import unittest

from scripts.jra_pdf_geometry import PositionedWord, TextRow
from scripts.jra_pdf_columns import (
    ColumnAssignmentError,
    ColumnBand,
    assign_word_to_column,
    split_row_into_columns,
    validate_column_bands,
)


class ExplicitColumnAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.bands = [
            ColumnBand("horse_no", 0, 30),
            ColumnBand("horse_name", 30, 160),
            ColumnBand("jockey", 160, 240),
        ]

    def test_assigns_words_to_explicit_bands(self):
        word = PositionedWord(8, 10, 18, 20, "7")
        self.assertEqual(assign_word_to_column(word, self.bands), "horse_no")

    def test_splits_row_and_joins_words_within_each_cell(self):
        row = TextRow(15, (
            PositionedWord(170, 10, 190, 20, "騎手A"),
            PositionedWord(8, 10, 18, 20, "7"),
            PositionedWord(40, 10, 65, 20, "サンプル"),
            PositionedWord(68, 10, 95, 20, "ホース"),
        ))
        cells = split_row_into_columns(row, self.bands)
        self.assertEqual(cells, {
            "horse_no": "7",
            "horse_name": "サンプル ホース",
            "jockey": "騎手A",
        })

    def test_rejects_overlapping_bands(self):
        with self.assertRaisesRegex(ColumnAssignmentError, "overlapping"):
            validate_column_bands([
                ColumnBand("a", 0, 20),
                ColumnBand("b", 19, 30),
            ])

    def test_rejects_duplicate_names(self):
        with self.assertRaisesRegex(ColumnAssignmentError, "duplicate"):
            validate_column_bands([
                ColumnBand("same", 0, 10),
                ColumnBand("same", 10, 20),
            ])

    def test_rejects_invalid_band_width(self):
        with self.assertRaisesRegex(ColumnAssignmentError, "invalid bounds"):
            validate_column_bands([ColumnBand("zero", 10, 10)])

    def test_rejects_words_in_unconfigured_gaps(self):
        word = PositionedWord(25, 10, 35, 20, "境界")
        with self.assertRaisesRegex(ColumnAssignmentError, "exactly one"):
            assign_word_to_column(word, self.bands)

    def test_left_boundary_is_inclusive_and_right_boundary_exclusive(self):
        self.assertEqual(
            assign_word_to_column(PositionedWord(0, 0, 0, 5, "L"), self.bands),
            "horse_no",
        )
        self.assertEqual(
            assign_word_to_column(PositionedWord(30, 0, 30, 5, "R"), self.bands),
            "horse_name",
        )

    def test_can_collect_unassigned_words_only_when_explicitly_allowed(self):
        row = TextRow(15, (PositionedWord(250, 10, 260, 20, "outside"),))
        cells = split_row_into_columns(row, self.bands, reject_unassigned=False)
        self.assertEqual(cells["_unassigned"], "outside")
        with self.assertRaises(ColumnAssignmentError):
            split_row_into_columns(row, self.bands)


if __name__ == "__main__":
    unittest.main()
