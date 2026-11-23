import unittest

from scripts.jra_pdf_progress import (
    ProgressError, RaceProgress, build_progress_summary,
    progress_summary_to_dict, validate_transition,
)


class RaceProgressTests(unittest.TestCase):
    def test_summary_counts_states_and_missing_ids(self):
        summary = build_progress_summary(
            ["202410010101", "202410010102", "202410010103"],
            [
                RaceProgress("202410010101", "segmented"),
                RaceProgress("202410010102", "manual_review", "row_count_mismatch"),
            ],
        )
        payload = progress_summary_to_dict(summary)
        self.assertEqual(payload["counts_by_status"]["segmented"], 1)
        self.assertEqual(payload["counts_by_status"]["manual_review"], 1)
        self.assertEqual(payload["missing_race_ids"], ["202410010103"])
        self.assertFalse(payload["promotion_authorized"])

    def test_unexpected_race_is_reported_not_silently_dropped(self):
        summary = build_progress_summary(
            ["202410010101"], [RaceProgress("202410010999", "pending")]
        )
        self.assertEqual(summary.unexpected_race_ids, ("202410010999",))

    def test_duplicate_progress_row_fails(self):
        row = RaceProgress("202410010101")
        with self.assertRaisesRegex(ProgressError, "duplicate progress"):
            build_progress_summary(["202410010101"], [row, row])

    def test_invalid_race_id_fails(self):
        with self.assertRaisesRegex(ProgressError, "12-digit"):
            build_progress_summary(["bad"], [])

    def test_sequential_transition_allowed(self):
        validate_transition("pending", "pdf_acquired")
        validate_transition("pdf_acquired", "segmented")
        validate_transition("extracted", "reconciled")

    def test_skipping_stage_fails(self):
        with self.assertRaisesRegex(ProgressError, "invalid transition"):
            validate_transition("pending", "extracted")

    def test_manual_review_can_only_be_resolved_or_kept(self):
        validate_transition("manual_review", "pending")
        with self.assertRaisesRegex(ProgressError, "resolved before advancing"):
            validate_transition("manual_review", "reconciled")

    def test_blocked_race_cannot_jump_forward(self):
        with self.assertRaisesRegex(ProgressError, "resolved before advancing"):
            validate_transition("blocked", "extracted")

    def test_progress_has_no_implicit_database_promotion(self):
        summary = build_progress_summary(
            ["202410010101"], [RaceProgress("202410010101", "reconciled")]
        )
        self.assertFalse(progress_summary_to_dict(summary)["promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
