#!/usr/bin/env python3
"""Download and verify official JRA result PDFs from a reviewed manifest.

This tool only downloads source PDFs and writes an acquisition audit. It never
opens or modifies the historical SQLite database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

REQUIRED = {
    "pdf_url", "year", "venue", "date_start", "date_end",
    "target_race_count", "target_race_ids", "locator_status",
}
ALLOWED_HOSTS = {"www.jra.go.jp", "jra.go.jp"}
USER_AGENT = "Mozilla/5.0 (compatible; JRAHistoricalPDFResearch/1.0)"


class ManifestError(ValueError):
    pass


@dataclass
class Result:
    pdf_url: str
    filename: str
    status: str
    http_status: int | None = None
    bytes: int = 0
    sha256: str | None = None
    content_type: str | None = None
    error: str | None = None


def validate_manifest(path: Path, expected_races: int = 149) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            missing = sorted(REQUIRED - set(reader.fieldnames or []))
            raise ManifestError(f"missing columns: {missing}")
        rows = list(reader)
    if not rows:
        raise ManifestError("manifest is empty")

    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    counted = 0
    for i, row in enumerate(rows, 2):
        url = (row.get("pdf_url") or "").strip()
        p = urlparse(url)
        if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS:
            raise ManifestError(f"row {i}: URL must be HTTPS on official JRA host")
        if not p.path.startswith("/datafile/seiseki/report/") or not p.path.lower().endswith(".pdf"):
            raise ManifestError(f"row {i}: URL is not an official result PDF path")
        if url in seen_urls:
            raise ManifestError(f"row {i}: duplicate PDF URL")
        seen_urls.add(url)
        ids = [x.strip() for x in (row.get("target_race_ids") or "").split(";") if x.strip()]
        try:
            declared = int(row["target_race_count"])
        except (TypeError, ValueError):
            raise ManifestError(f"row {i}: invalid target_race_count")
        if declared != len(ids):
            raise ManifestError(f"row {i}: target_race_count does not match target_race_ids")
        for race_id in ids:
            if not race_id.isdigit() or len(race_id) != 12:
                raise ManifestError(f"row {i}: malformed race_id {race_id!r}")
            if race_id in seen_ids:
                raise ManifestError(f"row {i}: duplicate race_id {race_id}")
            seen_ids.add(race_id)
        counted += len(ids)
    if counted != expected_races:
        raise ManifestError(f"expected {expected_races} race IDs, found {counted}")
    return rows


def _fetch(url: str, timeout: int) -> tuple[bytes, int, str, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.8"})
    with urlopen(req, timeout=timeout) as response:
        final_url = response.geturl()
        if urlparse(final_url).hostname not in ALLOWED_HOSTS:
            raise ValueError(f"redirected outside JRA host: {final_url}")
        body = response.read()
        return body, int(response.status), response.headers.get("Content-Type", ""), final_url


def download_one(row: dict[str, str], out_dir: Path, timeout: int = 30,
                 retries: int = 3, fetcher: Callable = _fetch,
                 sleep: Callable[[float], None] = time.sleep) -> Result:
    url = row["pdf_url"].strip()
    filename = Path(urlparse(url).path).name
    last_error = None
    for attempt in range(retries + 1):
        try:
            body, status, content_type, final_url = fetcher(url, timeout)
            if urlparse(final_url).hostname not in ALLOWED_HOSTS:
                raise ValueError("final URL is outside official JRA host")
            if status != 200:
                raise ValueError(f"unexpected HTTP status {status}")
            if not body.startswith(b"%PDF-"):
                raise ValueError("response does not begin with PDF signature")
            if len(body) < 1024:
                raise ValueError(f"PDF payload suspiciously small: {len(body)} bytes")
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / filename
            tmp = target.with_suffix(target.suffix + ".part")
            tmp.write_bytes(body)
            os.replace(tmp, target)
            return Result(url, filename, "downloaded", status, len(body),
                          hashlib.sha256(body).hexdigest(), content_type)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                sleep(min(2 ** attempt, 8))
    return Result(url, filename, "failed", error=last_error)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--expected-races", type=int, default=149)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between PDFs")
    args = ap.parse_args()

    try:
        rows = validate_manifest(args.manifest, args.expected_races)
    except (OSError, ManifestError) as exc:
        print(f"MANIFEST ERROR: {exc}", file=sys.stderr)
        return 2

    results: list[Result] = []
    for i, row in enumerate(rows):
        result = download_one(row, args.out, args.timeout, args.retries)
        results.append(result)
        print(f"[{i+1}/{len(rows)}] {result.status}: {result.filename}"
              + (f" ({result.bytes} bytes)" if result.status == "downloaded" else f" — {result.error}"))
        if i + 1 < len(rows) and args.delay > 0:
            time.sleep(args.delay + random.uniform(0, min(args.delay * 0.2, 0.5)))

    args.out.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(results[0]).keys()) if results else []
    with (args.out / "download_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(asdict(x) for x in results)
    summary = {
        "manifest": str(args.manifest), "pdf_files_expected": len(rows),
        "pdf_files_downloaded": sum(x.status == "downloaded" for x in results),
        "pdf_files_failed": sum(x.status == "failed" for x in results),
        "target_races": args.expected_races,
        "database_modified": False,
        "results": [asdict(x) for x in results],
    }
    (args.out / "download_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if summary["pdf_files_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())