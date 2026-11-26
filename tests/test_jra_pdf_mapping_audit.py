import json
import tempfile
import unittest
from pathlib import Path

from scripts.jra_pdf_mapping_audit import MappingAuditError, audit_race_pdf_mapping, main


def fixtures():
    url_a = "https://www.jra.go.jp/datafile/seiseki/report/2099/2099-7kyoto1.pdf"
    url_b = "https://www.jra.go.jp/datafile/seiseki/report/2099/2099-7kyoto2.pdf"
    mapping = [
        {"race_id": "209908070101", "date": "2099-11-30", "venue": "kyoto", "meeting_no": "7",
         "meeting_day": "1", "race_no": "1", "pdf_url": url_a},
        {"race_id": "209908070102", "date": "2099-11-30", "venue": "kyoto", "meeting_no": "7",
         "meeting_day": "1", "race_no": "2", "pdf_url": url_a},
        {"race_id": "209908070201", "date": "2099-12-01", "venue": "kyoto", "meeting_no": "7",
         "meeting_day": "2", "race_no": "1", "pdf_url": url_b},
    ]
    manifest = [
        {"pdf_url": url_a, "year": "2099", "venue": "kyoto", "date_start": "2099-11-30",
         "date_end": "2099-11-30", "target_race_count": "2",
         "target_race_ids": "209908070101;209908070102"},
        {"pdf_url": url_b, "year": "2099", "venue": "kyoto", "date_start": "2099-12-01",
         "date_end": "2099-12-01", "target_race_count": "1", "target_race_ids": "209908070201"},
    ]
    return mapping, manifest


class MappingAuditTests(unittest.TestCase):
    def test_exact_mapping_passes(self):
        mapping, manifest = fixtures()
        report = audit_race_pdf_mapping(mapping, manifest, 3, 2)
        self.assertTrue(report["audit_passed"])
        self.assertEqual(report["unique_race_ids"], 3)
        self.assertEqual(report["unique_mapping_pdf_urls"], 2)
        self.assertEqual(report["errors"], [])

    def test_duplicate_race_id_is_reported(self):
        mapping, manifest = fixtures()
        mapping.append(dict(mapping[0]))
        report = audit_race_pdf_mapping(mapping, manifest, 4, 2)
        self.assertIn("duplicate_race_id", {e["code"] for e in report["errors"]})

    def test_manifest_race_set_mismatch_is_reported(self):
        mapping, manifest = fixtures()
        manifest[0]["target_race_ids"] = "209908070101;209908070199"
        report = audit_race_pdf_mapping(mapping, manifest, 3, 2)
        self.assertIn("race_id_set_mismatch", {e["code"] for e in report["errors"]})

    def test_pdf_metadata_mismatch_is_reported(self):
        mapping, manifest = fixtures()
        mapping[0]["venue"] = "fukushima"
        report = audit_race_pdf_mapping(mapping, manifest, 3, 2)
        self.assertIn("venue_mismatch", {e["code"] for e in report["errors"]})

    def test_date_outside_pdf_range_is_reported(self):
        mapping, manifest = fixtures()
        mapping[0]["date"] = "2099-12-02"
        report = audit_race_pdf_mapping(mapping, manifest, 3, 2)
        self.assertIn("date_outside_pdf_range", {e["code"] for e in report["errors"]})

    def test_non_jra_url_is_rejected_in_report(self):
        mapping, manifest = fixtures()
        mapping[0]["pdf_url"] = "https://example.com/not-jra.pdf"
        report = audit_race_pdf_mapping(mapping, manifest, 3, 2)
        self.assertIn("invalid_jra_pdf_url", {e["code"] for e in report["errors"]})

    def test_rejects_missing_required_columns(self):
        with self.assertRaises(MappingAuditError):
            audit_race_pdf_mapping([{"race_id": "1"}], [{"pdf_url": "x"}], 1, 1)

    def test_missing_required_column_is_detected_even_with_extra_columns(self):
        mapping, manifest = fixtures()
        mapping[0].pop("race_no")
        mapping[0]["extra"] = "value"
        with self.assertRaisesRegex(MappingAuditError, "mapping missing columns"):
            audit_race_pdf_mapping(mapping, manifest, 3, 2)

    def test_cli_writes_report_and_returns_success(self):
        mapping, manifest = fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            m, f, out = root / "mapping.csv", root / "manifest.csv", root / "report.json"
            for path, rows in ((m, mapping), (f, manifest)):
                import csv
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
            self.assertEqual(main(["--mapping", str(m), "--manifest", str(f),
                                   "--expected-races", "3", "--expected-pdfs", "2",
                                   "--output", str(out)]), 0)
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["audit_passed"])

    def test_cli_refuses_output_that_is_an_input_or_symlink(self):
        mapping, manifest = fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mapping_path, manifest_path = root / "mapping.csv", root / "manifest.csv"
            for path, rows in ((mapping_path, mapping), (manifest_path, manifest)):
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
            before = mapping_path.read_bytes()
            with self.assertRaises(SystemExit):
                main(["--mapping", str(mapping_path), "--manifest", str(manifest_path),
                      "--output", str(mapping_path)])
            self.assertEqual(mapping_path.read_bytes(), before)

            protected = root / "protected.json"
            protected.write_text("keep", encoding="utf-8")
            link = root / "report.json"
            link.symlink_to(protected)
            with self.assertRaises(SystemExit):
                main(["--mapping", str(mapping_path), "--manifest", str(manifest_path),
                      "--output", str(link)])
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
