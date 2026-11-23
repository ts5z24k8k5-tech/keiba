import unittest

from scripts.jra_pdf_runner_fields import RunnerFieldParseError, parse_runner_cells


class RunnerFieldNormalizationTests(unittest.TestCase):
    def test_parses_common_explicit_cells_and_preserves_raw_values(self):
        row = parse_runner_cells({
            "frame_no": "３", "horse_no": "7", "horse_name": "サンプルホース",
            "sex_age": "牡4", "impost_kg": "56.0", "jockey_name": "騎手A",
            "trainer_name": "調教師B", "body_weight": "482(+4)",
            "finish": "2", "finish_time": "1:34.5", "margin": "クビ",
            "win_odds": "4.8", "popularity": "2",
        })
        self.assertEqual((row.frame_no, row.horse_no, row.sex, row.age), (3, 7, "牡", 4))
        self.assertEqual(row.body_weight, 482)
        self.assertEqual(row.body_weight_change, 4)
        self.assertEqual(row.finish_rank, 2)
        self.assertAlmostEqual(row.finish_seconds, 94.5)
        self.assertEqual(row.raw_cells["horse_name"], "サンプルホース")

    def test_blank_optional_cells_remain_null(self):
        row = parse_runner_cells({"horse_no": "1", "horse_name": "馬"})
        self.assertIsNone(row.impost_kg)
        self.assertIsNone(row.finish_rank)
        self.assertIsNone(row.finish_seconds)

    def test_normalizes_full_width_digits(self):
        row = parse_runner_cells({"horse_no": "１２", "horse_name": "馬", "sex_age": "牝３"})
        self.assertEqual(row.horse_no, 12)
        self.assertEqual((row.sex, row.age), ("牝", 3))

    def test_preserves_non_finisher_without_rank(self):
        for finish, status in (("中", "中"), ("中止", "中"), ("失", "失"), ("失格", "失")):
            with self.subTest(finish=finish):
                row = parse_runner_cells({"horse_no": "1", "horse_name": "馬", "finish": finish})
                self.assertEqual(row.finish_raw, finish)
                self.assertIsNone(row.finish_rank)
                self.assertEqual(row.result_status, status)

    def test_demotion_is_not_promoted_to_final_rank(self):
        row = parse_runner_cells({"horse_no": "1", "horse_name": "馬", "finish": "3(降)"})
        self.assertIsNone(row.finish_rank)
        self.assertEqual(row.result_status, "降")
        self.assertEqual(row.finish_raw, "3(降)")

    def test_rejects_missing_required_fields(self):
        for cells in ({"horse_name": "馬"}, {"horse_no": "1"}):
            with self.subTest(cells=cells), self.assertRaises(RunnerFieldParseError):
                parse_runner_cells(cells)

    def test_rejects_ambiguous_or_malformed_values(self):
        cases = (
            {"horse_no": "1番"},
            {"horse_no": "1", "horse_name": "馬", "sex_age": "牡四"},
            {"horse_no": "1", "horse_name": "馬", "body_weight": "482?"},
            {"horse_no": "1", "horse_name": "馬", "finish_time": "1:75.2"},
            {"horse_no": "1", "horse_name": "馬", "win_odds": "人気"},
            {"horse_no": "1", "horse_name": "馬", "finish": "同着?"},
        )
        for cells in cases:
            with self.subTest(cells=cells), self.assertRaises(RunnerFieldParseError):
                parse_runner_cells(cells)

    def test_rejects_unknown_fields_instead_of_silently_ignoring(self):
        with self.assertRaisesRegex(RunnerFieldParseError, "unknown cell keys"):
            parse_runner_cells({"horse_no": "1", "horse_name": "馬", "last3f": "34.5"})


if __name__ == "__main__":
    unittest.main()
