#!/usr/bin/env python3
"""Create a privacy-conscious geometry audit for locally acquired JRA PDFs.

Only aggregate page/layout metrics and the source PDF hash are written. No
horse names, jockey names, odds, raw text, or database data are emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Callable

from scripts.jra_pdf_geometry import group_words_into_rows, positioned_words_from_pymupdf


def inspect_pdf(path: Path, opener: Callable | None = None) -> dict:
    if opener is None:
        try:
            import pymupdf
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required: install the pinned dependency from requirements.txt") from exc
        opener = fitz.open

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pages = []
    document = opener(str(path))
    try:
        for page_index, page in enumerate(document):
            words = positioned_words_from_pymupdf(page.get_text("words"))
            rows = group_words_into_rows(words)
            widths = [len(row.words) for row in rows]
            rect = page.rect
            pages.append({
                "page_index": page_index,
                "width_points": round(float(rect.width), 2),
                "height_points": round(float(rect.height), 2),
                "word_count": len(words),
                "row_count": len(rows),
                "median_words_per_row": round(statistics.median(widths), 2) if widths else 0,
                "max_words_per_row": max(widths, default=0),
            })
    finally:
        close = getattr(document, "close", None)
        if callable(close):
            close()

    return {
        "filename": path.name,
        "sha256": digest,
        "page_count": len(pages),
        "total_words": sum(page["word_count"] for page in pages),
        "total_rows": sum(page["row_count"] for page in pages),
        "pages": pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(args.pdf_dir.glob("*.pdf"))
    if not files:
        parser.error(f"no PDF files found in {args.pdf_dir}")

    reports = []
    failures = []
    for path in files:
        try:
            reports.append(inspect_pdf(path))
        except Exception as exc:
            failures.append({"filename": path.name, "error": f"{type(exc).__name__}: {exc}"})

    result = {
        "pdf_count": len(files),
        "inspected_count": len(reports),
        "failed_count": len(failures),
        "raw_text_emitted": False,
        "database_modified": False,
        "reports": reports,
        "failures": failures,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Inspected {len(reports)}/{len(files)} PDFs; failures={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
