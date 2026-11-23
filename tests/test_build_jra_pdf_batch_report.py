import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_jra_pdf_batch_report import PdfBatchProgressError, build_report, main


def payload():
    return {
        "expected_race_ids": ["202410010101", "202410010102"],
        "pdf_batches": [
            {"pdf_key": "pdf-a", "race_ids": ["202410010101"], "status": "acquired", "attempt_count": 1},
            {"pdf_key": "pdf-b", "race_ids": ["202410010102"], "status": "failed", "attempt_count": 2, "failure_code": "http_503"},
        ],
    }


class PdfBatchReportCliTests(unittest.TestCase):
    def test_retry_target_and_coverage(self):
        report = build_report(payload())
        self.assertEqual(report["retry_pdf_keys"], ["pdf-b"])
        self.assertEqual(report["covered_race_count"], 2)

    def test_rejects_unknown_root_key(self):
        data = payload()
        data["extra"] = True
        with self.assertRaisesRegex(PdfBatchProgressError, "exactly"):
            build_report(data)

    def test_rejects_unknown_batch_key(self):
        data = payload()
        data["pdf_batches"][0]["horse_names"] = ["private"]
        with self.assertRaisesRegex(PdfBatchProgressError, "invalid keys"):
            build_report(data)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "batches.json", Path(directory) / "report.json"
            source.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--output", str(target)]), 0)
            self.assertEqual(json.loads(target.read_text())["retry_pdf_keys"], ["pdf-b"])


if __name__ == "__main__":
    unittest.main()
