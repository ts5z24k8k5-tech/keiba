"""Derive race-level progress from PDF acquisition state; no network or DB I/O."""
from __future__ import annotations

from typing import Any

from scripts.jra_pdf_batch_progress import (
    PdfBatch, PdfBatchProgressError, build_pdf_batch_summary,
)
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
        if (not isinstance(item, dict)
                or set(item) - {"race_id", "status", "note_code"}
                or not {"race_id", "status"} <= set(item)):
            raise IntegrationError(f"races[{i}] has invalid keys")
        race_id = item["race_id"]
        if not isinstance(race_id, str):
            raise IntegrationError(f"races[{i}].race_id must be a string")
        if race_id in supplied:
            raise IntegrationError(f"duplicate race progress row: {race_id}")
        supplied[race_id] = RaceProgress(race_id, item["status"], item.get("note_code"))

    unexpected = set(supplied) - set(expected)
    if unexpected:
        raise IntegrationError(f"unexpected race progress IDs: {sorted(unexpected)}")

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
        elif existing and existing.status == "blocked" and existing.note_code in {
            "pdf_acquisition_failed", "pdf_not_acquired"
        }:
            derived.append(RaceProgress(race_id, "pdf_acquired", "pdf_recovered"))
        else:
            derived.append(existing or RaceProgress(race_id, "pdf_acquired", "pdf_verified"))

    try:
        race_summary = build_progress_summary(expected, derived)
    except ProgressError as exc:
        raise IntegrationError(str(exc)) from exc
    race_report = progress_summary_to_dict(race_summary)
    pdf_report = {
        "expected_race_count": pdf_summary.expected_race_count,
        "pdf_count": pdf_summary.pdf_count,
        "covered_race_count": pdf_summary.covered_race_count,
        "counts_by_status": dict(pdf_summary.counts_by_status),
        "retry_pdf_keys": list(pdf_summary.retry_pdf_keys),
        "retry_race_ids": sorted(
            race_id for race_id, batch in pdf_by_race.items()
            if batch.status in {"pending", "failed"}
        ),
    }
    return {
        "pdf_batch_report": pdf_report,
        "race_progress_report": race_report,
        "overall": {
            "expected_races": len(expected),
            "pdf_assets": len(batches),
            "races_blocked": race_report["counts_by_status"]["blocked"],
            "races_pending": race_report["counts_by_status"]["pending"],
            "races_ready_for_segmentation": race_report["counts_by_status"]["pdf_acquired"],
            "races_reconciled": race_report["counts_by_status"]["reconciled"],
            "source_pdf_retry_required": len(pdf_report["retry_pdf_keys"]),
        },
        "audit_flags": {
            "mapping_complete_exactly_once": True,
            "unexpected_race_progress": False,
            "state_conflicts": False,
        },
        "promotion_authorized": False,
        "automatic_network_retry_performed": False,
    }
