"""Track PDF-level acquisition batches and their race coverage; no network or DB I/O."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence


PDF_STATES = {"pending", "acquired", "validated", "failed"}
RETRYABLE_STATES = {"pending", "failed"}


class PdfBatchProgressError(ValueError):
    pass


@dataclass(frozen=True)
class PdfBatch:
    pdf_key: str
    race_ids: tuple[str, ...]
    status: str = "pending"
    attempt_count: int = 0
    failure_code: str | None = None


@dataclass(frozen=True)
class PdfBatchSummary:
    expected_race_count: int
    pdf_count: int
    covered_race_count: int
    uncovered_race_ids: tuple[str, ...]
    multiply_mapped_race_ids: tuple[str, ...]
    counts_by_status: tuple[tuple[str, int], ...]
    retry_pdf_keys: tuple[str, ...]
    batches: tuple[PdfBatch, ...]


def _race_id(value: str) -> None:
    if not isinstance(value, str) or len(value) != 12 or not value.isdigit():
        raise PdfBatchProgressError("race IDs must be 12-digit strings")


def build_pdf_batch_summary(
    expected_race_ids: Sequence[str], batches: Sequence[PdfBatch]
) -> PdfBatchSummary:
    if not expected_race_ids or len(set(expected_race_ids)) != len(expected_race_ids):
        raise PdfBatchProgressError("expected race IDs must be non-empty and unique")
    for race_id in expected_race_ids:
        _race_id(race_id)
    keys = [batch.pdf_key for batch in batches]
    if any(not isinstance(key, str) or not key.strip() for key in keys):
        raise PdfBatchProgressError("pdf_key must be a non-empty string")
    if len(set(keys)) != len(keys):
        raise PdfBatchProgressError("duplicate pdf_key")
    coverage: Counter[str] = Counter()
    for batch in batches:
        if batch.status not in PDF_STATES:
            raise PdfBatchProgressError(f"invalid PDF status: {batch.status}")
        if not isinstance(batch.attempt_count, int) or isinstance(batch.attempt_count, bool) or batch.attempt_count < 0:
            raise PdfBatchProgressError("attempt_count must be a non-negative integer")
        if batch.status in {"acquired", "validated"} and batch.attempt_count < 1:
            raise PdfBatchProgressError("acquired/validated PDF must have at least one attempt")
        if batch.status == "failed" and not batch.failure_code:
            raise PdfBatchProgressError("failed PDF requires a failure_code")
        if batch.status != "failed" and batch.failure_code is not None:
            raise PdfBatchProgressError("failure_code is only allowed for failed PDFs")
        if not batch.race_ids:
            raise PdfBatchProgressError("each PDF batch must map at least one race")
        if len(set(batch.race_ids)) != len(batch.race_ids):
            raise PdfBatchProgressError(f"duplicate race ID within PDF {batch.pdf_key}")
        for race_id in batch.race_ids:
            _race_id(race_id)
            coverage[race_id] += 1
    expected = set(expected_race_ids)
    uncovered = tuple(sorted(expected - set(coverage)))
    unexpected = set(coverage) - expected
    if unexpected:
        raise PdfBatchProgressError(f"unexpected race IDs in PDF mapping: {sorted(unexpected)}")
    multiply = tuple(sorted(race_id for race_id, count in coverage.items() if count > 1))
    counts = Counter(batch.status for batch in batches)
    ordered_counts = tuple((state, counts[state]) for state in ("pending", "acquired", "validated", "failed"))
    retry = tuple(sorted(batch.pdf_key for batch in batches if batch.status in RETRYABLE_STATES))
    return PdfBatchSummary(
        expected_race_count=len(expected_race_ids),
        pdf_count=len(batches),
        covered_race_count=sum(1 for race_id in expected if coverage[race_id] == 1),
        uncovered_race_ids=uncovered,
        multiply_mapped_race_ids=multiply,
        counts_by_status=ordered_counts,
        retry_pdf_keys=retry,
        batches=tuple(sorted(batches, key=lambda item: item.pdf_key)),
    )


def pdf_batch_summary_to_dict(summary: PdfBatchSummary) -> dict[str, object]:
    return {
        "expected_race_count": summary.expected_race_count,
        "pdf_count": summary.pdf_count,
        "covered_race_count": summary.covered_race_count,
        "uncovered_race_ids": list(summary.uncovered_race_ids),
        "multiply_mapped_race_ids": list(summary.multiply_mapped_race_ids),
        "counts_by_status": dict(summary.counts_by_status),
        "retry_pdf_keys": list(summary.retry_pdf_keys),
        "batches": [
            {
                "pdf_key": batch.pdf_key,
                "race_ids": list(batch.race_ids),
                "status": batch.status,
                "attempt_count": batch.attempt_count,
                "failure_code": batch.failure_code,
            }
            for batch in summary.batches
        ],
        "automatic_network_retry_performed": False,
        "promotion_authorized": False,
    }
