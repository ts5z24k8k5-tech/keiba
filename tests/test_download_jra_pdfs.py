import csv
import tempfile
import unittest
from pathlib import Path

from scripts.download_jra_pdfs import ManifestError, validate_manifest, download_one

class DownloaderTests(unittest.TestCase):
    def write_manifest(self, path, rows):
        fields = ["pdf_url", "year", "venue", "date_start", "date_end",
                  "target_race_count", "target_race_ids", "locator_status"]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    def row(self, race_id="202408070901", url="https://www.jra.go.jp/datafile/seiseki/report/2024/2024-7kyoto9.pdf"):
        return {"pdf_url": url, "year": "2024", "venue": "kyoto",
                "date_start": "2024-12-28", "date_end": "2024-12-28",
                "target_race_count": "1", "target_race_ids": race_id,
                "locator_status": "official_pdf_url_web_open_verified"}

    def test_manifest_validates_official_url_and_race_count(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row()])
            self.assertEqual(len(validate_manifest(p, expected_races=1)), 1)

    def test_rejects_non_jra_host(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row(url="https://example.com/a.pdf")])
            with self.assertRaises(ManifestError): validate_manifest(p, 1)

    def test_rejects_duplicate_race_id(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row(), self.row(url="https://www.jra.go.jp/datafile/seiseki/report/2024/another.pdf")])
            with self.assertRaises(ManifestError): validate_manifest(p, 2)

    def test_download_saves_pdf_and_hash(self):
        body = b"%PDF-1.4" + b"x"*1500
        def fake(url, timeout): return body, 200, "application/pdf", url
        with tempfile.TemporaryDirectory() as d:
            r = download_one(self.row(), Path(d), fetcher=fake, sleep=lambda _: None)
            self.assertEqual(r.status, "downloaded")
            self.assertEqual(r.bytes, len(body))
            self.assertEqual((Path(d)/r.filename).read_bytes(), body)
            self.assertEqual(len(r.sha256), 64)

    def test_rejects_html_disguised_as_pdf(self):
        def fake(url, timeout): return b"<html>" + b"x"*1500, 200, "text/html", url
        with tempfile.TemporaryDirectory() as d:
            r = download_one(self.row(), Path(d), retries=0, fetcher=fake, sleep=lambda _: None)
            self.assertEqual(r.status, "failed")
            self.assertIn("PDF signature", r.error)

if __name__ == "__main__": unittest.main()