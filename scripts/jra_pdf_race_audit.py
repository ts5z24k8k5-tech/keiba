"""Aggregate race-level extraction and reconciliation quality without DB writes."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from scripts.jra_pdf_reconciliation import ReconciliationReport


class RaceAuditError(ValueError):
    pass


@dataclass(frozen=True)
class RaceAuditInput:
    race_id: str
    expected_runner_count: int
    extracted_horse_nos: tuple[int, ...]
    reconciliations: tuple[ReconciliationReport, ...]


@dataclass(frozen=True)
class RaceAuditResult:
    race_id: str
    expected_runner_count: int
    extracted_runner_count: int
    missing_horse_nos: tuple[int, ...]
    unexpected_horse_nos: tuple[int, ...]
    duplicate_horse_nos: tuple[int, ...]
    compared_runner_count: int
    matched_runner_count: int
    mismatch_count_by_field: tuple[tuple[str, int], ...]
    missing_count_by_field: tuple[tuple[str, int], ...]
    unresolved_comparison_count: int
    structurally_complete: bool
    fully_reconciled: bool


@dataclass(frozen=True)
class AuditSummary:
    expected_race_count: int
    supplied_race_count: int
    missing_race_ids: tuple[str, ...]
    unexpected_race_ids: tuple[str, ...]
    race_results: tuple[RaceAuditResult, ...]

    @property
    def structurally_complete_race_count(self) -> int:
        return sum(item.structurally_complete for item in self.race_results)

    @property
    def fully_reconciled_race_count(self) -> int:
        return sum(item.fully_reconciled for item in self.race_results)


def audit_race(item: RaceAuditInput) -> RaceAuditResult:
    if not item.race_id or item.expected_runner_count < 1 or item.expected_runner_count > 18:
        raise RaceAuditError("race_id and expected runner count 1..18 are required")
    horse_nos = item.extracted_horse_nos
    counts = Counter(horse_nos)
    duplicates = tuple(sorted(no for no, count in counts.items() if count > 1))
    missing = tuple(no for no in range(1, item.expected_runner_count + 1) if no not in counts)
    unexpected = tuple(sorted(no for no in counts if not isinstance(no, int) or no < 1 or no > item.expected_runner_count))

    seen_pairs: set[tuple[str, int]] = set()
    mismatch_by_field: Counter[str] = Counter()
    missing_by_field: Counter[str] = Counter()
    matched_runner_nos: set[int] = set()
    compared_runner_nos: set[int] = set()
    for report in item.reconciliations:
        if report.race_id != item.race_id:
            raise RaceAuditError("reconciliation report belongs to another race")
        pair = (report.race_id, report.horse_no)
        if pair in seen_pairs:
            raise RaceAuditError(f"duplicate reconciliation report for horse_no {report.horse_no}")
        seen_pairs.add(pair)
        compared_runner_nos.add(report.horse_no)
        if report.is_match:
            matched_runner_nos.add(report.horse_no)
        for difference in report.differences:
            if difference.status == "mismatch":
                mismatch_by_field[difference.field] += 1
            elif difference.status.startswith("missing_"):
                missing_by_field[difference.field] += 1

    structurally_complete = (
        len(horse_nos) == item.expected_runner_count
        and not missing and not unexpected and not duplicates
    )
    compared_complete = compared_runner_nos == set(range(1, item.expected_runner_count + 1))
    fully_reconciled = structurally_complete and compared_complete and len(matched_runner_nos) == item.expected_runner_count
    unresolved = item.expected_runner_count - len(compared_runner_nos.intersection(set(range(1, item.expected_runner_count + 1))))
    return RaceAuditResult(
        race_id=item.race_id,
        expected_runner_count=item.expected_runner_count,
        extracted_runner_count=len(horse_nos),
        missing_horse_nos=missing,
        unexpected_horse_nos=unexpected,
        duplicate_horse_nos=duplicates,
        compared_runner_count=len(compared_runner_nos),
        matched_runner_count=len(matched_runner_nos),
        mismatch_count_by_field=tuple(sorted(mismatch_by_field.items())),
        missing_count_by_field=tuple(sorted(missing_by_field.items())),
        unresolved_comparison_count=unresolved,
        structurally_complete=structurally_complete,
        fully_reconciled=fully_reconciled,
    )


def build_audit_summary(
    expected_race_ids: Sequence[str],
    race_inputs: Iterable[RaceAuditInput],
) -> AuditSummary:
    if not expected_race_ids or len(set(expected_race_ids)) != len(expected_race_ids):
        raise RaceAuditError("expected_race_ids must be non-empty and unique")
    supplied = list(race_inputs)
    supplied_ids = [item.race_id for item in supplied]
    if len(set(supplied_ids)) != len(supplied_ids):
        raise RaceAuditError("duplicate race audit input")
    expected_set, supplied_set = set(expected_race_ids), set(supplied_ids)
    results = tuple(audit_race(item) for item in sorted(supplied, key=lambda value: value.race_id))
    return AuditSummary(
        expected_race_count=len(expected_race_ids),
        supplied_race_count=len(supplied),
        missing_race_ids=tuple(sorted(expected_set - supplied_set)),
        unexpected_race_ids=tuple(sorted(supplied_set - expected_set)),
        race_results=results,
    )


def audit_summary_to_dict(summary: AuditSummary) -> dict[str, object]:
    return {
        "expected_race_count": summary.expected_race_count,
        "supplied_race_count": summary.supplied_race_count,
        "missing_race_ids": list(summary.missing_race_ids),
        "unexpected_race_ids": list(summary.unexpected_race_ids),
        "structurally_complete_race_count": summary.structurally_complete_race_count,
        "fully_reconciled_race_count": summary.fully_reconciled_race_count,
        "races": [
            {
                "race_id": row.race_id,
                "expected_runner_count": row.expected_runner_count,
                "extracted_runner_count": row.extracted_runner_count,
                "missing_horse_nos": list(row.missing_horse_nos),
                "unexpected_horse_nos": list(row.unexpected_horse_nos),
                "duplicate_horse_nos": list(row.duplicate_horse_nos),
                "compared_runner_count": row.compared_runner_count,
                "matched_runner_count": row.matched_runner_count,
                "mismatch_count_by_field": dict(row.mismatch_count_by_field),
                "missing_count_by_field": dict(row.missing_count_by_field),
                "unresolved_comparison_count": row.unresolved_comparison_count,
                "structurally_complete": row.structurally_complete,
                "fully_reconciled": row.fully_reconciled,
            }
            for row in summary.race_results
        ],
    }
