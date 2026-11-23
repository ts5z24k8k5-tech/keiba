#!/usr/bin/env python3
"""Read-only validator for a clean-history migration export.

The manifest is a reviewed path allowlist. This tool never copies, deletes,
rewrites, or uploads export files. Exit status is non-zero on any finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_PARTS = {
    "results", "private_input", "private-input", "output", "outputs",
    "data", "datasets", "snapshots", "models", "logs", "cache", "__pycache__",
    ".git", ".ssh", ".aws", ".gnupg", "credentials", "secrets",
}
FORBIDDEN_SUFFIXES = (
    ".pdf", ".sqlite", ".sqlite3", ".db", ".parquet", ".pkl", ".pickle",
    ".joblib", ".onnx", ".pt", ".pth", ".h5", ".csv", ".json",
)
ALLOWED_SOURCE_SUFFIXES = {".py", ".md", ".yml"}
FORBIDDEN_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials", "secrets.json",
}


def fail(message: str) -> ValueError:
    return ValueError(message)


def validate_manifest(data: object) -> tuple[dict[str, dict], list[str]]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise fail("manifest must be an object with schema_version=1")
    source = data.get("source")
    if not isinstance(source, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
        raise fail("manifest source.commit must be a 40-character lowercase SHA")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise fail("manifest entries must be a non-empty list")
    allowed: dict[str, dict] = {}
    errors: list[str] = []
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise fail(f"entries[{index}] must be an object")
        path = item.get("path")
        if not isinstance(path, str) or not path or "\\" in path:
            raise fail(f"entries[{index}].path is invalid")
        pure = PurePosixPath(path)
        if pure.is_absolute() or PureWindowsPath(path).drive or any(part in ("", ".", "..") for part in path.split("/")) or any(ord(ch) < 32 for ch in path):
            raise fail(f"entries[{index}].path is unsafe: {path!r}")
        if path in seen or path.casefold() in seen_casefold:
            raise fail(f"duplicate manifest path or case-colliding path: {path}")
        seen.add(path)
        seen_casefold.add(path.casefold())
        if not SHA1_RE.fullmatch(str(item.get("source_git_blob_sha1", ""))):
            raise fail(f"invalid source Git blob SHA-1 for {path}")
        if not isinstance(item.get("source_bytes"), int) or item["source_bytes"] < 0:
            raise fail(f"invalid source byte count for {path}")
        status = item.get("status")
        valid_statuses = {"ALLOW_CANDIDATE", "OPTIONAL_INCLUDE", "REWRITE_REQUIRED", "ALLOW_AFTER_ADAPTATION"}
        if status not in valid_statuses:
            raise fail(f"invalid or missing status for {path}")
        export = item.get("export")
        if not isinstance(export, bool):
            raise fail(f"export must be boolean for {path}")
        if export and status not in {"ALLOW_CANDIDATE", "OPTIONAL_INCLUDE"}:
            raise fail(f"status {status} cannot be exported without a reviewed manifest update: {path}")
        digest = item.get("expected_sha256")
        if digest is not None and not SHA256_RE.fullmatch(str(digest)):
            raise fail(f"invalid expected_sha256 for {path}")
        if export:
            allowed[path] = item
    if not allowed:
        raise fail("manifest contains no export=true entries")
    return allowed, errors


def forbidden_reason(rel: str) -> str | None:
    parts = rel.split("/")
    lower_parts = [p.lower() for p in parts]
    name = parts[-1].lower()
    if any(p in FORBIDDEN_PARTS for p in lower_parts):
        return "excluded directory/pattern"
    if name in FORBIDDEN_NAMES or name.startswith(".env."):
        return "credential/environment file"
    if name.endswith(FORBIDDEN_SUFFIXES):
        return "excluded data/binary file type"
    if Path(name).suffix.lower() not in ALLOWED_SOURCE_SUFFIXES and name != ".gitignore":
        return "file type is outside the source-only export policy"
    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "credential/key material"
    return None


def walk_export(root: Path) -> tuple[set[str], list[str]]:
    found: set[str] = set()
    findings: list[str] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(f"SYMLINK_REJECTED: {rel}")
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            findings.append(f"NON_REGULAR_FILE: {rel}")
            continue
        reason = forbidden_reason(rel)
        if reason:
            findings.append(f"EXCLUDED_PATH: {rel} ({reason})")
        found.add(rel)
    return found, findings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_export(root: Path, manifest_path: Path) -> dict:
    if not root.exists() or not root.is_dir():
        raise fail(f"export root is not a directory: {root}")
    if root.is_symlink():
        raise fail("export root must not be a symlink")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise fail(f"cannot read manifest: {exc}") from exc
    allowed, _ = validate_manifest(data)
    found, findings = walk_export(root)
    expected_paths = set(allowed)
    for missing in sorted(expected_paths - found):
        findings.append(f"MISSING_FILE: {missing}")
    for extra in sorted(found - expected_paths):
        findings.append(f"UNAUTHORIZED_FILE: {extra}")
    checked = 0
    for rel in sorted(expected_paths & found):
        item = allowed[rel]
        path = root.joinpath(*rel.split("/"))
        if path.is_symlink() or not path.is_file():
            continue
        actual_size = path.stat().st_size
        if actual_size != item["source_bytes"]:
            findings.append(f"SIZE_MISMATCH: {rel}: expected={item['source_bytes']} actual={actual_size}")
        actual_digest = sha256_file(path)
        checked += 1
        expected_digest = item.get("expected_sha256")
        if expected_digest is None:
            findings.append(f"SHA256_UNPINNED: {rel}: actual={actual_digest}")
            continue
        if actual_digest != expected_digest:
            findings.append(f"SHA256_MISMATCH: {rel}: expected={expected_digest} actual={actual_digest}")
    return {
        "ok": not findings,
        "source_commit": data["source"]["commit"],
        "allowlisted_files": len(expected_paths),
        "found_files": len(found),
        "sha256_checked": checked,
        "findings": findings,
    }


def validate_report_destination(report: Path, export_root: Path, manifest_path: Path) -> None:
    """Refuse report paths that could mutate the export or overwrite its manifest."""
    if report.is_symlink():
        raise fail(f"report path must not be a symlink: {report}")
    root_resolved = export_root.resolve(strict=True)
    report_resolved = report.resolve(strict=False)
    manifest_resolved = manifest_path.resolve(strict=False)
    if report_resolved == root_resolved or root_resolved in report_resolved.parents:
        raise fail("report path must be outside the export directory")
    if report_resolved == manifest_resolved:
        raise fail("report path must not overwrite the manifest")
    if report.exists():
        raise fail(f"report path already exists; refusing to overwrite: {report}")
    if not report.parent.is_dir():
        raise fail(f"report parent directory does not exist: {report.parent}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="optional JSON report path outside the export directory")
    args = parser.parse_args(argv)
    try:
        result = validate_export(args.export_dir, args.manifest)
    except (ValueError, OSError) as exc:
        result = {"ok": False, "findings": [f"MANIFEST_OR_INPUT_ERROR: {exc}"]}
    if args.report:
        try:
            validate_report_destination(args.report, args.export_dir, args.manifest)
            rendered_report = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            with args.report.open("x", encoding="utf-8") as stream:
                stream.write(rendered_report)
        except (ValueError, OSError) as exc:
            result["ok"] = False
            result.setdefault("findings", []).append(f"REPORT_WRITE_ERROR: {exc}")
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
