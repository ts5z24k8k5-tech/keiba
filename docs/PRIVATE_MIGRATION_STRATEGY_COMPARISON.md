# Private Migration Strategy Decision

Date: 2026-11-23  
Decision status: recommended design; **no migration authorized or performed**  
Source repository: `ts5z24k8k5-tech/keiba`

> This decision document supersedes the earlier full-mirror-first recommendation in `docs/PRIVATE_MIGRATION_RUNBOOK.md`. Do not execute that runbook's full-mirror destination procedure unless the user explicitly changes this decision.

## Executive decision

**Recommended operational migration: clean-history export into a new, standalone Private repository.**

Keep the existing public fork and public PR #1 untouched as the provenance/archive record. Build the new private operational repository from an explicitly approved allowlist of source, tests, documentation, and safe workflow files. Do not import the public repository's full Git history into the operational repository. Keep research inputs and generated datasets outside Git.

For stronger disaster recovery, optionally retain a **separate encrypted local full-mirror bundle** under the user's control. It is an archival backup, not the operational repository, and must be treated as a copy of already-public history. This optional backup is not required to begin clean-history operation and is not to be uploaded to a public repo or Actions artifact.

No new repository, mirror, push, visibility change, fork detachment, PR merge, or `main` modification is authorized by this document.

## Comparison

| Criterion | Full mirror into Private | Clean-history export into Private | Assessment |
|---|---|---|---|
| Reproducibility | Preserves original commit SHAs, branches, tags, and ancestry; easiest to reproduce an exact historical checkout. | Original commit ancestry is lost in the destination. Reproducibility can still be made strong by pinning the source commit, recording every exported file's source path/blob SHA/SHA-256, retaining dependency locks, and rerunning tests. | Full mirror wins on historical checkout; clean history is sufficient for a controlled operational baseline if provenance is recorded. |
| PR preservation | Git refs transfer, but GitHub PR numbers, comments, reviews, checks, labels, and timelines do not. | Same limitation. A new private PR is a new record. | Tie. Preserve public PR #1 by leaving the source repository untouched; create a new private draft PR later. |
| Public data / exposure | Copies all reachable historical commits, including already-public CSV/JSON outputs, odds snapshots, reports, and any overlooked historical material. Private visibility does not undo prior public disclosure. | Allows an allowlist-only snapshot and omits unnecessary historical research outputs and unrelated commits. It cannot reverse prior public disclosure, and every selected text/source file still needs secret review. | Clean history is materially safer for the operational copy. |
| Recovery / rollback | Best Git-level recovery: exact refs and commit graph can be restored from a verified mirror/bundle. A mirror push can overwrite/delete destination refs, so it requires an empty destination and careful verification. | Operational rollback is to a tagged/hashed approved baseline plus a separate verified source backup. Reconstructing original history requires the source public repo or optional local mirror archive. | Full mirror wins for exact Git-history recovery; clean history is adequate if backups and provenance are mandatory. |
| Operational simplicity | Simple transfer command, but unsafe workflow definitions and public data history travel with it; Actions must remain disabled until reviewed. | More preparation: allowlist, export manifest, clean initial commit, fresh CI and new PR. The smaller clean baseline is easier to audit. | Clean history takes more setup but reduces ongoing risk. |

### Decision rationale

The key requirement is not merely to preserve Git objects; it is to establish a private, personal-use working environment without carrying unnecessary historical public data into the new operational repository. The existing public fork and PR #1 already preserve the old public record. Therefore, duplicating every historical object into the new operational repo adds exposure and operational complexity without preserving PR metadata.

A full mirror is still useful as a separately held recovery artifact, but it should not be the default working repository.

## Concrete migration design (not executed)

### Phase 0 — Freeze and source snapshot

Immediately before a future migration, record and verify:

- repository visibility, fork/parent state, repository size, and default branch;
- exact SHA for `main` and every research branch; all tags and refs;
- PR #1 state, base/head SHAs, changed-file list, checks, comments, and reviews;
- workflow files and hashes; Actions runs and currently retained artifacts;
- current source tree inventory and the allowlist proposed for export.

Do not run data collection, odds capture, or PDF acquisition in the public repository. Do not alter public `main`, detach the fork, or merge PR #1.

### Phase 1 — Build an allowlist-only clean source snapshot

Start from the exact, freshly recorded research-branch commit, not a moving branch name. Select only reviewed source code, tests, documentation needed for the private workflow, and workflow definitions that have passed the private-repository safety review.

Explicitly exclude from the operational Git repository:

- all existing CSV/JSON research outputs unless a specific file is reviewed and justified as source-controlled synthetic fixture data;
- race mappings and PDF manifests;
- downloaded JRA PDFs and raw source files;
- SQLite databases, training/validation/test datasets, odds snapshots, raw logs, generated reports;
- model binaries, checkpoints, caches, local environment files, credentials, and tokens.

Do not rely on `.gitignore` as a security boundary. Inspect every exported file, including Python fixtures, Markdown, YAML, logs, and embedded text, for accidental data or secrets. Keep real research inputs in separately permissioned private storage with an encrypted backup.

### Phase 2 — Preserve provenance despite the clean history

Create a migration provenance manifest outside the public repository, and optionally include a sanitized copy in the private repo. For every exported file record:

- destination path;
- source repository and exact source commit SHA;
- source path and Git blob SHA;
- SHA-256 of the exported bytes;
- review decision and reviewer/date.

Also record the export tool/version, Python/runtime version, dependency lock hashes, test command, and test result. The private repository's initial commit should identify the source commit and migration manifest hash. Do not claim original commit ancestry was preserved: it was not.

### Phase 3 — Private destination and safe bootstrap

Only after the user explicitly authorizes repository creation:

1. Create a new **standalone Private** repository, empty and under the user's account.
2. Confirm Private visibility independently before transferring any private input.
3. Keep GitHub Actions disabled during bootstrap.
4. Push only the approved clean-history snapshot.
5. Verify default branch, commit SHA, exported file hashes, allowlist, and absence of excluded data.
6. Configure private `main` protection/rules: PR required, required CI, no force-push, no deletion, and restricted direct writes.
7. Re-enable Actions only after reviewing every workflow on the private default branch. Use least-privilege permissions and keep acquisition/collection workflows disabled until explicitly reviewed.

The existing public `main` contains older workflows that are not safe to run in a public repository. Do not copy or activate them without the private-visibility guard and artifact-safety checks already tested on the research branch.

### Phase 4 — PR continuity

- Leave public fork `ts5z24k8k5-tech/keiba` and public PR #1 open/draft and unchanged.
- Create a new private draft PR from the imported research work into the new private `main` only after the private baseline and CI are verified.
- Link the new PR to public PR #1 and state that it is a private continuation.
- Do not imply that reviews, comments, checks, labels, or timeline were transferred. They remain with the original PR.

### Phase 5 — Recovery and rollback

Before the first private push, retain a verified source snapshot and an independent backup. Recommended minimum:

- a local full mirror and `git bundle --all` stored encrypted, if the user elects to preserve exact historical Git recovery;
- a SHA-256 checksum for each backup;
- `git fsck --full` and ref-list verification;
- a separate copy of the approved clean export and its provenance manifest;
- independent encrypted backups of private datasets and model artifacts, never in Git.

If the user declines the optional full-mirror archive, the public source repository remains the historical Git recovery source, subject to its continued availability. The clean private repository can be restored from its own Git backup, but original public commit ancestry is not contained in it.

A failed clean export is discarded and rebuilt from the pinned source commit and allowlist. A failed destination push is retried only after confirming the destination refs and contents; do not use `git push --mirror` for the clean-history workflow.

## Current source snapshot (point-in-time; refresh before migration)

- Public source: `ts5z24k8k5-tech/keiba`
- Visibility: public; fork of `yuhevita-wq/keiba`
- `main`: `6ec783499b8e3b77274e59fb251936d90a231d8d`
- Research branch at this audit: `e4563ef3abdb19431858332d55e51a8a12f40077`
- PR #1: open, draft, unmerged; 145 commits, 47 changed files (+4,719 / -16) at the queried snapshot.
- Both branches were reported unprotected in the prior audit.
- The public tree/history contains previously disclosed research outputs. The full-mirror approach would carry them into the private destination as historical Git objects.
- The repository's current `main` has unsafe legacy data/odds workflows; do not run them publicly.

All values are point-in-time and must be refreshed before any migration.

## Explicit stop conditions

Stop without pushing if:

- the destination is not independently confirmed Private and empty;
- the allowlist or file hashes do not match the reviewed export;
- any credential, personal data, private input, odds snapshot, or generated dataset appears in the export;
- the source branch advances after the snapshot and has not been re-audited;
- workflow safety, token permissions, or artifact contents are uncertain.

The user must separately authorize repository creation and any migration push. This document is a recommendation and design only; it does not authorize those actions.
