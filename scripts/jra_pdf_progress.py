"""Track per-race recovery workflow state without touching source data or SQLite."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


STAGES = ("pending", "pdf_acquired", "segmented", "extracted", "reconciled")
TERMINAL_REVIEW_STATES = {"manual_review", "blocked"}
ALLOWED_STATES = set(STAGES) | TERMINAL_REVIEW_STATES

NEXT_ACTION = {
    "pending": "acquire_source_pdf",
    "pdf_acquired": "segment_race_block",
    "segmented": "extract_runner_rows",
    "extracted": "reconcile_against_independent_source",
    "reconciled": "ready_for_separate_human_acceptance",
    "manual_review": "resolve_manual_review",
    "blocked": "resolve_blocker_before_retry",
}


class ProgressError(ValueError):
    pass


@dataclass(frozen=True)
class RaceProgress:
    race_id: str
    status: str = "pending"
    note_code: str | None = None


@dataclass(frozen=True)
class ProgressSummary:
    expected_race_count: int
    supplied_race_count: int
    missing_race_ids: tuple[str, ...]
    unexpected_race_ids: tuple[str, ...]
    counts_by_status: tuple[tuple[str, int], ...]
    next_actions_by_status: tuple[tuple[str, str], ...]
    races: tuple[RaceProgress, ...]


def _validate_id(value: str) -> None:
    if not isinstance(value, str) or len(value) != 12 or not value.isdigit():
        raise ProgressError("race_id must be a 12-digit string")


def validate_transition(current: str, target: str) -> None:
    if current not in ALLOWED_STATES or target not in ALLOWED_STATES:
        raise ProgressError("unknown progress state")
    if current in TERMINAL_REVIEW_STATES:
        if target not in {"manual_review", "blocked", "pending"}:
            raise ProgressError("review/blocked state must be resolved before advancing")
        return
    if target == "blocked" or target == "manual_review":
        return
    if target == "pending":
        if current == "pending":
            return
        raise ProgressError("reset to pending requires an explicit reviewed reset")
    if STAGES.index(target) != STAGES.index(current) + 1:
        raise ProgressError(f"invalid transition: {current} -> {target}")


def build_progress_summary(
    expected_race_ids: Sequence[str],
    progress_rows: Iterable[RaceProgress],
) -> ProgressSummary:
    if not expected_race_ids:
        raise ProgressError("expected_race_ids must not be empty")
    for race_id in expected_race_ids:
        _validate_id(race_id)
    if len(set(expected_race_ids)) != len(expected_race_ids):
        raise ProgressError("expected_race_ids must be unique")

    rows = list(progress_rows)
    for row in rows:
        _validate_id(row.race_id)
        if row.status not in ALLOWED_STATES:
            raise ProgressError(f"invalid status for {row.race_id}: {row.status}")
        if row.note_code is not None and (
            not isinstance(row.note_code, str) or not row.note_code.strip()
        ):
            raise ProgressError("note_code must be a non-empty string or null")
    ids = [row.race_id for row in rows]
    if len(set(ids)) != len(ids):
        raise ProgressError("duplicate progress rows")

    expected, supplied = set(expected_race_ids), set(ids)
    counts = Counter(row.status for row in rows)
    for state in ALLOWED_STATES:
        counts.setdefault(state, 0)
    ordered_counts = tuple((state, counts[state]) for state in (*STAGES, "manual_review", "blocked"))
    return ProgressSummary(
        expected_race_count=len(expected_race_ids),
        supplied_race_count=len(rows),
        missing_race_ids=tuple(sorted(expected - supplied)),
        unexpected_race_ids=tuple(sorted(supplied - expected)),
        counts_by_status=ordered_counts,
        next_actions_by_status=tuple(
            (state, NEXT_ACTION[state])
            for state, count in ordered_counts if count
        ),
        races=tuple(sorted(rows, key=lambda row: row.race_id)),
    )


def progress_summary_to_dict(summary: ProgressSummary) -> dict[str, object]:
    return {
        "expected_race_count": summary.expected_race_count,
        "supplied_race_count": summary.supplied_race_count,
        "missing_race_ids": list(summary.missing_race_ids),
        "unexpected_race_ids": list(summary.unexpected_race_ids),
        "counts_by_status": dict(summary.counts_by_status),
        "next_actions_by_status": dict(summary.next_actions_by_status),
        "races": [
            {"race_id": row.race_id, "status": row.status, "note_code": row.note_code,
             "next_action": NEXT_ACTION[row.status]}
            for row in summary.races
        ],
        "promotion_authorized": False,
    }
