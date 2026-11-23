# Clean-History Migration Allowlist and File Hash Ledger

Date: 2026-11-23  
Decision: **reviewed candidate allowlist; not a migration authorization**  
Source repository: `ts5z24k8k5-tech/keiba`  
Source ref: `research/jra-pdf-acquisition-20261123`  
Pinned source commit for this inventory: `720b96c008ca22db1682927421773808986c9beb`

This document supersedes any assumption that the whole research branch can be exported. Only the paths in the allowlist below are candidates for the first clean-history snapshot. A candidate is not automatically approved for transfer: the destination SHA-256, final content review, and destination-path review must be completed on a trusted local machine immediately before export.

## 1. Export decision

### Initial bootstrap allowlist

- 18 PDF-research Python modules listed in section 3.
- 18 synthetic/unit-test files listed in section 3.
- `docs/PRIVATE_MIGRATION_STRATEGY_COMPARISON.md` as an optional governance record; refresh its point-in-time source references before copying.
- `.gitignore`, **only after rewriting it for the new private repository** as described below.
- `.github/workflows/research-pdf-tests.yml`, **only after adapting its push-branch filter to the destination branch strategy**. Keep Actions disabled until the private destination and workflow have been checked.

The initial allowlist deliberately excludes the PDF acquisition workflow. It can be considered for a later, separate activation stage after the destination is confirmed Private, the manifest secret is installed by the user, and artifact retention/access are reviewed. Do not include or enable it in the first bootstrap push.

### Conditional / deferred

| Path | Decision | Reason / required action |
|---|---|---|
| `README.md` | Rewrite; do not copy as-is | Contains legacy historical-data collection instructions and claims about model status that may not describe the private working baseline. Create a new README describing only the approved private workflow. |
| `README_JRA_PDF_RECOVERY.md` | Rewrite; do not copy as-is | Refers to this repository being a public fork, current source-repo state, old migration steps and the public-fork stop condition. Replace those with destination-specific instructions after migration design is approved. |
| `.github/workflows/research-acquire-jra-pdfs.yml` | Defer | Handles source PDFs and uploads them as Actions artifacts. Only consider after Private visibility is confirmed, secret and artifact access are reviewed, and the user explicitly authorizes activation. |
| `docs/PRIVATE_MIGRATION_PREFLIGHT_AUDIT.md` | Do not copy to operational repo | Source-specific, time-bound public exposure audit with historical repo/PR/Actions details. Retain separately as migration evidence. |
| `docs/PRIVATE_MIGRATION_RUNBOOK.md` | Do not copy | Earlier full-mirror instructions conflict with the later clean-history decision. Keep as historical source record; do not execute it. |
| `docs/PUBLIC_REPOSITORY_EXPOSURE_AUDIT.md` | Do not copy to operational repo | Source-specific public exposure audit. Retain separately with the old public repository evidence. |

### Explicit exclusions

- `results/**`: all model outputs, race reports, candidate-ticket CSVs, market-price tests, odds snapshots, audit JSON, and other generated/research results. These are not source dependencies for the PDF parsing utilities.
- `scripts/build_dataset.py`: historical dataset builder; outside this PDF research scope.
- `scripts/collect_live_all_odds.py`: odds collector; its outputs and write path are not part of the clean PDF-parser bootstrap.
- `.github/workflows/collect-jra.yml`: historical dataset workflow; not part of this bootstrap.
- `.github/workflows/fetch-current-odds.yml`: odds-capture workflow with repository write permission; not part of this bootstrap.
- `docs/JRA_PDF_PARSER_ACCEPTANCE.md`: REWRITE_REQUIRED; current text contains project-specific aggregate race/PDF counts and time-bound source audit details.
- `tests/test_jra_pdf_workflow_security.py`: REWRITE_REQUIRED; it depends on workflow and `.gitignore` files excluded from this operational allowlist.
- All real manifests, race-to-PDF mappings, downloaded PDFs, extracted race text, horse/runner data, odds, predictions, SQLite databases, training/validation/test datasets, model binaries, logs, caches, and credentials. Keep them outside Git in separately permissioned private storage.
- Any untracked or ignored local files. The allowlist is an explicit tracked-path allowlist, not a request to copy the working directory.

## 2. Export rules and hash semantics

1. Export from the pinned source commit above, not from a moving branch name. If the source branch advances, create a new inventory and review it again.
2. Use only exact paths listed in the bootstrap allowlist. Do not use broad commands such as `git archive HEAD`, `cp -R .`, or a whole-branch mirror for this operational export.
3. The `source_git_blob_sha1` values below identify the Git blob objects at the pinned source tree. They are provenance identifiers, **not** the requested exported-file SHA-256.
4. On the trusted export machine, calculate SHA-256 for every exported file and populate the `exported_sha256` field. Verify destination bytes against that digest after import.
5. Record exact source commit SHA, source path, destination path, source blob SHA-1, source byte count, exported SHA-256, review status, reviewer, and review timestamp.
6. Do not fill the SHA-256 field with a GitHub commit SHA or blob SHA. Do not mark a file complete until the actual exported bytes have been hashed and re-read.
7. Scan content, not just filenames/extensions. Review Markdown, Python fixtures, YAML, test data, and comments for private race IDs, real runner names, odds, tokens, user identifiers, and embedded research outputs.
8. A clean history does not erase earlier public disclosure. Existing public data remains disclosed even when excluded from the new private repository.

## 3. File-by-file bootstrap allowlist and hash ledger

Status values:
- `ALLOW_CANDIDATE`: source review found no obvious private input or credential pattern; still requires export SHA-256 and final destination review.
- `REWRITE_REQUIRED`: do not copy current bytes; create a reviewed replacement.
- `ALLOW_AFTER_ADAPTATION`: copy only after the stated workflow/configuration adjustment.
- `OPTIONAL_INCLUDE`: include only if the user wants this governance document in the operational repository.

| Source path | Source Git blob SHA-1 | Source bytes | Status | Exported SHA-256 (fill on trusted machine) | Destination path / review note |
|---|---|---:|---|---|---|
| `.gitignore` | `999fd0e2cc29c17ec1c8747eafa690f06e511865` | 340 | REWRITE_REQUIRED |  | Add destination-specific ignores for private inputs, outputs, datasets, snapshots, models, logs, caches, and local secrets. Ignore rules do not untrack existing files. |
| `.github/workflows/research-pdf-tests.yml` | `702a4c332731a348afc42ceb67f6e1a9679e23db` | 546 | ALLOW_AFTER_ADAPTATION |  | Retain read-only permissions and no artifact upload; adjust push branch filter; run only after Actions are enabled deliberately. |
| `docs/JRA_PDF_PARSER_ACCEPTANCE.md` | `9e6db9c3e6c875ccfcd2af5baf26e197e0a3ae7a` | 23308 | REWRITE_REQUIRED |  | Contains project-specific race/PDF counts and time-bound audit claims; keep out of clean-history operational export until rewritten generically. |
| `docs/PRIVATE_MIGRATION_STRATEGY_COMPARISON.md` | `18a8d29dfabb16b349d4c585b762fee8d9dad392` | 10800 | OPTIONAL_INCLUDE |  | Refresh source SHA/PR counts and retain only if a migration decision record is wanted in the operational repo. |
| `scripts/build_jra_pdf_audit_report.py` | `342ab8bb68028f0c9712c605b88608243cae5a88` | 7816 | ALLOW_CANDIDATE |  | Local-only JSON staging input; private staging JSON/output remain outside Git. |
| `scripts/build_jra_pdf_batch_report.py` | `6a041aaa5402338176b0d3980b14c5e0774c5eb8` | 3286 | ALLOW_CANDIDATE |  | Local-only private mapping/status JSON; do not include real input files. |
| `scripts/build_jra_pdf_integrated_progress.py` | `673be0ba268d2007b0c367e47610fa42140ffa94` | 1425 | ALLOW_CANDIDATE |  | Local-only private progress JSON; do not include real input files. |
| `scripts/build_jra_pdf_progress_report.py` | `969023c17624f38920585378ed5d038fc5fb629e` | 3353 | ALLOW_CANDIDATE |  | Local-only private progress JSON; do not include real input files. |
| `scripts/download_jra_pdfs.py` | `de842005cf1abb923cf8f1763b4b8f38867c89dc` | 12019 | ALLOW_CANDIDATE |  | Removed project-specific 149/23 defaults; expected counts are optional explicit CLI inputs. Network access remains restricted to official JRA result-PDF HTTPS URLs. |
| `scripts/inspect_jra_pdf_layout.py` | `9242c71eae7eaf8105175b72afab6571bb1bf76a` | 3164 | ALLOW_CANDIDATE |  | Aggregate geometry audit; verify it continues to omit raw text and runner names. |
| `scripts/jra_pdf_batch_progress.py` | `22f1e3b9150c6b2ad7509dac5d6b4d4d3bc32683` | 5950 | ALLOW_CANDIDATE |  | Metadata-only batch state; actual mapping remains private. |
| `scripts/jra_pdf_columns.py` | `88c938d46ac8ff088a45f32c4562dc9f0f622930` | 2892 | ALLOW_CANDIDATE |  | Explicit configured coordinate bands; no real layout values should be embedded. |
| `scripts/jra_pdf_geometry.py` | `78192659b40d4aed7f1e900009a3b2c3f12104c8` | 3374 | ALLOW_CANDIDATE |  | Generic coordinate primitives. |
| `scripts/jra_pdf_mapping_audit.py` | `6a43c2727f2d5b0fa7023af0bf45ab95c6f06ace` | 9906 | ALLOW_CANDIDATE |  | Removed project-specific 149/23 defaults; expected counts are optional. Real manifests and mapping CSVs remain excluded. |
| `scripts/jra_pdf_progress.py` | `a706620e5ecb209812fa822bb33a5653a562967e` | 4682 | ALLOW_CANDIDATE |  | Generic state-machine logic; no real progress ledger. |
| `scripts/jra_pdf_progress_integration.py` | `589e9b0881a1802e8b4022d0922095f3768a590d` | 5765 | ALLOW_CANDIDATE |  | Generic integration logic; no real mapping/status JSON. |
| `scripts/jra_pdf_race_audit.py` | `b41dbe7ea8073fbc310331a3bc84950bc005a7ab` | 7187 | ALLOW_CANDIDATE |  | Aggregate race-quality logic; no actual race staging records. |
| `scripts/jra_pdf_race_pipeline.py` | `8e3fe4c8d7de1bccd60d4729bb48605a8de19b71` | 6054 | ALLOW_CANDIDATE |  | Candidate composition only; no actual PDF extraction or DB write. |
| `scripts/jra_pdf_reconciliation.py` | `0745261f5800d65cb66ed83276798fa8f7efc118` | 3389 | ALLOW_CANDIDATE |  | Generic comparator; independent real reference data stays private. |
| `scripts/jra_pdf_runner_fields.py` | `789fc13b05200d52190804cff10a5f9b730235a7` | 6109 | ALLOW_CANDIDATE |  | Normalizes caller-supplied cells; no real extracted rows. |
| `scripts/jra_pdf_runner_validation.py` | `14a809ee11adaca83dd80bd0844904374c9a8369` | 3809 | ALLOW_CANDIDATE |  | Validates staged candidates; no real candidate records. |
| `scripts/segment_jra_pdf_text.py` | `98c55f6ed1f768dcc48eaa34bbbbff86adba29a8` | 5058 | ALLOW_CANDIDATE |  | Strict segmentation logic; no extracted race text or real mapping. |
| `tests/test_build_jra_pdf_audit_report.py` | `aa803cc410685a3391500a27323b0aec471406cc` | 4410 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs; no private mapping or staging data. |
| `tests/test_build_jra_pdf_batch_report.py` | `de81f9db11fafdf942eb914d47b6307672863c61` | 1996 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs; no private mapping or staging data. |
| `tests/test_build_jra_pdf_progress_report.py` | `36908c216828e6da63f0ae260ebf9de926db3c30` | 1997 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs; no private progress ledger. |
| `tests/test_download_jra_pdfs.py` | `f55c3aff69f1e14a79ba51d8b5b26934034487c2` | 5785 | ALLOW_CANDIDATE |  | Uses 2099 sentinel IDs/dates and URL-shaped non-existing test fixtures; fetcher is injected and no real download occurs. |
| `tests/test_inspect_jra_pdf_layout.py` | `542de6766cb7511cb8278f544e0cc98b1a37dc36` | 1827 | ALLOW_CANDIDATE |  | Deliberately uses fake marker strings such as horse-secret-name to assert redaction. |
| `tests/test_jra_pdf_batch_progress.py` | `475c797a25c729add711ccca747db385601607e8` | 3903 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs and digest placeholders. |
| `tests/test_jra_pdf_columns.py` | `c7f03490a1e258c2c1259ceed98573638fa2e539` | 2959 | ALLOW_CANDIDATE |  | Synthetic horse/jockey labels and test values. |
| `tests/test_jra_pdf_geometry.py` | `288cb72d8fa7d2cac14b9c1b651b1b7c5be58940` | 2702 | ALLOW_CANDIDATE |  | Synthetic geometry only. |
| `tests/test_jra_pdf_mapping_audit.py` | `2978e6f9de927d29801ef486e1813966b64253e1` | 4655 | ALLOW_CANDIDATE |  | Uses 2099 sentinel race IDs/dates and non-existing official-URL-shaped fixtures; no real mapping values. |
| `tests/test_jra_pdf_progress.py` | `f3c8f24aa2be388746dc67031a5731ef63c21cf5` | 2707 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel IDs and state codes only. |
| `tests/test_jra_pdf_progress_integration.py` | `981af98f09a26198c8973251fbf0a3035ffcb21b` | 4863 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel mapping/state fixtures only. |
| `tests/test_jra_pdf_race_audit.py` | `7a798279f3ad43757739e4bcb1326bce8bd0748b` | 3883 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs and runner-name placeholders only. |
| `tests/test_jra_pdf_race_pipeline.py` | `75a8bee1dd3c1443b40b9e8c5193ac3a72197082` | 3465 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race ID, runner rows, and coordinates only. |
| `tests/test_jra_pdf_reconciliation.py` | `73019af70181017c80ab1a9bd65d6ceecfa9fbc7` | 2467 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race ID and field values only. |
| `tests/test_jra_pdf_resume.py` | `579a505deec0b3be988870e51fca5d3701fe8605` | 4050 | ALLOW_CANDIDATE |  | Uses a 2099 sentinel URL and generated in-memory PDF bytes only. |
| `tests/test_jra_pdf_runner_fields.py` | `067f9964072b521f9520bfe6fd4e337d319a979f` | 3468 | ALLOW_CANDIDATE |  | Synthetic sample names/odds values only. |
| `tests/test_jra_pdf_runner_validation.py` | `314ce9f2a29ca1b9f91252c78e8ab914df663fd8` | 3287 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs, runner rows, and SHA-256 placeholders. |
| `tests/test_jra_pdf_workflow_security.py` | `ecf621899349190f59b0a1e8ee439d7c4a9f41f5` | 3225 | REWRITE_REQUIRED |  | Depends on workflow and .gitignore files intentionally excluded from operational allowlist; rewrite as a self-contained test or omit. |
| `tests/test_segment_jra_pdf_text.py` | `d80ef31e449859e821840b77ed1ccee4c56a7886` | 3152 | ALLOW_CANDIDATE |  | Uses 2099 sentinel date/race identity fixtures only. |

## 4. Explicit non-allowlist inventory

The following path groups are excluded from the first clean export:

| Source path / pattern | Decision |
|---|---|
| `results/**` | EXCLUDE all files, regardless of extension; includes generated reports, probabilities, candidate tickets, odds snapshots and market tests. |
| `scripts/build_dataset.py` | EXCLUDE; historical data builder outside this PDF parser scope. |
| `scripts/collect_live_all_odds.py` | EXCLUDE; odds collection outside this bootstrap scope. |
| `.github/workflows/collect-jra.yml` | EXCLUDE; historical-data collection workflow. |
| `.github/workflows/fetch-current-odds.yml` | EXCLUDE; odds workflow with write permission and snapshot commit/push. |
| `.github/workflows/research-acquire-jra-pdfs.yml` | DEFER; do not bootstrap or activate until separate review and explicit authorization. |
| `README.md`, `README_JRA_PDF_RECOVERY.md` | REWRITE; both contain source-repository-specific or legacy instructions. |
| `docs/PRIVATE_MIGRATION_PREFLIGHT_AUDIT.md` | EXCLUDE from operational repo; retain as source audit evidence. |
| `docs/PRIVATE_MIGRATION_RUNBOOK.md` | EXCLUDE; obsolete full-mirror procedure conflicts with this clean-history decision. |
| `docs/PUBLIC_REPOSITORY_EXPOSURE_AUDIT.md` | EXCLUDE from operational repo; retain separately as source audit evidence. |
| Any unlisted path | EXCLUDE by default; require explicit review and a new allowlist version. |

## 5. Final export checklist

Before any future export, a human operator must verify each item:

- [ ] Source commit still equals the pinned SHA; if not, regenerate this ledger.
- [ ] Export includes only the bootstrap allowlist, with the conditional workflow/doc decisions resolved.
- [ ] No `results/**`, real manifest, race mapping, PDF, extracted text, runner data, odds, prediction, database, dataset, model, log, cache, credential, or local environment file is present.
- [ ] Every exported file has an independently computed SHA-256 recorded in the ledger.
- [ ] Every destination file re-hashes to the recorded SHA-256.
- [ ] Git history is newly initialized and contains no source-history objects; provenance is recorded in the first commit message or a sanitized migration record.
- [ ] The destination is independently confirmed Private before any private input or secret is transferred.
- [ ] GitHub Actions remain disabled during bootstrap; test workflow is enabled only after review.
- [ ] No repository creation, push, secret transfer, data transfer, or workflow activation occurs without the user's separate explicit authorization.

## 6. Review limitations

The file list, byte counts, and Git blob SHAs were retrieved from the source branch tree. The listed Python modules and tests were fetched and checked for obvious credential patterns; test fixtures were reviewed for synthetic sample values. Workflow YAML, README files, and key documentation were inspected. This is a source-tree review, not a forensic scan of every historical Git object, all Actions logs/artifacts, or external backups. The SHA-256 values remain blank intentionally because no local export was performed.

This document is a planning and verification artifact only. It does not authorize migration or imply that any private destination exists.
