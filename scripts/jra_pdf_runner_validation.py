"""Conservative validation for runner-row staging candidates.

This layer validates already-extracted fields. It does not parse PDF text,
resolve identities, or write to the production SQLite database.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


class RunnerValidationError(ValueError):
    """Raised when a race runner candidates fail staging acceptance checks."""


@dataclass(frozen=True)
class RunnerCandidate:
    race_id: str
    horse_no: int
    horse_name: str
    raw_row_text: str
    source_pdf_sha256: str
    source_page_index: int
    finish_raw: str = ""
    finish_rank: int | None = None
    result_status: str | None = None
    horse_id: str | None = None


def validate_runner_candidates(candidates: Iterable[RunnerCandidate], *, race_id: str, declared_field_size: int) -> list[RunnerCandidate]:
    """Validate one race without guessing missing values or dropping rows.

    horse_id may remain unresolved. Non-finish statuses 中 and 失 cannot
    carry a fabricated numeric finish rank. Demotion status 降 is preserved
    as raw status and may have a rank only when explicitly supplied.
    """
    rows = list(candidates)
    if not re.fullmatch(r"20\\d{10}", race_id):
        raise RunnerValidationError("race_id must be a 12-digit target ID")
    if declared_field_size < 1 or declared_field_size > 18:
        raise RunnerValidationError("declared field size must be between 1 and 18")
    if len(rows) != declared_field_size:
        raise RunnerValidationError(f"runner count {len(rows)} does not match declared field size {declared_field_size}")

    seen: set[int] = set()
    for row in rows:
        if row.race_id != race_id:
            raise RunnerValidationError("candidate race_id does not match target race")
        if not isinstance(row.horse_no, int) or isinstance(row.horse_no, bool):
            raise RunnerValidationError("horse_no must be an integer")
        if not 1 <= row.horse_no <= declared_field_size:
            raise RunnerValidationError("horse_no is outside declared field-size range")
        if row.horse_no in seen:
            raise RunnerValidationError(f"duplicate horse_no: {row.horse_no}")
        seen.add(row.horse_no)
        if not row.horse_name.strip():
            raise RunnerValidationError(f"horse_name is empty for horse_no {row.horse_no}")
        if not row.raw_row_text.strip():
            raise RunnerValidationError(f"raw row text is missing for horse_no {row.horse_no}")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", row.source_pdf_sha256):
            raise RunnerValidationError("source_pdf_sha256 must be a 64-character SHA-256 hex digest")
        if not isinstance(row.source_page_index, int) or row.source_page_index < 0:
            raise RunnerValidationError("source_page_index must be a non-negative integer")
        if row.finish_rank is not None and (not isinstance(row.finish_rank, int) or isinstance(row.finish_rank, bool) or row.finish_rank < 1):
            raise RunnerValidationError("finish_rank must be a positive integer or null")
        status = (row.result_status or "").strip()
        if status in {"中", "失", "中止", "失格"} and row.finish_rank is not None:
            raise RunnerValidationError(f"non-finisher/disqualified horse_no {row.horse_no} cannot have numeric finish_rank")
        if status and not row.finish_raw.strip():
            raise RunnerValidationError(f"raw finish text is required when result_status is set for horse_no {row.horse_no}")
        if row.horse_id is not None and not re.fullmatch(r"\\d{10}", row.horse_id):
            raise RunnerValidationError(f"horse_id must be an exact 10-digit ID or null for horse_no {row.horse_no}")
    return sorted(rows, key=lambda row: row.horse_no)