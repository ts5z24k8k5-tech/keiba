"""Derive race-level next work from PDF batch status; no network or DB I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from scripts.jra_pdf_batch_progress import PdfBatch, PdfBatchProgressError, build_pdf_batch_summary
from scripts.jra_pdf_progress import (
    ProgressError, RaceProgress, build_progress_summary, progress_summary_to_dict,
)

class IntegrationError(ValueError):
    pass


def build_integrated_progress_report(payload: Any) -> dict[str, object]:
    if not isinstance(payload, dict) or set(payload) - {"expected_race_ids", "pdf_batches", "races"}:
        raise IntegrationError("root contains unsupported keys")
    if not {"expected_race_ids", "pdf_batches"} <= set(payload):
        raise IntegrationError("root requires expected_race_ids and pdf_batches")
    expected = payload["expected_race_ids"]
    raw_batches = payload["pdf_batches"]
    raw_races = payload.get("races", [])
    if not isinstance(raw_batches, list) or not isinstance(raw_races, list):
        raise IntegrationError("pdf_batches and races must be arrays")
    batches = []
    for i, item in enumerate(raw_batches):
        required = {"pdf_key", "race_ids", "status", "attempt_count"}
        allowed = required | {"failure_code", "sha256", "byte_count"}
        if not isinstance(item, dict) or not required <= set(item) or set(item) - allowed:
            raise IntegrationError(f"pdf_batches[{i}] has invalid keys")
        if not isinstance(item["race_ids"], list):
            raise IntegrationError(f"pdf_batches[{i}].race_ids must be an array")
        batches.append(PdfBatch(
            item["pdf_key"], tuple(item["race_ids"]), item["status"],
            item["attempt_count"], item.get("failure_code"),
            item.get("sha256"), item.get("byte_count"),
        ))
    try:
        pdf_summary = build_pdf_batch_summary(expected, batches)
    except (PdfBatchProgressError, TypeError) as exc:
        raise IntegrationError(str(exc)) from exc
    if pdf_summary.uncovered_race_ids or pdf_summary.multiply_mapped_race_ids:
        raise IntegrationError("PDF mapping must cover every expected race exactly once before integration")
    supplied = {}
    for i, item in enumerate(raw_races):
        if not isinstance(item, dict) or set(item) - {"race_id", "status", "note_code"} or not {"race_id", "status"} <= set(item):
            raise IntegrationError(f"races[{i}] has invalid keys")
        race_id = item["race_id"]
        if race_id in supplied:
            raise IntegrationError(f"duplicate race progress row: {race_id}")
        supplied[race_id] = RaceProgress(race_id, item["status"], item.get("note_code"))
    pdf_by_race = {race_id: batch for batch in batches for race_id in batch.race_ids}
    derived = []
    for race_id in expected:
        batch = pdf_by_race[race_id]
        existing = supplied.get(race_id)
        if batch.status in {"pending", "failed"}:
            if existing and existing.status not in {"pending", "blocked"}:
                raise IntegrationError(
                    f"race {race_id} is {existing.status} but its source PDF is {batch.status}"
                )
            derived.append(RaceProgress(
                race_id,
                "blocked" if batch.status == "failed" else "pending",
                "pdf_acquisition_failed" if batch.status == "failed" else "pdf_not_acquired",
            ))
        else:
            if existing and existing.status == "blocked" and existing.note_code in {
                "pdf_acquisition_failed", "pdf_not_acquired"
            }:
                derived.append(RaceProgress(race_id, "pdf_acquired", "pdf_recovered"))
            else:
                derived.append(existing or RaceProgress(race_id, "pdf_acquired", "pdf_verified"))
    try:
        race_summary = build_progress_summary(expected, derived)
    except ProgressError as exc:
        raise IntegrationError(str(exc)) from exc
    return {
        "pdf_batch_report": {
            "pdf_count": pdf_summary.pdf_count,
            "counts_by_status": dict(pdf_summary.counts_by_status),
            "retry_pdf_keys": list(pdf_summary.retry_pdf_keys),
            "covered_race_count": pdf_summary.covered_race_count,
        },
        "race_progress_report": progress_summary_to_dict(race_summary),
        "race_ids_requiring_source_pdf": sorted(
            race_id for race_id, batch in pdf_by_race.items()
            if batch.status in {"pending", "failed"}
        ),
        "promotion_authorized": False,
        "automatic_network_retry_performed": False,
    }
