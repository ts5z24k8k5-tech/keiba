import json
import tempfile
import unittest
from pathlib import Path

from scripts.jra_pdf_progress_integration import IntegrationError, build_integrated_progress_report
from scripts.build_jra_pdf_integrated_progress import main


def payload():
    return {
        "expected_race_ids": ["202410010101", "202410010102", "202410010103"],
        "pdf_batches": [
            {"pdf_key": "pdf-a", "race_ids": ["202410010101", "202410010102"], "status": "validated",
             "attempt_count": 1, "sha256": "a" * 64, "byte_count": 2048},
            {"pdf_key": "pdf-b", "race_ids": ["202410010103"], "status": "failed",
             "attempt_count": 2, "failure_code": "http_503"},
        ],
    }


class IntegratedProgressTests(unittest.TestCase):
    def test_failed_pdf_blocks_only_its_races(self):
        report = build_integrated_progress_report(payload())
        races = {row["race_id"]: row for row in report["race_progress_report"]["races"]}
        self.assertEqual(races["202410010101"]["status"], "pdf_acquired")
        self.assertEqual(races["202410010102"]["status"], "pdf_acquired")
        self.assertEqual(races["202410010103"]["status"], "blocked")
        self.assertEqual(report["race_ids_requiring_source_pdf"], ["202410010103"])
        self.assertFalse(report["promotion_authorized"])\n        self.assertEqual(report["overall"]["expected_races"], 3)\n        self.assertEqual(report["overall"]["races_blocked"], 1)\n        self.assertEqual(report["overall"]["races_ready_for_segmentation"], 2)\n        self.assertEqual(report["pdf_batch_report"]["retry_race_ids"], ["202410010103"])

    def test_recovered_pdf_unblocks_its_races(self):
        data = payload()
        data["pdf_batches"][1] = {
            "pdf_key": "pdf-b", "race_ids": ["202410010103"], "status": "validated",
            "attempt_count": 3, "sha256": "b" * 64, "byte_count": 3000,
        }
        data["races"] = [{"race_id": "202410010103", "status": "blocked",
                          "note_code": "pdf_acquisition_failed"}]
        report = build_integrated_progress_report(data)
        row = next(r for r in report["race_progress_report"]["races"] if r["race_id"] == "202410010103")
        self.assertEqual(row["status"], "pdf_acquired")
        self.assertEqual(row["note_code"], "pdf_recovered")

    def test_pending_pdf_marks_only_its_races_pending(self):
        data = payload()
        data["pdf_batches"][1] = {
            "pdf_key": "pdf-b", "race_ids": ["202410010103"], "status": "pending", "attempt_count": 0
        }
        report = build_integrated_progress_report(data)
        row = next(r for r in report["race_progress_report"]["races"] if r["race_id"] == "202410010103")
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["note_code"], "pdf_not_acquired")

    def test_mapping_must_cover_every_race_once(self):
        data = payload()
        data["pdf_batches"][1]["race_ids"] = []
        with self.assertRaises(IntegrationError):
            build_integrated_progress_report(data)

    def test_progress_beyond_pdf_stage_conflicts_with_failed_pdf(self):
        data = payload()
        data["races"] = [{"race_id": "202410010103", "status": "segmented"}]
        with self.assertRaisesRegex(IntegrationError, "source PDF is failed"):
            build_integrated_progress_report(data)

    def test_unexpected_progress_race_rejected(self):
        data = payload()
        data["races"] = [{"race_id": "202410019999", "status": "pending"}]
        with self.assertRaisesRegex(IntegrationError, "unexpected race progress"):
            build_integrated_progress_report(data)

    def test_consolidated_audit_counts_match_race_and_pdf_ledgers(self):\n        data = payload()\n        data["pdf_batches"][1] = {\n            "pdf_key": "pdf-b", "race_ids": ["202410010103"], "status": "pending", "attempt_count": 0\n        }\n        report = build_integrated_progress_report(data)\n        self.assertEqual(report["overall"]["pdf_assets"], 2)\n        self.assertEqual(report["overall"]["source_pdf_retry_required"], 2)\n        self.assertEqual(report["overall"]["races_pending"], 1)\n        self.assertTrue(report["audit_flags"]["mapping_complete_exactly_once"])\n\n    def test_cli_writes_integrated_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.json", Path(directory) / "out.json"
            source.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--output", str(target)]), 0)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["race_ids_requiring_source_pdf"], ["202410010103"])


if __name__ == "__main__":
    unittest.main()
