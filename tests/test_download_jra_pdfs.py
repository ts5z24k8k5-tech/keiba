import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import download_jra_pdfs as downloader
from scripts.download_jra_pdfs import (ManifestError, validate_manifest, download_one, JRAOnlyRedirectHandler)

class DownloaderTests(unittest.TestCase):
    def test_redirect_handler_blocks_non_jra_and_http_targets(self):
        handler = JRAOnlyRedirectHandler()
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://www.jra.go.jp/datafile/seiseki/report/a.pdf"
        )
        for target in (
            "https://example.com/steal",
            "http://www.jra.go.jp/redirect.pdf",
            "https://www.jra.go.jp:8443/redirect.pdf",
            "https://user@www.jra.go.jp/redirect.pdf",
            "https://www.jra.go.jp:notaport/redirect.pdf",
            "https://www.jra.go.jp/other/redirect.pdf",
            "https://www.jra.go.jp/datafile/seiseki/report/readme.html",
        ):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_redirect_handler_allows_official_jra_https_target(self):
        handler = JRAOnlyRedirectHandler()
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            "https://www.jra.go.jp/datafile/seiseki/report/a.pdf"
        )
        redirected = handler.redirect_request(
            request, None, 302, "Found", {},
            "https://jra.go.jp/datafile/seiseki/report/b.pdf"
        )
        self.assertEqual(redirected.full_url, "https://jra.go.jp/datafile/seiseki/report/b.pdf")

    def write_manifest(self, path, rows):
        fields = ["pdf_url", "year", "venue", "date_start", "date_end",
                  "target_race_count", "target_race_ids", "locator_status"]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    def row(self, race_id="209908070901", url="https://www.jra.go.jp/datafile/seiseki/report/2099/2099-7kyoto9.pdf"):
        return {"pdf_url": url, "year": "2099", "venue": "kyoto",
                "date_start": "2099-12-28", "date_end": "2099-12-28",
                "target_race_count": "1", "target_race_ids": race_id,
                "locator_status": "official_pdf_url_web_open_verified"}

    def test_download_rejects_final_url_outside_result_pdf_path(self):
        body = b"%PDF-1.4" + b"x"*1500
        def fake(url, timeout):
            return body, 200, "application/pdf", "https://www.jra.go.jp/other/not-a-result.pdf"
        with tempfile.TemporaryDirectory() as d:
            r = download_one(self.row(), Path(d), retries=0, fetcher=fake, sleep=lambda _: None)
            self.assertEqual(r.status, "failed")
            self.assertIn("result-PDF policy", r.error)

    def test_manifest_validates_official_url_and_race_count(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row()])
            self.assertEqual(len(validate_manifest(p, expected_races=1)), 1)

    def test_rejects_duplicate_pdf_filename(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"
            rows = [
                self.row(),
                self.row(race_id="209908070902", url="https://www.jra.go.jp/datafile/seiseki/report/2099/other/2099-7kyoto9.pdf"),
            ]
            self.write_manifest(p, rows)
            with self.assertRaises(ManifestError):
                validate_manifest(p, expected_races=2)

    def test_rejects_nonstandard_port_and_userinfo(self):
        bad_urls = (
            "https://www.jra.go.jp:8443/datafile/seiseki/report/a.pdf",
            "https://user@www.jra.go.jp/datafile/seiseki/report/a.pdf",
            "https://www.jra.go.jp:notaport/datafile/seiseki/report/a.pdf",
        )
        for url in bad_urls:
            with self.subTest(url=url):
                with tempfile.TemporaryDirectory() as d:
                    p = Path(d)/"m.csv"
                    self.write_manifest(p, [self.row(url=url)])
                    with self.assertRaises(ManifestError):
                        validate_manifest(p, expected_races=1)

    def test_rejects_non_jra_host(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row(url="https://example.com/a.pdf")])
            with self.assertRaises(ManifestError): validate_manifest(p, 1)

    def test_rejects_duplicate_race_id(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"m.csv"; self.write_manifest(p, [self.row(), self.row(url="https://www.jra.go.jp/datafile/seiseki/report/2099/another.pdf")])
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

    def test_rejects_oversized_pdf_before_write(self):
        body = b"%PDF-1.4" + b"x" * 1500
        def fake(url, timeout): return body, 200, "application/pdf", url
        with tempfile.TemporaryDirectory() as d:
            with patch.object(downloader, "MAX_PDF_BYTES", 1500):
                result = download_one(self.row(), Path(d), retries=0, fetcher=fake, sleep=lambda _: None)
            self.assertEqual(result.status, "failed")
            self.assertIn("exceeds", result.error)
            self.assertFalse((Path(d) / "2099-7kyoto9.pdf").exists())

    def test_refuses_symlink_output_target(self):
        body = b"%PDF-1.4" + b"x" * 1500
        def fake(url, timeout): return body, 200, "application/pdf", url
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            protected = root / "protected.txt"
            protected.write_text("keep", encoding="utf-8")
            target = root / "2099-7kyoto9.pdf"
            target.symlink_to(protected)
            result = download_one(self.row(), root, retries=0, fetcher=fake, sleep=lambda _: None)
            self.assertEqual(result.status, "failed")
            self.assertIn("symlink", result.error)
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep")

if __name__ == "__main__": unittest.main()