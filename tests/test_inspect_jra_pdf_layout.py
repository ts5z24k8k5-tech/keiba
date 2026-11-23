import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.inspect_jra_pdf_layout import inspect_pdf


class FakePage:
    rect = SimpleNamespace(width=595.0, height=842.0)

    def get_text(self, mode):
        self.mode = mode
        return [
            (10, 10, 20, 20, "horse-secret-name", 0, 0, 0),
            (30, 10, 40, 20, "jockey-secret-name", 0, 0, 1),
            (10, 30, 20, 40, "another-secret-name", 0, 0, 2),
        ]


class FakeDocument(list):
    def close(self):
        self.closed = True


class LayoutAuditTests(unittest.TestCase):
    def test_reports_aggregate_geometry_without_raw_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pdf"
            payload = b"%PDF-test-fixture"
            path.write_bytes(payload)
            document = FakeDocument([FakePage()])
            report = inspect_pdf(path, opener=lambda _: document)

            self.assertEqual(report["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(report["page_count"], 1)
            self.assertEqual(report["total_words"], 3)
            self.assertEqual(report["total_rows"], 2)
            self.assertNotIn("horse-secret-name", repr(report))
            self.assertNotIn("jockey-secret-name", repr(report))
            self.assertTrue(document.closed)

    def test_empty_pdf_document_has_zero_page_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.pdf"
            path.write_bytes(b"%PDF-empty")
            report = inspect_pdf(path, opener=lambda _: FakeDocument())
            self.assertEqual(report["page_count"], 0)
            self.assertEqual(report["total_words"], 0)


if __name__ == "__main__":
    unittest.main()
