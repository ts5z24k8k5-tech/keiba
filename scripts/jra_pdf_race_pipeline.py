"""Compose geometry, explicit columns, field parsing, and row validation.

This is a candidate-building layer only. It never opens a PDF, guesses column
positions, resolves horse IDs, or writes to a database.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

from scripts.jra_pdf_columns import ColumnBand, split_row_into_columns
from scripts.jra_pdf_geometry import PositionedWord, TextRow, group_words_into_rows
from scripts.jra_pdf_runner_fields import ParsedRunnerFields, parse_runner_cells
from scripts.jra_pdf_runner_validation import (
    RunnerCandidate,
    validate_runner_candidates,
)


class RaceExtractionError(ValueError):
    """Raised when a race cannot be safely converted into runner candidates."""


@dataclass(frozen=True)
class RunnerExtraction:
    fields: ParsedRunnerFields
    candidate: RunnerCandidate


def build_race_candidates(
    rows: Sequence[TextRow],
    column_bands: Iterable[ColumnBand],
    *,
    race_id: str,
    declared_field_size: int,
    source_pdf_sha256: str,
    source_page_index: int,
) -> list[RunnerExtraction]:
    """Build and validate one race from already-grouped, already-located rows.

    The caller must remove non-runner headers/footers only through a separately
    reviewed row-selection rule. This function deliberately fails on any row
    that cannot be parsed; it never silently skips a row.
    """
    if not re.fullmatch(r"20\d{10}", race_id):
        raise RaceExtractionError("race_id must be a 12-digit target ID")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", source_pdf_sha256):
        raise RaceExtractionError("source_pdf_sha256 must be a SHA-256 hex digest")
    if not isinstance(source_page_index, int) or isinstance(source_page_index, bool) or source_page_index < 0:
        raise RaceExtractionError("source_page_index must be a non-negative integer")
    if not rows:
        raise RaceExtractionError("no runner rows supplied")

    bands = list(column_bands)
    if not bands:
        raise RaceExtractionError("at least one explicit column band is required")

    extracted: list[RunnerExtraction] = []
    candidates: list[RunnerCandidate] = []
    for index, row in enumerate(rows):
        try:
            cells = split_row_into_columns(row, bands, reject_unassigned=True)
            fields = parse_runner_cells(cells)
        except (ValueError, TypeError) as exc:
            raise RaceExtractionError(f"runner row {index} could not be parsed: {exc}") from exc

        candidate = RunnerCandidate(
            race_id=race_id,
            horse_no=fields.horse_no,
            horse_name=fields.horse_name,
            raw_row_text=row.text,
            source_pdf_sha256=source_pdf_sha256.lower(),
            source_page_index=source_page_index,
            finish_raw=fields.finish_raw or "",
            finish_rank=fields.finish_rank,
            result_status=fields.result_status,
            horse_id=None,
        )
        extracted.append(RunnerExtraction(fields=fields, candidate=candidate))
        candidates.append(candidate)

    try:
        validated = validate_runner_candidates(
            candidates,
            race_id=race_id,
            declared_field_size=declared_field_size,
        )
    except ValueError as exc:
        raise RaceExtractionError(f"race candidate validation failed: {exc}") from exc

    by_horse_no = {item.candidate.horse_no: item for item in extracted}
    return [by_horse_no[row.horse_no] for row in validated]


def group_page_words(
    words: Iterable[PositionedWord],
    *,
    baseline_tolerance: float = 2.5,
) -> list[TextRow]:
    """Convenience wrapper for coordinate grouping; no semantic row filtering."""
    return group_words_into_rows(words, baseline_tolerance=baseline_tolerance)
