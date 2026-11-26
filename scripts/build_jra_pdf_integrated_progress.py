"""Build integrated PDF-to-race progress report from private JSON."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from scripts.jra_pdf_progress_integration import IntegrationError, build_integrated_progress_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build integrated JRA PDF/race progress report.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.is_symlink():
        parser.error("--output must not be a symlink")
    if args.input.resolve() == args.output.resolve():
        parser.error("--input and --output must be different files")
    try:
        report = build_integrated_progress_report(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, IntegrationError) as exc:
        print(f"Integrated progress report failed: {exc}", file=sys.stderr)
        return 2
    print(f"Integrated report written: PDFs={report['pdf_batch_report']['pdf_count']} "
          f"races={report['race_progress_report']['expected_race_count']} "
          f"need_source_pdf={len(report['race_ids_requiring_source_pdf'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
