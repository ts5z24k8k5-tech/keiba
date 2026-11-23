"""Tests for the local-only JRA PDF aggregate audit CLI."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_jra_pdf_audit_report import (
    AuditInputError,
    build_report_from_payload,
    main,
)


def valid_payload():
    return {
        "expected_race_ids": ["202410010101", "202410010102"],
        "races": [
            {
                "race_id": "202410010101",
                "expected_runner_count": 2,
                "extracted_horse_nos": [1, 2],
                "reconciliations": [
                    {
                        "race_id": "202410010101",
                        "horse_no": 1,
                        "compared_fields": ["finish_rank"],
                        "differences": [],
                    },
                    {
                        "race_id": "202410010101",
                        "horse_no": 2,
                        "compared_fields": ["finish_rank"],
                        "differences": [
                            {
                                "field": "finish_rank",
                                "extracted": 3,
                                "reference": 2,
                                "status": "mismatch",
                            }
                        ],
                    },
                ],
            }
        ],
    }


class BuildAuditReportTests(unittest.TestCase):
    def test_report_contains_missing_race_and_field_mismatch(self):
        report = build_report_from_payload(valid_payload())
        self.assertEqual(report["expected_race_count"], 2)
        self.assertEqual(report["supplied_race_count"], 1)
        self.assertEqual(report["missing_race_ids"], ["202410010102"])
        self.assertEqual(report["fully_reconciled_race_count"], 0)
        self.assertEqual(report["races"][0]["mismatch_count_by_field"], {"finish_rank": 1})

    def test_complete_race_is_marked_fully_reconciled(self):
        payload = valid_payload()
        payload["expected_race_ids"] = ["202410010101"]
        payload["races"][0]["reconciliations"][1]["differences"] = []
        report = build_report_from_payload(payload)
        self.assertEqual(report["fully_reconciled_race_count"], 1)

    def test_rejects_unknown_keys(self):
        payload = valid_payload()
        payload["races"][0]["unreviewed"] = True
        with self.assertRaisesRegex(AuditInputError, "keys invalid"):
            build_report_from_payload(payload)

    def test_rejects_malformed_race_id(self):
        payload = valid_payload()
        payload["expected_race_ids"] = ["race-one"]
        with self.assertRaisesRegex(AuditInputError, "12-digit"):
            build_report_from_payload(payload)

    def test_rejects_invalid_difference_status(self):
        payload = valid_payload()
        payload["races"][0]["reconciliations"][1]["differences"][0]["status"] = "close_enough"
        with self.assertRaisesRegex(AuditInputError, "status is invalid"):
            build_report_from_payload(payload)

    def test_rejects_difference_for_unrequested_field(self):
        payload = valid_payload()
        payload["races"][0]["reconciliations"][1]["differences"][0]["field"] = "odds"
        with self.assertRaisesRegex(AuditInputError, "not in compared_fields"):
            build_report_from_payload(payload)

    def test_cli_writes_report_without_modifying_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "private.json"
            target = Path(directory) / "report.json"
            original = json.dumps(valid_payload(), ensure_ascii=False)
            source.write_text(original, encoding="utf-8")
            result = main(["--input", str(source), "--output", str(target)])
            self.assertEqual(result, 0)
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            output = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(output["missing_race_ids"], ["202410010102"])

    def test_cli_rejects_same_input_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "same.json"
            source.write_text("{}", encoding="utf-8")
            with self.assertRaises(SystemExit):
                main(["--input", str(source), "--output", str(source)])


if __name__ == "__main__":
    unittest.main()
