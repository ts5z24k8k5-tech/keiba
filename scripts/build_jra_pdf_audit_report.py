"""Build a local-only JSON quality report from private JRA PDF staging data.

The input contains private race/runner fields and must stay outside this repository.
This tool reads JSON and writes an aggregate audit report; it never touches SQLite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts.jra_pdf_race_audit import (
    RaceAuditInput,
    audit_summary_to_dict,
    build_audit_summary,
)
from scripts.jra_pdf_reconciliation import FieldDifference, ReconciliationReport


RACE_ID_RE = re.compile(r"^\d{12}$")
DIFFERENCE_STATUSES = {"mismatch", "missing_extracted", "missing_reference"}


class AuditInputError(ValueError):
    """Raised when a local audit JSON file does not match the strict schema."""


def _object(value: Any, required: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditInputError(f"{label} must be a JSON object")
    missing = required - set(value)
    extra = set(value) - required
    if missing or extra:
        raise AuditInputError(
            f"{label} keys invalid; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return value


def _race_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not RACE_ID_RE.fullmatch(value):
        raise AuditInputError(f"{label} must be a 12-digit string")
    return value


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AuditInputError(f"{label} must be a non-empty JSON array")
    if any(not isinstance(item, str) or not item for item in value):
        raise AuditInputError(f"{label} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise AuditInputError(f"{label} must not contain duplicates")
    return tuple(value)


def load_audit_payload(payload: Any) -> tuple[tuple[str, ...], tuple[RaceAuditInput, ...]]:
    """Validate and convert the documented private JSON staging schema."""
    root = _object(payload, {"expected_race_ids", "races"}, "root")
    expected_ids = _string_list(root["expected_race_ids"], "expected_race_ids")
    for index, race_id in enumerate(expected_ids):
        _race_id(race_id, f"expected_race_ids[{index}]")

    if not isinstance(root["races"], list):
        raise AuditInputError("races must be a JSON array")

    race_inputs: list[RaceAuditInput] = []
    for index, raw_race in enumerate(root["races"]):
        label = f"races[{index}]"
        race = _object(
            raw_race,
            {"race_id", "expected_runner_count", "extracted_horse_nos", "reconciliations"},
            label,
        )
        race_id = _race_id(race["race_id"], f"{label}.race_id")
        count = race["expected_runner_count"]
        if not isinstance(count, int) or isinstance(count, bool):
            raise AuditInputError(f"{label}.expected_runner_count must be an integer")
        horse_nos = race["extracted_horse_nos"]
        if not isinstance(horse_nos, list) or any(
            not isinstance(number, int) or isinstance(number, bool) for number in horse_nos
        ):
            raise AuditInputError(f"{label}.extracted_horse_nos must be an integer array")
        raw_reports = race["reconciliations"]
        if not isinstance(raw_reports, list):
            raise AuditInputError(f"{label}.reconciliations must be an array")

        reports: list[ReconciliationReport] = []
        for report_index, raw_report in enumerate(raw_reports):
            report_label = f"{label}.reconciliations[{report_index}]"
            report = _object(
                raw_report,
                {"race_id", "horse_no", "compared_fields", "differences"},
                report_label,
            )
            report_race_id = _race_id(report["race_id"], f"{report_label}.race_id")
            horse_no = report["horse_no"]
            if not isinstance(horse_no, int) or isinstance(horse_no, bool):
                raise AuditInputError(f"{report_label}.horse_no must be an integer")
            compared_fields = report["compared_fields"]
            if not isinstance(compared_fields, list) or not compared_fields or any(
                not isinstance(field, str) or not field for field in compared_fields
            ):
                raise AuditInputError(f"{report_label}.compared_fields must be a string array")
            if len(set(compared_fields)) != len(compared_fields):
                raise AuditInputError(f"{report_label}.compared_fields must be unique")
            raw_differences = report["differences"]
            if not isinstance(raw_differences, list):
                raise AuditInputError(f"{report_label}.differences must be an array")
            differences: list[FieldDifference] = []
            for diff_index, raw_diff in enumerate(raw_differences):
                diff_label = f"{report_label}.differences[{diff_index}]"
                diff = _object(
                    raw_diff, {"field", "extracted", "reference", "status"}, diff_label
                )
                if not isinstance(diff["field"], str) or not diff["field"]:
                    raise AuditInputError(f"{diff_label}.field must be a non-empty string")
                if diff["field"] not in compared_fields:
                    raise AuditInputError(f"{diff_label}.field is not in compared_fields")
                if not isinstance(diff["status"], str) or diff["status"] not in DIFFERENCE_STATUSES:
                    raise AuditInputError(f"{diff_label}.status is invalid")
                differences.append(
                    FieldDifference(
                        diff["field"], diff["extracted"], diff["reference"], diff["status"]
                    )
                )
            reports.append(
                ReconciliationReport(
                    report_race_id, horse_no, tuple(compared_fields), tuple(differences)
                )
            )
        race_inputs.append(
            RaceAuditInput(race_id, count, tuple(horse_nos), tuple(reports))
        )

    return expected_ids, tuple(race_inputs)


def build_report_from_payload(payload: Any) -> dict[str, object]:
    expected_ids, race_inputs = load_audit_payload(payload)
    summary = build_audit_summary(expected_ids, race_inputs)
    return audit_summary_to_dict(summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a local JSON quality audit from private JRA PDF staging JSON."
    )
    parser.add_argument("--input", required=True, type=Path, help="private staging JSON")
    parser.add_argument("--output", required=True, type=Path, help="aggregate audit JSON")
    args = parser.parse_args(argv)

    if args.input.resolve() == args.output.resolve():
        parser.error("--input and --output must be different files")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = build_report_from_payload(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, AuditInputError, ValueError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2

    print(
        "audit written: "
        f"expected={report['expected_race_count']} "
        f"supplied={report['supplied_race_count']} "
        f"missing={len(report['missing_race_ids'])} "
        f"structurally_complete={report['structurally_complete_race_count']} "
        f"fully_reconciled={report['fully_reconciled_race_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
