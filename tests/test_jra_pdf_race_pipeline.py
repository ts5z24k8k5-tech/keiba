import unittest

from scripts.jra_pdf_geometry import PositionedWord, TextRow
from scripts.jra_pdf_columns import ColumnBand
from scripts.jra_pdf_race_pipeline import (
    RaceExtractionError, RunnerRowBand, build_race_candidates,
    select_runner_rows_from_page_words,
)


class RacePipelineTests(unittest.TestCase):
    def setUp(self):
        self.bands = [
            ColumnBand("horse_no", 0, 20),
            ColumnBand("horse_name", 20, 100),
            ColumnBand("sex_age", 100, 140),
            ColumnBand("finish", 140, 160),
        ]
        self.digest = "b" * 64

    def row(self, number, name, finish, y=10):
        values = [(5, str(number)), (40, name), (110, "牡4"), (150, finish)]
        words = tuple(PositionedWord(x, y, x + 10, y + 8, text) for x, text in values)
        return TextRow(y + 4, words)

    def test_builds_validated_candidates_and_sorts_by_horse_number(self):
        rows = [self.row(2, "馬B", "2", 20), self.row(1, "馬A", "1", 10)]
        result = build_race_candidates(
            rows, self.bands, race_id="202410010101",
            declared_field_size=2, source_pdf_sha256=self.digest,
            source_page_index=0,
        )
        self.assertEqual([r.fields.horse_no for r in result], [1, 2])
        self.assertEqual(result[0].fields.sex, "牡")
        self.assertIsNone(result[0].candidate.horse_id)

    def test_preserves_nonfinisher_status_without_rank(self):
        result = build_race_candidates(
            [self.row(1, "馬A", "中")], self.bands,
            race_id="202410010101", declared_field_size=1,
            source_pdf_sha256=self.digest, source_page_index=0,
        )
        self.assertEqual(result[0].candidate.result_status, "中")
        self.assertIsNone(result[0].candidate.finish_rank)

    def test_rejects_row_count_mismatch(self):
        with self.assertRaisesRegex(RaceExtractionError, "does not match"):
            build_race_candidates(
                [self.row(1, "馬A", "1")], self.bands,
                race_id="202410010101", declared_field_size=2,
                source_pdf_sha256=self.digest, source_page_index=0,
            )

    def test_rejects_unassigned_words_instead_of_dropping_them(self):
        bad = TextRow(14, self.row(1, "馬A", "1").words + (
            PositionedWord(300, 10, 310, 18, "余剰"),
        ))
        with self.assertRaisesRegex(RaceExtractionError, "does not map"):
            build_race_candidates(
                [bad], self.bands, race_id="202410010101",
                declared_field_size=1, source_pdf_sha256=self.digest,
                source_page_index=0,
            )

    def test_rejects_bad_provenance(self):
        with self.assertRaisesRegex(RaceExtractionError, "SHA-256"):
            build_race_candidates(
                [self.row(1, "馬A", "1")], self.bands,
                race_id="202410010101", declared_field_size=1,
                source_pdf_sha256="bad", source_page_index=0,
            )

    def test_rejects_missing_horse_number_cell(self):
        row = TextRow(14, tuple(w for w in self.row(1, "馬A", "1").words if w.x0 != 5))
        with self.assertRaisesRegex(RaceExtractionError, "horse_no is required"):
            build_race_candidates(
                [row], self.bands, race_id="202410010101",
                declared_field_size=1, source_pdf_sha256=self.digest,
                source_page_index=0,
            )


if __name__ == "__main__":
    unittest.main()
