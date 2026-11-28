# Clean-History Migration Allowlist and File Hash Ledger

Date: 2026-11-23  
Decision: **reviewed candidate allowlist; not a migration authorization**  
Source repository: `ts5z24k8k5-tech/keiba`  
Source ref: `research/jra-pdf-acquisition-20261123`  
Pinned source commit for this inventory: `33ff31300b95f38c3da671f53a26816e8996568c`

This document supersedes any assumption that the whole research branch can be exported. Only the paths in the allowlist below are candidates for the first clean-history snapshot. A candidate is not automatically approved for transfer: the destination SHA-256, final content review, and destination-path review must be completed on a trusted local machine immediately before export.

## 1. Export decision

### Initial bootstrap allowlist

- 18 PDF-research Python modules listed in section 3.
- 18 synthetic/unit-test files listed in section 3.
- `docs/PRIVATE_MIGRATION_STRATEGY_COMPARISON.md` as an optional governance record; refresh its point-in-time source references before copying.
- The source `.gitignore` and workflow are not copied verbatim. Reviewed destination replacements are listed in section 4; both still require exported SHA-256 and destination review.
- The replacement workflow targets destination `main`, uses read-only permissions, installs the pinned dependency, and runs synthetic tests only. Keep Actions disabled until the private destination is confirmed and reviewed.

The initial allowlist deliberately excludes the PDF acquisition workflow. It can be considered for a later, separate activation stage after the destination is confirmed Private, the manifest secret is installed by the user, and artifact retention/access are reviewed. Do not include or enable it in the first bootstrap push.

### Conditional / deferred

| Path | Decision | Reason / required action |
|---|---|---|
| `README.md` | Rewrite; do not copy as-is | Legacy README is replaced by a local-only PDF-tool README drafted on the research branch; verify its exported SHA-256 before transfer. |
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
| `.gitignore` | `cfd84e6eefe4f1b5493a37c89b90e15804f00b39` | 568 | REWRITE_REQUIRED |  | Source bytes excluded; destination replacement is listed in section 4. Ignore rules do not untrack already tracked files. |
| `.github/workflows/research-pdf-tests.yml` | `bb8b7911b19fdd79007d9bc28a48882e8ed2ae2c` | 775 | ALLOW_AFTER_ADAPTATION |  | Source bytes excluded; adapted destination workflow is listed in section 4. |
| `docs/JRA_PDF_PARSER_ACCEPTANCE.md` | `9e6db9c3e6c875ccfcd2af5baf26e197e0a3ae7a` | 23308 | REWRITE_REQUIRED |  | Contains project-specific race/PDF counts and time-bound audit claims; keep out of clean-history operational export until rewritten generically. |
| `docs/PRIVATE_MIGRATION_STRATEGY_COMPARISON.md` | `18a8d29dfabb16b349d4c585b762fee8d9dad392` | 10800 | OPTIONAL_INCLUDE |  | Refresh source SHA/PR counts and retain only if a migration decision record is wanted in the operational repo. |
| `scripts/build_jra_pdf_audit_report.py` | `80bdf4a70af0b21c839afe3626a8774378186b70` | 7904 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/build_jra_pdf_batch_report.py` | `c2b420a1c1fc6c8f5cdbbd6ad629cbac524e8bf8` | 3374 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/build_jra_pdf_integrated_progress.py` | `beb14524363935f016df37eaef645392e20365a7` | 1513 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/build_jra_pdf_progress_report.py` | `c641f29267ee6a684a3cb0b2993970d80458c292` | 3441 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/download_jra_pdfs.py` | `1283f8077d87a3307a9709ebe0b651165c649ef4` | 13087 | ALLOW_CANDIDATE |  | Removed project-specific count defaults; adds a 50 MiB response cap, symlink-target refusal, and exclusive temporary-file creation. |
| `scripts/inspect_jra_pdf_layout.py` | `72d32d17a2e257691fd0b23c156f0aa6a90b3c2b` | 3415 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/jra_pdf_batch_progress.py` | `22f1e3b9150c6b2ad7509dac5d6b4d4d3bc32683` | 5950 | ALLOW_CANDIDATE |  | Metadata-only batch state; actual mapping remains private. |
| `scripts/jra_pdf_columns.py` | `88c938d46ac8ff088a45f32c4562dc9f0f622930` | 2892 | ALLOW_CANDIDATE |  | Explicit configured coordinate bands; no real layout values should be embedded. |
| `scripts/jra_pdf_geometry.py` | `78192659b40d4aed7f1e900009a3b2c3f12104c8` | 3374 | ALLOW_CANDIDATE |  | Generic coordinate primitives. |
| `scripts/jra_pdf_mapping_audit.py` | `638834bf7243489302a1f251e3708f341c1bb67c` | 10196 | ALLOW_CANDIDATE |  | Adds CLI output path/symlink protection; inputs/outputs remain explicit local paths. |
| `scripts/jra_pdf_progress.py` | `a706620e5ecb209812fa822bb33a5653a562967e` | 4682 | ALLOW_CANDIDATE |  | Generic state-machine logic; no real progress ledger. |
| `scripts/jra_pdf_progress_integration.py` | `589e9b0881a1802e8b4022d0922095f3768a590d` | 5765 | ALLOW_CANDIDATE |  | Generic integration logic; no real mapping/status JSON. |
| `scripts/jra_pdf_race_audit.py` | `b41dbe7ea8073fbc310331a3bc84950bc005a7ab` | 7187 | ALLOW_CANDIDATE |  | Aggregate race-quality logic; no actual race staging records. |
| `scripts/jra_pdf_race_pipeline.py` | `8e3fe4c8d7de1bccd60d4729bb48605a8de19b71` | 6054 | ALLOW_CANDIDATE |  | Candidate composition only; no actual PDF extraction or DB write. |
| `scripts/jra_pdf_reconciliation.py` | `0745261f5800d65cb66ed83276798fa8f7efc118` | 3389 | ALLOW_CANDIDATE |  | Generic comparator; independent real reference data stays private. |
| `scripts/jra_pdf_runner_fields.py` | `789fc13b05200d52190804cff10a5f9b730235a7` | 6109 | ALLOW_CANDIDATE |  | Normalizes caller-supplied cells; no real extracted rows. |
| `scripts/jra_pdf_runner_validation.py` | `14a809ee11adaca83dd80bd0844904374c9a8369` | 3809 | ALLOW_CANDIDATE |  | Validates staged candidates; no real candidate records. |
| `scripts/segment_jra_pdf_text.py` | `98c55f6ed1f768dcc48eaa34bbbbff86adba29a8` | 5058 | ALLOW_CANDIDATE |  | Strict segmentation logic; no extracted race text or real mapping. |
| `tests/test_build_jra_pdf_audit_report.py` | `a7f0be1982bc239474dc479845faffe552d4af37` | 5060 | ALLOW_CANDIDATE |  | Adds CLI path-boundary regression coverage; uses synthetic fixtures only. |
| `tests/test_build_jra_pdf_batch_report.py` | `de81f9db11fafdf942eb914d47b6307672863c61` | 1996 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs; no private mapping or staging data. |
| `tests/test_build_jra_pdf_progress_report.py` | `36908c216828e6da63f0ae260ebf9de926db3c30` | 1997 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs; no private progress ledger. |
| `tests/test_download_jra_pdfs.py` | `b37e4bb8df01a56841f93d5cf31832629daab07c` | 7150 | ALLOW_CANDIDATE |  | Runtime/fixture note refreshed after content review. |
| `tests/test_inspect_jra_pdf_layout.py` | `cb7dcac04271566c09cefb38501f099b5887ccfa` | 2728 | ALLOW_CANDIDATE |  | Adds CLI path-boundary regression coverage; uses synthetic fixtures only. |
| `tests/test_jra_pdf_batch_progress.py` | `475c797a25c729add711ccca747db385601607e8` | 3903 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs and digest placeholders. |
| `tests/test_jra_pdf_columns.py` | `c7f03490a1e258c2c1259ceed98573638fa2e539` | 2959 | ALLOW_CANDIDATE |  | Synthetic horse/jockey labels and test values. |
| `tests/test_jra_pdf_geometry.py` | `288cb72d8fa7d2cac14b9c1b651b1b7c5be58940` | 2702 | ALLOW_CANDIDATE |  | Synthetic geometry only. |
| `tests/test_jra_pdf_mapping_audit.py` | `96dd5e4dfbf3af272c1a41402c400c389b3af6b1` | 6020 | ALLOW_CANDIDATE |  | Adds CLI path-boundary regression coverage; uses synthetic fixtures only. |
| `tests/test_jra_pdf_progress.py` | `f3c8f24aa2be388746dc67031a5731ef63c21cf5` | 2707 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel IDs and state codes only. |
| `tests/test_jra_pdf_progress_integration.py` | `981af98f09a26198c8973251fbf0a3035ffcb21b` | 4863 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel mapping/state fixtures only. |
| `tests/test_jra_pdf_race_audit.py` | `7a798279f3ad43757739e4bcb1326bce8bd0748b` | 3883 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs and runner-name placeholders only. |
| `tests/test_jra_pdf_race_pipeline.py` | `75a8bee1dd3c1443b40b9e8c5193ac3a72197082` | 3465 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race ID, runner rows, and coordinates only. |
| `tests/test_jra_pdf_reconciliation.py` | `73019af70181017c80ab1a9bd65d6ceecfa9fbc7` | 2467 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race ID and field values only. |
| `tests/test_jra_pdf_resume.py` | `579a505deec0b3be988870e51fca5d3701fe8605` | 4050 | ALLOW_CANDIDATE |  | Uses a 2099 sentinel URL and generated in-memory PDF bytes only. |
| `tests/test_jra_pdf_runner_fields.py` | `067f9964072b521f9520bfe6fd4e337d319a979f` | 3468 | ALLOW_CANDIDATE |  | Synthetic sample names/odds values only. |
| `tests/test_jra_pdf_runner_validation.py` | `314ce9f2a29ca1b9f91252c78e8ab914df663fd8` | 3287 | ALLOW_CANDIDATE |  | Uses synthetic 2099 sentinel race IDs, runner rows, and SHA-256 placeholders. |
| `tests/test_jra_pdf_workflow_security.py` | `ecf621899349190f59b0a1e8ee439d7c4a9f41f5` | 3225 | REWRITE_REQUIRED |  | Depends on workflow and .gitignore files intentionally excluded from operational allowlist; rewrite as a self-contained test or omit. |
| `tests/test_segment_jra_pdf_text.py` | `40a819b4836b89b901449c1b6863fe1195dffbca` | 3152 | ALLOW_CANDIDATE |  | Uses 2099 sentinel date/race identity fixtures only, including full-width year digits. |

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


## 4. Destination-generated bootstrap files (outside the 36 source candidates)

These files are clean-history replacement/addition artifacts authored on the research branch, not files copied from the pinned source tree. They do not change the 36-file source allowlist. Before any transfer, compute and verify their exported SHA-256 on the trusted export machine and review the destination paths.

| Path | Current branch blob SHA-1 | Bytes | Purpose / gate |
|---|---|---:|---|
| `README.md` | `29a7597b219b46b2237e4f6dcb319de0e38e934f` | 4495 | Replaces legacy project instructions with local-only PDF utility setup; pins direct and transitive runtime dependencies. |
| `requirements.txt` | `80d0b8f052225328a3a60c567cb153ab63d182df` | 293 | Pins PyMuPDF 2.2 and the transitive dependency versions resolved by CI; verify package/license review. |
| `.gitignore` | `cfd84e6eefe4f1b5493a37c89b90e15804f00b39` | 568 | Destination-specific private input/output, data, model, credential, and runtime ignores. |
| `.github/workflows/research-pdf-tests.yml` | `6eaa9789085e6e967be08f636c1dd20e9a214c4b` | 861 | Adapted read-only CI; actions pinned to verified commit SHAs, installs dependency, imports backend, runs synthetic tests; no JRA download or artifact upload. |

