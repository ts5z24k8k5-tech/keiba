# Local Private-Migration Export Validator

This is a read-only gate for a **future clean-history export**. It does not copy files,
create repositories, transfer data, modify Git history, or contact GitHub.

## Files

- `docs/PRIVATE_MIGRATION_EXPORT_MANIFEST.json`: machine-readable exact-path candidate allowlist.
- `scripts/validate_private_migration_export.py`: validator.
- `tests/test_private_migration_jra_pdf.py`: synthetic regression tests.

Only manifest entries with `export: true` are permitted. At present that means
the entries marked `ALLOW_CANDIDATE`; `OPTIONAL_INCLUDE` is off by default,
and `REWRITE_REQUIRED` / `ALLOW_AFTER_ADAPTATION` entries are not exportable.
The manifest's `expected_sha256` values are intentionally null until a trusted
operator has exported and reviewed the actual bytes. The validator fails closed
on every null digest.

## Usage

From the repository root, after preparing a separate export directory:

```sh
python scripts/validate_private_migration_export.py \
  --export-dir /path/to/clean-export \
  --manifest docs/PRIVATE_MIGRATION_EXPORT_MANIFEST.json
```

Exit code 0 means the export exactly matches the manifest, all byte counts match,
and every exported file has a pinned matching SHA-256. Exit code 1 means one or
more findings exist. Optional `--report /path/to/report.json` writes a report;
the export directory remains read-only.

## Checks

- Exact allowlist: missing and extra files are rejected.
- Exclusions: results, private inputs, datasets, databases, PDFs, model artifacts,
  credentials, environment files, and other named sensitive paths are rejected.
- Symlinks and non-regular files are rejected.
- Manifest duplicates, absolute paths, backslashes, and traversal components are rejected.
- Source byte count and exported SHA-256 are checked independently.
- An unset SHA-256 is a hard failure, never a warning-only pass.

## Limitations

The manifest records source Git blob SHA-1 and source byte counts as provenance.
Those are not exported SHA-256 values. This validator does not prove the semantic
safety of file contents, scan historical Git objects, or verify that a destination
repository is Private. Human content review and destination visibility checks
remain separate mandatory gates. Synthetic tests use fabricated bytes only.
