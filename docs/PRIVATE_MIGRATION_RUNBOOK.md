# Private Repository Migration Runbook

Date: 2026-11-23

## Decision and safety boundary

Recommended path: create a **new, standalone private repository** and mirror the Git history into it. Keep the existing public fork and PR #1 untouched as an archival record until the private copy has been verified.

Do not:
- change the existing `main` branch;
- detach or delete the existing fork;
- merge PR #1;
- run data-collection, odds-capture, or PDF-acquisition workflows in the public repository;
- copy secrets, manifests, PDFs, databases, model files, odds snapshots, or other private inputs into the public repository.

This runbook is a plan only. No repository migration or visibility change has been performed.

## Verified source state

- Source: `ts5z24k8k5-tech/keiba`
- Current visibility: public; repository is a fork of `yuhevita-wq/keiba`
- Current repository size reported by GitHub: 702 KB
- Child forks reported for this fork: 0
- Current `main`: `6ec783499b8e3b77274e59fb251936d90a231d8d`
- Research branch: `research/jra-pdf-acquisition-20261123`
- Research branch head at the preflight snapshot before the latest audit additions: `8f6ab1599a1167dc41047eb884f6b74f58d0d082` (record the live head again immediately before migration; do not use this historical snapshot blindly)
- PR #1 at the 8f6ab159 snapshot: open, draft, unmerged; base `main`, head research branch; 138 commits, 46 changed files (+4,454 / -16).
- At that snapshot, relative to current `main`, the research branch was 138 commits ahead and 2 commits behind. Merge base is `9203de7c9adc300d167be5cf32ce12c3323c41d5`.

The fork appears to meet GitHub's manual "Leave network" eligibility criteria (public, under 1 GB, no child forks). **Do not use that option for this migration**: GitHub documents that manual detachment does not retain pull requests, issues, wikis, stars, watchers, comments, or other repository metadata. It is permanent. The existing PR #1 would be lost from the detached repository.

## Public exposure findings

The detailed 2026-11-23 follow-up inventory is in `docs/PRIVATE_MIGRATION_PREFLIGHT_AUDIT.md`. It records the current 35-file `main` tree, 79-file research tree, 38-commit `main` history, 200 available Actions run records, and the branch-protection gap.

The current public `main` tree contains model-derived probability files, candidate ticket combinations, market snapshots, and evaluation/audit outputs. The historical commit `9203de7c9adc300d167be5cf32ce12c3323c41d5` explicitly publishes the 1,554-row candidate-ticket CSV. A private mirror will preserve this history; it will not reverse the fact that those historical files were already public.

The current `main` workflows are not guarded:
- `.github/workflows/collect-jra.yml` is manually dispatchable and uploads the SQLite database, train/validation/test CSVs, audit files, summary, and fetch log. Its artifact step uses `if: always()`.
- `.github/workflows/fetch-current-odds.yml` has a push trigger on selected `main` paths, writes with `contents: write`, uploads the odds directory with `if: always()`, and attempts to commit/push the snapshot.

The research branch contains proposed private-visibility gates and safer artifact conditions, but these changes are not in current `main`. Do not run either current-main workflow in the public repository.

## Actions audit scope and result

The repository Actions API returned 200 workflow-run records; page 3 was empty. The records available in that response consisted of the PDF research test workflow, three failed push-triggered PDF acquisition workflow attempts, and one early PDF test workflow attempt. No historical-data collection or odds-capture run appeared in those returned records.

Artifact lists were empty for the latest two successful test runs and the three failed PDF acquisition attempts inspected. The PDF test workflow itself does not publish artifacts. This is a bounded audit of the run records and artifact IDs currently available through the API, **not proof that no older, expired, deleted, or otherwise unavailable artifact ever existed**. Historical workflow logs/artifacts should be checked in the GitHub UI if a complete retention-era audit is required.

Latest research-branch CI: 148 tests passed. The latest test run published no artifacts.

## PR preservation strategy

Git history and PR metadata are separate:

- A Git mirror preserves commits and Git refs (branches/tags).
- A Git mirror does **not** transfer GitHub PR #1's number, review threads, comments, checks, labels, or timeline.
- Keeping the existing public fork and PR #1 in place preserves that original PR record.
- A new private repository can receive the same branch and commits; a new draft PR can then be opened there and link back to the original PR #1.

Therefore, keep PR #1 open in the old public fork. Recreate a separate draft PR in the private repository only after its branches and tests are verified. Do not detach or delete the old fork.

## Migration procedure (manual; not yet executed)

### 1. Freeze and preserve the public source

1. Do not run any Actions workflow in the public repository.
2. Leave PR #1 open and draft.
3. Record the current `main` and research branch SHAs above.
4. Do not add private data or secrets to the public repository.

### 2. Create a local full-history backup

On a trusted computer with Git installed:

```sh
git clone --mirror https://github.com/ts5z24k8k5-tech/keiba.git keiba-mirror.git
git --git-dir=keiba-mirror.git fsck --full
git --git-dir=keiba-mirror.git show-ref > keiba-mirror-refs.txt
git --git-dir=keiba-mirror.git rev-list --all --count
git --git-dir=keiba-mirror.git bundle create ../keiba-all-refs.bundle --all
shasum -a 256 ../keiba-all-refs.bundle
```

Keep the mirror directory, bundle, refs list, and bundle SHA-256 as separate backup material. Do not upload the bundle to a public repository or share it as an artifact.

### 3. Create an empty private destination

1. In the user's own GitHub account, create a new repository such as `keiba-private`.
2. Set visibility to **Private** at creation.
3. Do not initialize it with a README, license, or .gitignore; the destination should be empty.
4. **Disable GitHub Actions in the destination immediately**, before the first mirror push. The source `main` still contains a push-triggered odds workflow with write permission; do not risk firing it during initial migration.
5. Confirm the destination owner and URL before pushing.

### 4. Mirror Git refs and history

Keep Actions disabled throughout this step and the initial verification. A mirror push may update the destination `main` and encounter the source's historical push-triggered workflow definitions.

Only after confirming that the destination is the intended empty private repository:

```sh
git --git-dir=keiba-mirror.git push --mirror https://github.com/OWNER/keiba-private.git
```

Use the exact private destination URL. `--mirror` synchronizes refs and can delete refs on the destination, so never point it at the old public source or a non-empty destination.

### 5. Verify the private copy before using it

Compare source and destination:
- `main` must point to `6ec783499b8e3b77274e59fb251936d90a231d8d`.
- `research/jra-pdf-acquisition-20261123` must point to the exact SHA recorded immediately before migration. The `8f6ab159...` value above is only the preflight snapshot, not a permanent expected SHA.
- Branch/tag refs and unique reachable commit count must match the local mirror.
- Run `git fsck --full` on the mirror.
- Confirm the destination repository is Private in GitHub settings.
- Confirm no secrets or local-only input files were accidentally added to the public source during the process.

Do not start Actions yet.

### 6. Re-establish PR workflow without losing the original

1. Keep the old public PR #1 open and draft.
2. In the private repository, create a new draft PR from `research/jra-pdf-acquisition-20261123` into `main`.
3. In the new PR description, link to the old public PR #1 and state that it is the private continuation. The new PR will have a new number and will not inherit old comments/reviews/checks.
4. Do not merge either PR until the private copy, workflow guards, and CI are reviewed.

### 7. Reconfigure Actions separately

Repository secrets, variables, environments, permissions, and workflow settings are not Git refs and are not copied by `git push --mirror`.

1. Keep Actions disabled until the initial mirror has been verified.
2. Review all workflow files on the private default branch before enabling Actions. The copied `main` still contains the old odds `push` trigger and historical-data workflow; the research-branch safety changes are not automatically applied to `main`.
3. Ensure the private-repository visibility gate is present before any data, odds, PDF, or artifact step.
4. Keep least-privilege token permissions and success-only artifact publication.
5. Re-add `JRA_PDF_MANIFEST_B64` manually as a repository secret only after confirming the destination is Private. Never commit the manifest or secret value.
6. Configure private `main` branch protection/rulesets (PR required, CI required, no force-push or deletion) before routine work.
7. Keep all data collection and acquisition workflows disabled until the private branch/default-branch review is complete.
8. Verify artifact contents and retention settings before the first manual run.

## Rollback and stop conditions

- If mirror verification fails, do not create the replacement PR or run Actions. Rebuild the private destination from the local mirror after diagnosing the mismatch.
- If the wrong destination was selected, stop before pushing; do not use `--mirror` on a repository containing unrelated refs.
- If any secret or private input appears in the public source, stop further pushes and treat it as exposed. Removing a file in a later commit does not remove it from public Git history or existing clones.
- Keep the original public fork and PR #1 intact until the user explicitly decides otherwise.

## External references

- GitHub: [Detaching a fork](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/detaching-a-fork)
- GitHub: [Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
- GitHub: [Downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
- GitHub: [Planning your migration to GitHub](https://docs.github.com/en/migrations/overview/planning-your-migration-to-github)


## Live preflight correction — 2026-11-23 16:27 JST

This addendum supersedes any earlier branch-head, PR-size, and Actions-run-count snapshot above. GitHub was queried again immediately before this update.

- Current `main`: `6ec783499b8e3b77274e59fb251936d90a231d8d` (unchanged).
- Current research branch: `277e4ce4da644067e29f56788021a4d358de55db`.
- PR #1: Open, Draft, unmerged; base `main`; head research branch; 141 commits, 47 changed files, +4,603 / -16.
- PR #1 currently has zero issue comments and zero submitted reviews in the queried endpoints. This does not mean its PR metadata or check history can be recreated by a Git mirror.
- The source repository currently reports 702 KB, public, fork=true, zero child forks, and parent `yuhevita-wq/keiba`.
- Main commit listing currently returns 38 commits. The research branch contains 141 commits in the PR comparison. The PR commit endpoint returned 100 on page 1 and 41 on page 2.
- Actions API currently reports 212 workflow runs across three pages: 208 `Research PDF downloader tests`, 3 `.github/workflows/research-acquire-jra-pdfs.yml`, and 1 `.github/workflows/research-pdf-tests.yml`. Conclusions: 142 success, 70 failure. No historical-data collection or odds-capture run appeared in these returned records.
- Latest PR run inspected: `45131277893`, job `unit-tests` succeeded; its artifact list was empty.
- Current main workflow files were fetched directly and confirmed unsafe for a public repository: `collect-jra.yml` remains manually dispatchable and uploads SQLite/training CSV/audit/log outputs with `if: always()`; `fetch-current-odds.yml` still has a selected-path push trigger, `contents: write`, `if: always()` artifact upload, and commit/push attempts. Do not run these workflows in the public fork.
- The run counts above are the current API listing, not a guarantee that expired/deleted artifacts or older records never existed.

### Migration inventory and stop conditions — refined

Treat these as separate migration classes; do not indiscriminately copy all files into the private repository:

1. **Git refs/history:** mirror all branches and tags to an empty private destination only after local mirror backup and verification. The public history already contains model probabilities, market snapshots, evaluation outputs, and the 1,554-row candidate-ticket CSV. Mirroring preserves that exposure in history; it does not undo public disclosure.
2. **PR metadata:** preserve old public PR #1 by leaving the source fork untouched. Create a new private Draft PR only after mirror verification; link back to public PR #1. Do not promise comment/review/check migration.
3. **Actions configuration:** workflow YAML files are Git content and will be mirrored. GitHub Actions enablement, repository secrets, variables, environments, permissions, branch rules, and artifacts are not Git refs and must be handled separately. Keep Actions disabled in the destination before the mirror push and during initial validation because the mirrored `main` contains a push-triggered workflow with write permission.
4. **Private research inputs:** keep manifest CSVs, local source PDFs, SQLite databases, training/validation/test datasets, model binaries, odds snapshots not intended for publication, raw logs, and credentials outside Git history. Use a separately controlled private storage/backup path and transfer only after the destination's Private visibility is independently confirmed.
5. **Publicly exposed material:** do not treat migration as remediation. If any credential is found in any historical commit, revoke/rotate it first; history rewriting or deleting the current file is not sufficient to invalidate an exposed credential.

### Required pre-migration freeze snapshot

Immediately before any future migration, re-query and record:
- repository `private`, `fork`, parent, size, and child-fork count;
- all branch names and exact SHAs; all tags;
- PR #1 state, draft flag, base/head refs and SHAs, commit count, changed files, comments/reviews;
- Actions run inventory and currently retained artifacts;
- source tree and workflow file hashes.

Do not reuse the SHA values in this addendum blindly if the research branch advances again. This addendum is an audit record, not permission to create a destination or push refs.


## Live correction and staged-data gate — 2026-11-23 18:21 JST

This section supersedes older point-in-time values above when they differ:
- Current public `main`: `6ec783499b8e3b77274e59fb251936d90a231d8d`.
- Research branch at the start of this audit pass: `d2e881cd2943d617a0b3013a7593ae22e9eb3722`; the audit-document update itself will advance this branch again. Re-query immediately before any future migration.
- PR #1: Open / Draft / unmerged; 143 commits, 47 changed files, +4,656 / -16 at the start of this audit pass.
- Latest inspected runs on the prior research head both completed successfully: push and PR jobs each ran 149 tests; neither produced artifacts. The next audit-document update triggers fresh CI, which must be checked separately.
- Repository size reported at this check: 735 KB. Both current branches remain unprotected. No destination repository has been created.

### File classification and staging gate

The current PR changed-file list contains only source scripts, tests, documentation, workflow YAML, and `.gitignore`; no CSV, JSON, PDF, database, model binary, manifest, odds snapshot, or training dataset appears in that list. This is a path-level review, not a full source-code secret scan. See `docs/PRIVATE_MIGRATION_PREFLIGHT_AUDIT.md` for the class-by-class decision matrix.

The `.gitignore` is not a universal data-loss-prevention rule. It does not exclude every CSV/JSON file or every possible private-data directory. Before every commit, inspect `git status --short`, `git diff --cached --name-status`, `git diff --cached --stat`, and `git diff --cached --check`; manually inspect all staged data-like files. Never assume an ignored extension or folder list catches private data embedded in text, source, fixtures, or logs.

Do not automatically mirror public CSV/JSON outputs as operational research inputs. They are already publicly disclosed in the source history. The private mapping CSV and manifest, downloaded PDFs, SQLite, model files, raw datasets, and private odds snapshots remain outside Git. GitHub Actions settings/secrets/variables/artifacts and PR metadata must be handled separately.

### Stop condition

No migration operation is authorized by this document. Do not create a repository, push refs, change source visibility, detach the fork, merge PR #1, or modify public `main` without a separate explicit instruction.
