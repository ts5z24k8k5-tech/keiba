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
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REQUIRED = {
    "pdf_url", "year", "venue", "date_start", "date_end",
    "target_race_count", "target_race_ids", "locator_status",
}
ALLOWED_HOSTS = {"www.jra.go.jp", "jra.go.jp"}
USER_AGENT = "Mozilla/5.0 (compatible; JRAHistoricalPDFResearch/1.0)"

def _is_allowed_jra_url(url: str) -> bool:
    """Accept only HTTPS URLs to official JRA hosts on the standard port."""
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS
                and parsed.port in (None, 443) and parsed.username is None
                and parsed.password is None)
    except ValueError:
        return False


def _is_allowed_jra_pdf_url(url: str) -> bool:
    """Require the official result-PDF directory, including after redirects."""
    if not _is_allowed_jra_url(url):
        return False
    path = urlparse(url).path.lower()
    return path.startswith("/datafile/seiseki/report/") and path.endswith(".pdf")



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


def validate_manifest(path: Path, expected_races: int = 149, expected_pdfs: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            missing = sorted(REQUIRED - set(reader.fieldnames or []))
            raise ManifestError(f"missing columns: {missing}")
        rows = list(reader)
    if not rows:
        raise ManifestError("manifest is empty")
    if expected_pdfs is not None and len(rows) != expected_pdfs:
        raise ManifestError(f"expected {expected_pdfs} PDF rows, found {len(rows)}")

    seen_urls: set[str] = set()
    seen_filenames: set[str] = set()
    seen_ids: set[str] = set()
    counted = 0
    for i, row in enumerate(rows, 2):
        url = (row.get("pdf_url") or "").strip()
        p = urlparse(url)
        if not _is_allowed_jra_pdf_url(url):
            raise ManifestError(f"row {i}: URL must use HTTPS on an official JRA host and standard port")
        if not p.path.startswith("/datafile/seiseki/report/") or not p.path.lower().endswith(".pdf"):
            raise ManifestError(f"row {i}: URL is not an official result PDF path")
        if url in seen_urls:
            raise ManifestError(f"row {i}: duplicate PDF URL")
        seen_urls.add(url)
        filename = Path(p.path).name
        if not filename or filename in seen_filenames:
            raise ManifestError(f"row {i}: empty or duplicate PDF filename {filename!r}")
        seen_filenames.add(filename)
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


class JRAOnlyRedirectHandler(HTTPRedirectHandler):
    """Reject non-HTTPS or non-JRA redirects before following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_allowed_jra_pdf_url(newurl):
            raise ValueError(f"blocked redirect outside official JRA HTTPS hosts/port: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, timeout: int) -> tuple[bytes, int, str, str]:
    if not _is_allowed_jra_pdf_url(url):
        raise ValueError("source URL must be an official JRA HTTPS result-PDF URL")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.8"})
    opener = build_opener(JRAOnlyRedirectHandler())
    with opener.open(req, timeout=timeout) as response:
        final_url = response.geturl()
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
            if not _is_allowed_jra_pdf_url(final_url):
                raise ValueError("final URL is outside official JRA HTTPS result-PDF policy")
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


def load_prior_download_audit(out_dir: Path) -> dict[str, dict[str, str]]:
    """Load only unambiguous successful rows from a previous local audit."""
    audit_path = out_dir / "download_audit.csv"
    if not audit_path.is_file():
        return {}
    try:
        with audit_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except (OSError, csv.Error, UnicodeError):
        return {}
    verified: dict[str, dict[str, str]] = {}
    ambiguous: set[str] = set()
    for row in rows:
        url = (row.get("pdf_url") or "").strip()
        digest = (row.get("sha256") or "").strip().lower()
        if not url or row.get("status") != "downloaded":
            continue
        if url in verified:
            ambiguous.add(url)
            verified.pop(url, None)
            continue
        if url in ambiguous:
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            continue
        try:
            byte_count = int(row.get("bytes") or "0")
        except ValueError:
            continue
        if byte_count < 1024:
            continue
        verified[url] = row
    return verified


def reuse_verified_pdf(row: dict[str, str], out_dir: Path,
                       prior: dict[str, dict[str, str]]) -> Result | None:
    """Reuse a local PDF only when prior audit identity, size, signature and SHA match."""
    url = row["pdf_url"].strip()
    filename = Path(urlparse(url).path).name
    previous = prior.get(url)
    if not previous or previous.get("filename") != filename:
        return None
    target = out_dir / filename
    try:
        if not target.is_file():
            return None
        body = target.read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(body).hexdigest()
    try:
        expected_bytes = int(previous.get("bytes") or "0")
    except ValueError:
        return None
    if (not body.startswith(b"%PDF-") or len(body) < 1024
            or len(body) != expected_bytes
            or digest != (previous.get("sha256") or "").lower()):
        return None
    return Result(url, filename, "already_verified", previous.get("http_status") and int(previous["http_status"]),
                  len(body), digest, previous.get("content_type"), None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--expected-races", type=int, default=149)
    ap.add_argument("--expected-pdfs", type=int, default=23)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between PDFs")
    ap.add_argument("--resume", action="store_true",
                    help="reuse only local PDFs whose prior audit SHA-256 and size still match")
    args = ap.parse_args()

    try:
        rows = validate_manifest(args.manifest, args.expected_races, args.expected_pdfs)
    except (OSError, ManifestError) as exc:
        print(f"MANIFEST ERROR: {exc}", file=sys.stderr)
        return 2

    results: list[Result] = []
    prior_audit = load_prior_download_audit(args.out) if args.resume else {}
    for i, row in enumerate(rows):
        result = reuse_verified_pdf(row, args.out, prior_audit) if args.resume else None
        if result is None:
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
        "pdf_files_reused_verified": sum(x.status == "already_verified" for x in results),
        "pdf_files_failed": sum(x.status == "failed" for x in results),
        "resume_enabled": args.resume,
        "target_races": args.expected_races,
        "database_modified": False,
        "results": [asdict(x) for x in results],
    }
    (args.out / "download_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if summary["pdf_files_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())