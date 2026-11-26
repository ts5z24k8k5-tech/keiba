"""Build a local PDF-batch progress report from private mapping/status JSON."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts.jra_pdf_batch_progress import (
    PdfBatch, PdfBatchProgressError, build_pdf_batch_summary, pdf_batch_summary_to_dict,
)

RACE_ID_RE = re.compile(r"^\d{12}$")
ALLOWED_KEYS = {"pdf_key", "race_ids", "status", "attempt_count", "failure_code", "sha256", "byte_count"}


def build_report(payload: Any) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) != {"expected_race_ids", "pdf_batches"}:
        raise PdfBatchProgressError("root must contain exactly expected_race_ids and pdf_batches")
    expected = payload["expected_race_ids"]
    raw_batches = payload["pdf_batches"]
    if not isinstance(expected, list) or not expected:
        raise PdfBatchProgressError("expected_race_ids must be a non-empty array")
    if any(not isinstance(item, str) or not RACE_ID_RE.fullmatch(item) for item in expected):
        raise PdfBatchProgressError("expected race IDs must be 12-digit strings")
    if not isinstance(raw_batches, list):
        raise PdfBatchProgressError("pdf_batches must be an array")
    batches = []
    for index, item in enumerate(raw_batches):
        label = f"pdf_batches[{index}]"
        if not isinstance(item, dict) or set(item) - ALLOWED_KEYS or not {"pdf_key", "race_ids", "status", "attempt_count"} <= set(item):
            raise PdfBatchProgressError(f"{label} has invalid keys")
        if not isinstance(item["race_ids"], list) or any(not isinstance(r, str) for r in item["race_ids"]):
            raise PdfBatchProgressError(f"{label}.race_ids must be a string array")
        batches.append(PdfBatch(
            item["pdf_key"], tuple(item["race_ids"]), item["status"],
            item["attempt_count"], item.get("failure_code"), item.get("sha256"), item.get("byte_count"),
        ))
    summary = build_pdf_batch_summary(expected, batches)
    return pdf_batch_summary_to_dict(summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local JRA PDF batch progress report.")
    parser.add_argument("--input", required=True, type=Path, help="private PDF mapping/status JSON")
    parser.add_argument("--output", required=True, type=Path, help="batch progress JSON")
    args = parser.parse_args(argv)
    if args.output.is_symlink():
        parser.error("--output must not be a symlink")
    if args.input.resolve() == args.output.resolve():
        parser.error("--input and --output must be different files")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = build_report(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, PdfBatchProgressError) as exc:
        print(f"PDF batch report failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"PDF batch report written: PDFs={report['pdf_count']} "
        f"races_covered_once={report['covered_race_count']} "
        f"retry_targets={len(report['retry_pdf_keys'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
