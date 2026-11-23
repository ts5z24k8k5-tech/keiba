import unittest

from scripts.jra_pdf_reconciliation import ReconciliationError, reconcile_runner_fields


class RunnerReconciliationTests(unittest.TestCase):
    def compare(self, actual, expected, fields, **kwargs):
        return reconcile_runner_fields(
            actual, expected, race_id="209901010101", horse_no=1,
            fields=fields, **kwargs
        )

    def test_exact_match_after_unicode_and_space_normalization(self):
        report = self.compare({"horse_name": " テスト馬 "}, {"horse_name": "テスト馬"}, ["horse_name"])
        self.assertTrue(report.is_match)

    def test_reports_wrong_finish_rank(self):
        report = self.compare({"finish_rank": 3}, {"finish_rank": 2}, ["finish_rank"])
        self.assertEqual(report.differences[0].status, "mismatch")

    def test_distinguishes_missing_extracted(self):
        report = self.compare({"body_weight": None}, {"body_weight": 456}, ["body_weight"])
        self.assertEqual(report.differences[0].status, "missing_extracted")

    def test_both_nulls_are_not_a_difference(self):
        report = self.compare({"jockey_name": None}, {"jockey_name": None}, ["jockey_name"])
        self.assertTrue(report.is_match)

    def test_explicit_numeric_tolerance(self):
        report = self.compare(
            {"finish_seconds": 92.31}, {"finish_seconds": 92.30},
            ["finish_seconds"], numeric_tolerances={"finish_seconds": "0.02"}
        )
        self.assertTrue(report.is_match)

    def test_no_implicit_numeric_tolerance(self):
        report = self.compare({"finish_seconds": 92.31}, {"finish_seconds": 92.30}, ["finish_seconds"])
        self.assertEqual(report.differences[0].status, "mismatch")

    def test_rejects_missing_requested_key(self):
        with self.assertRaisesRegex(ReconciliationError, "both inputs"):
            self.compare({"horse_name": "馬"}, {}, ["horse_name"])

    def test_rejects_unrequested_tolerance(self):
        with self.assertRaisesRegex(ReconciliationError, "unrequested"):
            self.compare({"horse_name": "馬"}, {"horse_name": "馬"}, ["horse_name"],
                         numeric_tolerances={"finish_seconds": "0.1"})

    def test_rejects_negative_tolerance(self):
        with self.assertRaisesRegex(ReconciliationError, "negative"):
            self.compare({"time": 1.0}, {"time": 1.0}, ["time"],
                         numeric_tolerances={"time": "-0.1"})


if __name__ == "__main__":
    unittest.main()
