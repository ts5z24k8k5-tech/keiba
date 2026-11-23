import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_jra_pdf_progress_report import ProgressError, build_report, main


def payload():
    return {
        "expected_race_ids": ["202410010101", "202410010102"],
        "races": [
            {"race_id": "202410010101", "status": "pdf_acquired"},
            {"race_id": "202410010102", "status": "manual_review", "note_code": "header_mismatch"},
        ],
    }


class ProgressReportCliTests(unittest.TestCase):
    def test_builds_counts_and_next_actions(self):
        report = build_report(payload())
        self.assertEqual(report["counts_by_status"]["pdf_acquired"], 1)
        self.assertEqual(report["next_actions_by_status"]["segment_race_block"], "segment_race_block")
        self.assertEqual(report["races"][1]["next_action"], "resolve_manual_review")

    def test_rejects_unknown_root_key(self):
        data = payload()
        data["private_text"] = "should not be accepted"
        with self.assertRaisesRegex(ProgressError, "exactly"):
            build_report(data)

    def test_rejects_unknown_race_key(self):
        data = payload()
        data["races"][0]["horse_names"] = ["private"]
        with self.assertRaisesRegex(ProgressError, "invalid keys"):
            build_report(data)

    def test_rejects_invalid_status(self):
        data = payload()
        data["races"][0]["status"] = "done"
        with self.assertRaisesRegex(ProgressError, "status is invalid"):
            build_report(data)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "progress.json", Path(directory) / "report.json"
            source.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--output", str(target)]), 0)
            self.assertEqual(json.loads(target.read_text())["supplied_race_count"], 2)


if __name__ == "__main__":
    unittest.main()
