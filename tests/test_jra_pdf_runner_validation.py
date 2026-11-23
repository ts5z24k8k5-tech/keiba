import unittest
from scripts.jra_pdf_runner_validation import RunnerCandidate, RunnerValidationError, validate_runner_candidates

class RunnerCandidateValidationTests(unittest.TestCase):
    def setUp(self):
        self.race_id = "202410010101"
        self.digest = "a" * 64

    def row(self, horse_no, **overrides):
        values = dict(race_id=self.race_id, horse_no=horse_no, horse_name=f"馬{horse_no}", raw_row_text=f"{horse_no} 馬{horse_no} 牡4", source_pdf_sha256=self.digest, source_page_index=0, finish_raw=str(horse_no), finish_rank=horse_no, result_status=None, horse_id=None)
        values.update(overrides)
        return RunnerCandidate(**values)

    def validate(self, rows, size=None):
        return validate_runner_candidates(rows, race_id=self.race_id, declared_field_size=size or len(rows))

    def test_accepts_unresolved_horse_ids_and_sorts_by_number(self):
        rows = self.validate([self.row(2), self.row(1)])
        self.assertEqual([r.horse_no for r in rows], [1, 2])
        self.assertIsNone(rows[0].horse_id)

    def test_rejects_runner_count_mismatch(self):
        with self.assertRaisesRegex(RunnerValidationError, "does not match"): self.validate([self.row(1)], 2)

    def test_rejects_duplicate_horse_number(self):
        with self.assertRaisesRegex(RunnerValidationError, "duplicate"): self.validate([self.row(1), self.row(1)])

    def test_rejects_number_outside_field_size(self):
        with self.assertRaisesRegex(RunnerValidationError, "outside"): self.validate([self.row(1), self.row(3)])

    def test_rejects_wrong_race_id(self):
        with self.assertRaisesRegex(RunnerValidationError, "does not match"): self.validate([self.row(1, race_id="202410010102")])

    def test_rejects_empty_name_and_raw_row(self):
        for changes in ({"horse_name": " "}, {"raw_row_text": ""}):
            with self.subTest(changes=changes), self.assertRaises(RunnerValidationError): self.validate([self.row(1, **changes)])

    def test_rejects_bad_hash_and_negative_page(self):
        for changes in ({"source_pdf_sha256": "bad"}, {"source_page_index": -1}):
            with self.subTest(changes=changes), self.assertRaises(RunnerValidationError): self.validate([self.row(1, **changes)])

    def test_rejects_numeric_rank_for_nonfinishers(self):
        for status in ("中", "失", "中止", "失格"):
            with self.subTest(status=status), self.assertRaisesRegex(RunnerValidationError, "cannot have numeric"): self.validate([self.row(1, result_status=status, finish_raw=status)])

    def test_requires_raw_finish_status(self):
        with self.assertRaisesRegex(RunnerValidationError, "raw finish text"): self.validate([self.row(1, result_status="降", finish_raw="")])

    def test_horse_id_may_be_null_but_not_guessed(self):
        with self.assertRaisesRegex(RunnerValidationError, "10-digit"): self.validate([self.row(1, horse_id="guess-name")])
        self.assertIsNone(self.validate([self.row(1, horse_id=None)])[0].horse_id)

    def test_rejects_invalid_finish_rank(self):
        for rank in (0, -1, 1.5, True):
            with self.subTest(rank=rank), self.assertRaisesRegex(RunnerValidationError, "positive integer"): self.validate([self.row(1, finish_rank=rank)])

if __name__ == "__main__": unittest.main()