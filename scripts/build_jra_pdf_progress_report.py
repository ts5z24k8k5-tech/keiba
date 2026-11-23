"""Create a local progress report from private race-status JSON."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts.jra_pdf_progress import (
    ProgressError, RaceProgress, build_progress_summary, progress_summary_to_dict,
)

RACE_ID_RE = re.compile(r"^\d{12}$")
STATES = {"pending", "pdf_acquired", "segmented", "extracted", "reconciled", "manual_review", "blocked"}


def build_report(payload: Any) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) != {"expected_race_ids", "races"}:
        raise ProgressError("root must contain exactly expected_race_ids and races")
    expected = payload["expected_race_ids"]
    races = payload["races"]
    if not isinstance(expected, list) or not expected:
        raise ProgressError("expected_race_ids must be a non-empty array")
    if any(not isinstance(item, str) or not RACE_ID_RE.fullmatch(item) for item in expected):
        raise ProgressError("every expected race_id must be a 12-digit string")
    if not isinstance(races, list):
        raise ProgressError("races must be an array")
    rows = []
    for index, item in enumerate(races):
        label = f"races[{index}]"
        if not isinstance(item, dict) or set(item) - {"race_id", "status", "note_code"} or not {"race_id", "status"} <= set(item):
            raise ProgressError(f"{label} has invalid keys")
        race_id, status, note_code = item["race_id"], item["status"], item.get("note_code")
        if not isinstance(race_id, str) or not RACE_ID_RE.fullmatch(race_id):
            raise ProgressError(f"{label}.race_id must be a 12-digit string")
        if not isinstance(status, str) or status not in STATES:
            raise ProgressError(f"{label}.status is invalid")
        if note_code is not None and (not isinstance(note_code, str) or not note_code.strip()):
            raise ProgressError(f"{label}.note_code must be a non-empty string or null")
        rows.append(RaceProgress(race_id, status, note_code))
    summary = build_progress_summary(expected, rows)
    return progress_summary_to_dict(summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local JRA race recovery progress report.")
    parser.add_argument("--input", required=True, type=Path, help="private progress JSON")
    parser.add_argument("--output", required=True, type=Path, help="progress report JSON")
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("--input and --output must be different files")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = build_report(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ProgressError) as exc:
        print(f"progress report failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"progress written: expected={report['expected_race_count']} "
        f"supplied={report['supplied_race_count']} "
        f"missing={len(report['missing_race_ids'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
