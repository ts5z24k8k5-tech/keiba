# Private Migration Preflight Audit

Audit date: 2026-11-23  
Source snapshot: `8f6ab1599a1167dc41047eb884f6b74f58d0d082`  
Scope: public Git history, tracked-tree inventory, branch/PR metadata, Actions run inventory, and migration prerequisites. This is a preflight report only; no destination repository was created and no migration was performed.

## 1. Source repository state

- Repository: `ts5z24k8k5-tech/keiba`
- Visibility: public
- Fork: yes; parent `yuhevita-wq/keiba`
- GitHub repository size field: 702 KB
- Child fork count: 0
- Default branch: `main`
- Branches returned by GitHub: `main`, `research/jra-pdf-acquisition-20261123`
- Both branches reported `protected: false`
- Repository rulesets endpoint returned an empty list.
- PR #1 remains Open / Draft / unmerged.
- At this snapshot, PR #1 had 138 commits, 46 changed files, +4,454 / -16.
- Current `main`: `6ec783499b8e3b77274e59fb251936d90a231d8d`
- Research branch: `8f6ab1599a1167dc41047eb884f6b74f58d0d082`
- Compare: research branch 138 commits ahead, 2 behind; merge base `9203de7c9adc300d167be5cf32ce12c3323c41d5`.

The branch-protection status is important: neither branch currently reports protection, and no repository rulesets were returned. The future private destination should not be treated as protected by default. Before normal work resumes, configure a protection rule or ruleset for private `main`: require pull requests, require the relevant CI checks, block force pushes and deletion, and keep direct pushes restricted.

## 2. Tracked-tree inventory

The current public `main` tree contains 35 blobs (2,297,439 bytes):
- 20 CSV
- 4 JSON
- 7 Markdown
- 2 Python
- 2 GitHub Actions YAML

The research branch at the audit snapshot contains 79 blobs (2,505,129 bytes):
- 20 CSV
- 4 JSON
- 11 Markdown
- 39 Python
- 4 GitHub Actions YAML
- 1 `.gitignore`

The 20 CSV and 4 JSON outputs are inherited public research outputs: model probabilities, candidate ticket combinations, market-price comparisons, tail-corrected tables, and timestamped market snapshots. The large all-pools odds snapshot is approximately 1.01 MB. These files are already public and remain part of the Git history; a private mirror would make the copied history private in the new repository, but cannot undo prior public exposure.

No current-tree path has a `.sqlite`, `.db`, `.pdf`, archive, or obvious model-binary extension. No `.gitmodules` path appeared in the tree. This is a path/type inventory, not a byte-for-byte forensic scan of every historical Git object.

The private 149-race mapping CSV and 23-PDF manifest are not tracked in the research branch. They must remain local or be added later as an Actions secret in the private destination. No downloaded JRA PDF or SQLite database is present in the tracked tree.

## 3. Git history findings

The current `main` history exposes 38 commits. The recorded commits include:
- model probability and evaluation reports;
- 1,554 candidate ticket combinations;
- market-price and tail-corrected CSVs;
- timestamped all-pool odds snapshots;
- the historical data-collection workflow and its dataset builder;
- the odds-capture script and push-triggered workflow.

Commit `9203de7c9adc300d167be5cf32ce12c3323c41d5` explicitly added the 1,554-row candidate-ticket CSV. The all-pools snapshot was committed in October 2026. These historical objects remain retrievable from the public repository even if a later commit deletes the files.

Two recent `main` commits added and then removed `scripts/jra_pdf_batch_progress.py`; the file is absent from the current `main` tree. This is a historical source-code change, not a private-data removal.

The research branch's comparison against `main` contains 46 changed paths: workflow changes, `.gitignore`, documentation, Python utilities, and synthetic tests. No new CSV/JSON research data, PDF, SQLite, model binary, or private manifest is introduced by the research-only delta.

A full historical secret scan of every blob and every commit was not completed. Earlier path and representative-content checks found no obvious credentials, but that is not a guarantee that no secret ever entered Git history. Treat any later-discovered credential as exposed and rotate it; deleting it in a later commit is insufficient.

## 4. Actions audit

The Actions runs endpoint returned 200 records across two pages; page 3 was empty:
- 130 successful PDF research test runs;
- 66 failed PDF research test runs;
- 3 failed PDF acquisition workflow attempts;
- 1 early PDF test workflow attempt that failed.

No run of the historical dataset-collection workflow or the odds-capture workflow appeared in the returned 200 records. This does not prove that no expired, deleted, or otherwise unavailable run existed.

Artifact lists were checked for the latest two successful test runs and the three failed PDF acquisition attempts; each returned no artifacts. The PDF test workflow does not upload artifacts. The audit did not individually enumerate artifact IDs for all 200 runs, and it cannot inspect expired/deleted artifacts.

The latest research-branch push and PR checks at the audit snapshot each ran 148 tests successfully and had no artifacts.

## 5. Critical migration trigger hazard

The current public `main` contains `.github/workflows/fetch-current-odds.yml` with:
- a `push` trigger on changes to the workflow or `scripts/collect_live_all_odds.py`;
- `contents: write`;
- code that collects odds, uploads snapshots, and commits/pushes results.

The current public `main` also contains a manually dispatchable `collect-jra.yml` workflow that can upload a SQLite database and training CSVs, including when earlier steps fail.

The research branch has safer replacements, but these are **not** in current `main`. A full mirror push into a new private repository may cause push-triggered Actions to be considered on the new destination if Actions are enabled. Therefore:

**Disable GitHub Actions in the empty private destination before the first mirror push.** Keep Actions disabled while the refs are copied and verified. Do not rely only on the fact that the destination is private.

After migration, review the default-branch workflows and install the reviewed safety changes through a separate, explicit PR on the private repository. Only re-enable selected workflows after the default branch is hardened and the user approves.

## 6. Migration object inventory

### Copied by a Git mirror
- Advertised Git refs: branches and tags (verify exact refs locally with `git show-ref`).
- All reachable Git commits and tracked blobs for those refs, including the historical public CSV/JSON outputs.
- The existing research branch and its synthetic test suite.

### Not copied by a Git mirror
- PR #1 number, review comments, inline threads, labels, approvals, checks, and timeline.
- Issues, discussions, wiki, projects, releases, stars, watchers, webhooks, deploy keys, GitHub App installations, and repository settings.
- Actions secrets, variables, environments, permissions, run logs, and artifacts.
- Branch protection and repository rulesets.
- Local untracked files, the private mapping/manifest, downloaded PDFs, SQLite database, and model binaries.

Keep the old public fork and PR #1 open as the authoritative historical record. Open a new Draft PR in the private repository after verification and link back to PR #1.

## 7. Required migration order

1. Freeze the public repository: do not run Actions and do not add private data.
2. On a trusted computer, create a mirror clone, run `git fsck --full`, save `git show-ref`, record `git rev-list --all --count`, create a bundle, and hash the bundle.
3. Create a new **empty Private** standalone repository.
4. Immediately disable Actions in that destination before any Git push.
5. Push the mirror only to the confirmed empty destination.
6. Compare all branch/tag refs, commit counts, and the two known branch SHAs. Run `git fsck --full` again.
7. Keep Actions disabled. Inspect all default-branch workflows. The initial `main` still has the old unguarded workflow definitions.
8. Create a separate safety PR on the private repository to bring in the reviewed private gates and remove unsafe push triggers from the default branch. Do not merge it without approval.
9. Configure private-main branch protection/rulesets, least-privilege Actions permissions, and secrets manually.
10. Open a new Draft PR for the research branch, linking the preserved public PR #1.
11. Re-enable only the selected Actions workflows after explicit approval and a final dry-run review.

## 8. Working-tree safeguard added on the research branch

The research branch's `.gitignore` now excludes:
- `private_input/` and all of `output/`;
- local `.env` files, PEM/key material;
- SQLite/database files and common model/data binary formats.

A regression test checks these ignore rules. This prevents accidental staging of common local outputs but is not a substitute for checking `git status` and reviewing staged files before every commit. `.gitignore` does not remove files already tracked in Git.

## 9. Explicit stop conditions

- Do not create the destination repository, push a mirror, change visibility, detach the fork, merge PR #1, or modify public `main` as part of this preflight.
- Do not enable Actions on the private destination until its first mirror push and workflow review are complete.
- If a secret/private file is found in public history, treat it as exposed; rotate/revoke it and separately evaluate history cleanup.
- If refs, commit counts, or object integrity do not match, stop before opening a private PR or enabling workflows.

This document is a migration preflight audit, not authorization to execute the migration.
