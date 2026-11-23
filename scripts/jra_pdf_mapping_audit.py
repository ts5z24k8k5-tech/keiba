"""Cross-audit the per-race mapping against the PDF manifest; no network or DB I/O."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

MAPPING_REQUIRED = {"race_id", "date", "venue", "meeting_no", "meeting_day", "race_no", "pdf_url"}
MANIFEST_REQUIRED = {
    "pdf_url", "year", "venue", "date_start", "date_end",
    "target_race_count", "target_race_ids",
}
ALLOWED_HOSTS = {"www.jra.go.jp", "jra.go.jp"}


class MappingAuditError(ValueError):
    pass


def _valid_pdf_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_HOSTS
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and parsed.path.startswith("/datafile/seiseki/report/")
            and parsed.path.lower().endswith(".pdf")
        )
    except ValueError:
        return False


def _iso_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MappingAuditError(f"{label} must be an ISO date: {value!r}") from exc


def audit_race_pdf_mapping(
    mapping_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    expected_races: int = 149,
    expected_pdfs: int = 23,
) -> dict[str, object]:
    if not isinstance(mapping_rows, list) or not isinstance(manifest_rows, list):
        raise MappingAuditError("mapping_rows and manifest_rows must be lists")
    if expected_races < 1 or expected_pdfs < 1:
        raise MappingAuditError("expected counts must be positive")
    if not mapping_rows or not manifest_rows:
        raise MappingAuditError("mapping and manifest must both be non-empty")
    if not MAPPING_REQUIRED.issubset(mapping_rows[0]):
        raise MappingAuditError(f"mapping missing columns: {sorted(MAPPING_REQUIRED - set(mapping_rows[0]))}")
    if not MANIFEST_REQUIRED.issubset(manifest_rows[0]):
        raise MappingAuditError(f"manifest missing columns: {sorted(MANIFEST_REQUIRED - set(manifest_rows[0]))}")

    errors: list[dict[str, str]] = []
    def issue(code: str, key: str, detail: str) -> None:
        errors.append({"code": code, "key": key, "detail": detail})

    if len(mapping_rows) != expected_races:
        issue("mapping_row_count", "mapping", f"expected {expected_races}, found {len(mapping_rows)}")
    if len(manifest_rows) != expected_pdfs:
        issue("manifest_row_count", "manifest", f"expected {expected_pdfs}, found {len(manifest_rows)}")

    mapping_by_id: dict[str, dict[str, str]] = {}
    mapping_by_url: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(mapping_rows, 1):
        race_id = (row.get("race_id") or "").strip()
        url = (row.get("pdf_url") or "").strip()
        key = race_id or f"row:{index}"
        if not re.fullmatch(r"\d{12}", race_id):
            issue("malformed_race_id", key, "race_id must contain exactly 12 digits")
        elif race_id in mapping_by_id:
            issue("duplicate_race_id", race_id, "race_id occurs more than once in mapping")
        else:
            mapping_by_id[race_id] = row
        if not _valid_pdf_url(url):
            issue("invalid_jra_pdf_url", key, "URL is not an official JRA HTTPS result-PDF URL")
        else:
            mapping_by_url[url].append(row)
        try:
            race_date = _iso_date(row.get("date", ""), f"mapping row {index} date")
            if race_id and re.fullmatch(r"\d{12}", race_id):
                if race_id[:4] != str(race_date.year):
                    issue("race_year_mismatch", race_id, f"ID year {race_id[:4]} differs from date {race_date.year}")
                race_no = int(row.get("race_no", ""))
                if int(race_id[-2:]) != race_no:
                    issue("race_number_mismatch", race_id, f"ID suffix differs from race_no {race_no}")
        except (MappingAuditError, TypeError, ValueError) as exc:
            issue("invalid_mapping_metadata", key, str(exc))
        for field in ("meeting_no", "meeting_day", "race_no"):
            try:
                if int(row.get(field, "")) < 1:
                    raise ValueError
            except (TypeError, ValueError):
                issue("invalid_mapping_metadata", key, f"{field} must be a positive integer")

    manifest_by_url: dict[str, dict[str, str]] = {}
    for index, row in enumerate(manifest_rows, 1):
        url = (row.get("pdf_url") or "").strip()
        key = url or f"row:{index}"
        if not _valid_pdf_url(url):
            issue("invalid_jra_pdf_url", key, "URL is not an official JRA HTTPS result-PDF URL")
        if url in manifest_by_url:
            issue("duplicate_manifest_url", url, "PDF URL occurs more than once in manifest")
            continue
        manifest_by_url[url] = row
        try:
            start = _iso_date(row.get("date_start", ""), f"manifest row {index} date_start")
            end = _iso_date(row.get("date_end", ""), f"manifest row {index} date_end")
            if end < start:
                issue("invalid_manifest_date_range", url, "date_end precedes date_start")
            if not str(row.get("year", "")).isdigit() or int(row["year"]) != start.year:
                issue("manifest_year_mismatch", url, "manifest year differs from date_start year")
            ids = [part.strip() for part in (row.get("target_race_ids") or "").split(";") if part.strip()]
            declared = int(row.get("target_race_count", ""))
            if declared != len(ids):
                issue("manifest_target_count_mismatch", url, f"declared {declared}, listed {len(ids)}")
            if len(ids) != len(set(ids)):
                issue("duplicate_manifest_race_id", url, "target_race_ids contains duplicates")
            for race_id in ids:
                if not re.fullmatch(r"\d{12}", race_id):
                    issue("malformed_manifest_race_id", url, f"malformed race ID {race_id!r}")
            mapped = sorted(r.get("race_id", "").strip() for r in mapping_by_url.get(url, []))
            if sorted(ids) != mapped:
                issue("race_id_set_mismatch", url, f"manifest IDs ({len(ids)}) differ from mapping IDs ({len(mapped)})")
            for mapped_row in mapping_by_url.get(url, []):
                race_id = mapped_row.get("race_id", "").strip()
                venue = (mapped_row.get("venue") or "").strip().casefold()
                manifest_venue = (row.get("venue") or "").strip().casefold()
                if venue != manifest_venue:
                    issue("venue_mismatch", race_id, f"mapping venue {venue!r} differs from manifest {manifest_venue!r}")
                race_date = _iso_date(mapped_row.get("date", ""), f"mapping date for {race_id}")
                if not start <= race_date <= end:
                    issue("date_outside_pdf_range", race_id, f"{race_date} is outside {start}..{end}")
        except (MappingAuditError, TypeError, ValueError) as exc:
            issue("invalid_manifest_metadata", key, str(exc))

    for url in sorted(set(mapping_by_url) - set(manifest_by_url)):
        issue("mapping_url_missing_from_manifest", url, "mapping references a PDF absent from manifest")
    for url in sorted(set(manifest_by_url) - set(mapping_by_url)):
        issue("manifest_pdf_without_races", url, "manifest PDF has no race mapping")

    duplicate_id_count = sum(count > 1 for count in Counter(
        (row.get("race_id") or "").strip() for row in mapping_rows
    ).values())
    return {
        "audit_passed": not errors,
        "expected_races": expected_races,
        "mapping_rows": len(mapping_rows),
        "unique_race_ids": len(mapping_by_id),
        "expected_pdfs": expected_pdfs,
        "manifest_rows": len(manifest_rows),
        "unique_mapping_pdf_urls": len(mapping_by_url),
        "unique_manifest_pdf_urls": len(manifest_by_url),
        "duplicate_race_id_groups": duplicate_id_count,
        "errors": errors,
        "database_modified": False,
        "network_access_performed": False,
        "promotion_authorized": False,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-races", type=int, default=149)
    parser.add_argument("--expected-pdfs", type=int, default=23)
    args = parser.parse_args(argv)
    try:
        report = audit_race_pdf_mapping(
            _read_csv(args.mapping), _read_csv(args.manifest),
            args.expected_races, args.expected_pdfs,
        )
    except (OSError, csv.Error, UnicodeError, MappingAuditError) as exc:
        print(f"MAPPING AUDIT ERROR: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"mapping audit: passed={report['audit_passed']} races={report['unique_race_ids']} PDFs={report['unique_mapping_pdf_urls']} issues={len(report['errors'])}")
    return 0 if report["audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
