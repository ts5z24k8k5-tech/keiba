import unittest

from scripts.jra_pdf_batch_progress import (
    PdfBatch, PdfBatchProgressError, build_pdf_batch_summary, pdf_batch_summary_to_dict,
)


class PdfBatchProgressTests(unittest.TestCase):
    def test_retry_list_contains_only_pending_and_failed_batches(self):
        summary = build_pdf_batch_summary(
            ["202410010101", "202410010102", "202410010103"],
            [
                PdfBatch("pdf-a", ("202410010101", "202410010102"), "validated", 1, sha256="a" * 64, byte_count=2048),
                PdfBatch("pdf-b", ("202410010103",), "failed", 2, "http_503"),
            ],
        )
        result = pdf_batch_summary_to_dict(summary)
        self.assertEqual(result["retry_pdf_keys"], ["pdf-b"])
        self.assertEqual(result["covered_race_count"], 3)
        self.assertEqual(result["counts_by_status"]["validated"], 1)
        self.assertFalse(result["automatic_network_retry_performed"])

    def test_uncovered_races_are_reported(self):
        summary = build_pdf_batch_summary(
            ["202410010101", "202410010102"],
            [PdfBatch("pdf-a", ("202410010101",), "pending", 0)],
        )
        self.assertEqual(summary.uncovered_race_ids, ("202410010102",))

    def test_duplicate_race_mapping_is_reported(self):
        summary = build_pdf_batch_summary(
            ["202410010101"],
            [PdfBatch("pdf-a", ("202410010101",)), PdfBatch("pdf-b", ("202410010101",))],
        )
        self.assertEqual(summary.multiply_mapped_race_ids, ("202410010101",))

    def test_unexpected_race_mapping_fails(self):
        with self.assertRaisesRegex(PdfBatchProgressError, "unexpected race IDs"):
            build_pdf_batch_summary(
                ["202410010101"], [PdfBatch("pdf-a", ("202410010999",))]
            )

    def test_failed_batch_requires_reason(self):
        with self.assertRaisesRegex(PdfBatchProgressError, "failure_code"):
            build_pdf_batch_summary(
                ["202410010101"], [PdfBatch("pdf-a", ("202410010101",), "failed", 1)]
            )

    def test_acquired_requires_attempt(self):
        with self.assertRaisesRegex(PdfBatchProgressError, "at least one attempt"):
            build_pdf_batch_summary(
                ["202410010101"], [PdfBatch("pdf-a", ("202410010101",), "acquired", 0)]
            )

    def test_acquired_requires_valid_sha256_and_size(self):
        for changes in ({"sha256": "bad", "byte_count": 2048}, {"sha256": "b" * 64, "byte_count": 100}):
            with self.subTest(changes=changes), self.assertRaises(PdfBatchProgressError):
                build_pdf_batch_summary(["202410010101"], [PdfBatch("pdf-a", ("202410010101",), "acquired", 1, **changes)])

    def test_successful_batch_serializes_integrity_metadata(self):
        summary = build_pdf_batch_summary(["202410010101"], [PdfBatch("pdf-a", ("202410010101",), "acquired", 1, sha256="c" * 64, byte_count=2048)])
        item = pdf_batch_summary_to_dict(summary)["batches"][0]
        self.assertEqual(item["sha256"], "c" * 64)
        self.assertEqual(item["byte_count"], 2048)

    def test_duplicate_race_within_pdf_fails(self):
        with self.assertRaisesRegex(PdfBatchProgressError, "duplicate race ID within PDF"):
            build_pdf_batch_summary(
                ["202410010101"], [PdfBatch("pdf-a", ("202410010101", "202410010101"))]
            )

    def test_duplicate_pdf_key_fails(self):
        row = PdfBatch("same", ("202410010101",))
        with self.assertRaisesRegex(PdfBatchProgressError, "duplicate pdf_key"):
            build_pdf_batch_summary(["202410010101"], [row, row])

    def test_bad_status_fails(self):
        with self.assertRaisesRegex(PdfBatchProgressError, "invalid PDF status"):
            build_pdf_batch_summary(
                ["202410010101"], [PdfBatch("pdf-a", ("202410010101",), "done")]
            )


if __name__ == "__main__":
    unittest.main()
