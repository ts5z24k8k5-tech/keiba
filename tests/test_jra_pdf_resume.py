import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.download_jra_pdfs import load_prior_download_audit, reuse_verified_pdf


class VerifiedResumeTests(unittest.TestCase):
    URL = "https://www.jra.go.jp/datafile/seiseki/report/2024/resume-test.pdf"
    ROW = {"pdf_url": URL}

    def setup_asset(self, directory, *, status="downloaded", digest=None, byte_count=None, filename="resume-test.pdf"):
        body = b"%PDF-1.7\n" + b"x" * 1500
        target = Path(directory) / "resume-test.pdf"
        target.write_bytes(body)
        fields = ["pdf_url", "filename", "status", "bytes", "sha256", "http_status", "content_type"]
        with (Path(directory) / "download_audit.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "pdf_url": self.URL, "filename": filename, "status": status,
                "bytes": len(body) if byte_count is None else byte_count,
                "sha256": hashlib.sha256(body).hexdigest() if digest is None else digest,
                "http_status": 200, "content_type": "application/pdf",
            })
        return body

    def test_reuses_only_exact_hash_and_size_match(self):
        with tempfile.TemporaryDirectory() as directory:
            body = self.setup_asset(directory)
            prior = load_prior_download_audit(Path(directory))
            result = reuse_verified_pdf(self.ROW, Path(directory), prior)
            self.assertEqual(result.status, "already_verified")
            self.assertEqual(result.bytes, len(body))
            self.assertEqual(result.sha256, hashlib.sha256(body).hexdigest())

    def test_modified_file_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_asset(directory)
            target = Path(directory) / "resume-test.pdf"
            target.write_bytes(b"%PDF-1.7\n" + b"y" * 1500)
            result = reuse_verified_pdf(self.ROW, Path(directory), load_prior_download_audit(Path(directory)))
            self.assertIsNone(result)

    def test_missing_file_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_asset(directory)
            (Path(directory) / "resume-test.pdf").unlink()
            result = reuse_verified_pdf(self.ROW, Path(directory), load_prior_download_audit(Path(directory)))
            self.assertIsNone(result)

    def test_failed_audit_row_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_asset(directory, status="failed")
            self.assertEqual(load_prior_download_audit(Path(directory)), {})

    def test_duplicate_audit_urls_are_ambiguous_and_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_asset(directory)
            path = Path(directory) / "download_audit.csv"
            with path.open("a", encoding="utf-8") as stream:
                stream.write(f"{self.URL},resume-test.pdf,downloaded,1508," + "a" * 64 + ",200,application/pdf\n")
            self.assertNotIn(self.URL, load_prior_download_audit(Path(directory)))

    def test_wrong_filename_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.setup_asset(directory, filename="other.pdf")
            result = reuse_verified_pdf(self.ROW, Path(directory), load_prior_download_audit(Path(directory)))
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
