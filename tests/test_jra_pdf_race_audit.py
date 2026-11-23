import unittest

from scripts.jra_pdf_race_audit import (
    RaceAuditError, RaceAuditInput, audit_race, audit_summary_to_dict,
    build_audit_summary,
)
from scripts.jra_pdf_reconciliation import FieldDifference, ReconciliationReport


def report(horse_no, differences=()):
    return ReconciliationReport(
        race_id="209901010101", horse_no=horse_no,
        compared_fields=("finish_rank",), differences=tuple(differences)
    )


class RaceAuditTests(unittest.TestCase):
    def test_complete_and_fully_reconciled_race(self):
        result = audit_race(RaceAuditInput(
            "209901010101", 2, (1, 2), (report(1), report(2))
        ))
        self.assertTrue(result.structurally_complete)
        self.assertTrue(result.fully_reconciled)
        self.assertEqual(result.matched_runner_count, 2)

    def test_detects_missing_and_duplicate_horse_numbers(self):
        result = audit_race(RaceAuditInput(
            "209901010101", 3, (1, 1, 3), ()
        ))
        self.assertEqual(result.missing_horse_nos, (2,))
        self.assertEqual(result.duplicate_horse_nos, (1,))
        self.assertFalse(result.structurally_complete)

    def test_detects_mismatch_by_field(self):
        diff = FieldDifference("finish_rank", 3, 2, "mismatch")
        result = audit_race(RaceAuditInput(
            "209901010101", 1, (1,), (report(1, (diff,)),)
        ))
        self.assertEqual(result.mismatch_count_by_field, (("finish_rank", 1),))
        self.assertFalse(result.fully_reconciled)

    def test_counts_missing_extracted_and_reference_by_field(self):
        diffs = (
            FieldDifference("jockey_name", None, "騎手A", "missing_extracted"),
            FieldDifference("body_weight", 450, None, "missing_reference"),
        )
        result = audit_race(RaceAuditInput(
            "209901010101", 1, (1,), (report(1, diffs),)
        ))
        self.assertEqual(dict(result.missing_count_by_field), {
            "body_weight": 1, "jockey_name": 1
        })

    def test_uncompared_runner_prevents_full_reconciliation(self):
        result = audit_race(RaceAuditInput(
            "209901010101", 2, (1, 2), (report(1),)
        ))
        self.assertTrue(result.structurally_complete)
        self.assertFalse(result.fully_reconciled)
        self.assertEqual(result.unresolved_comparison_count, 1)

    def test_summary_reports_missing_expected_races(self):
        summary = build_audit_summary(
            ["209901010101", "209901010102"],
            [RaceAuditInput("209901010101", 1, (1,), (report(1),))]
        )
        self.assertEqual(summary.missing_race_ids, ("209901010102",))
        self.assertEqual(summary.expected_race_count, 2)
        self.assertEqual(summary.supplied_race_count, 1)

    def test_summary_serializes_to_plain_dictionary(self):
        summary = build_audit_summary(
            ["209901010101"],
            [RaceAuditInput("209901010101", 1, (1,), (report(1),))]
        )
        payload = audit_summary_to_dict(summary)
        self.assertEqual(payload["fully_reconciled_race_count"], 1)
        self.assertEqual(payload["races"][0]["race_id"], "209901010101")

    def test_rejects_duplicate_race_inputs(self):
        item = RaceAuditInput("209901010101", 1, (1,), ())
        with self.assertRaisesRegex(RaceAuditError, "duplicate race"):
            build_audit_summary(["209901010101"], [item, item])

    def test_rejects_non_integer_horse_number(self):
        with self.assertRaisesRegex(RaceAuditError, "must be integers"):
            audit_race(RaceAuditInput("209901010101", 1, ("1",), ()))

    def test_rejects_out_of_range_reconciliation_horse(self):
        with self.assertRaisesRegex(RaceAuditError, "outside expected field"):
            audit_race(RaceAuditInput(
                "209901010101", 1, (1,), (report(2),)
            ))


if __name__ == "__main__":
    unittest.main()
