# Private Repository Migration Runbook

Date: 2026-11-28

## 1. Purpose and governing decision

This document governs a possible future clean-history migration of the JRA PDF research utility. The only approved design described here is **Clean-History**: create a new, standalone private repository and initialize its Git history from a separately reviewed staging directory containing only exact-path approved files.

Do not mirror, clone, bundle, fetch, push, or otherwise transfer the source repository's Git history, commits, branches, tags, refs, or Git objects. A destination must begin with a new initial commit. This runbook is a control document, not authorization to perform any migration step.

The existing public fork and public PR #1 must remain untouched unless the user separately directs otherwise. A clean-history migration does not erase prior public disclosure.

## 2. Safety boundary and separate authorization

The following are distinct actions and each requires the user's separate, explicit authorization immediately before execution:

- creating a destination repository;
- exporting or staging files;
- pushing the reviewed initial commit;
- transferring private inputs or data;
- creating or transferring repository secrets or variables;
- enabling GitHub Actions or activating any workflow;
- creating a replacement pull request or changing the old public PR.

Approval of this runbook, a preflight, a file review, or one of the actions above does not authorize any other action. Do not infer permission from prior discussion or from the existence of credentials.

Until the relevant action is separately authorized, do not create a repository, export files, push commits, transfer secrets/data, or enable workflows.

## 3. Pinned source and inventory

- Source repository: `ts5z24k8k5-tech/keiba`
- Source ref recorded by the inventory: `research/jra-pdf-acquisition-20261123`
- Pinned source commit: `33ff31300b95f38c3da671f53a26816e8996568c`
- Inventory: `docs/PRIVATE_MIGRATION_EXPORT_MANIFEST.json`
- Source candidates: exactly 36 entries with `export=true`.
- Destination-generated bootstrap artifacts: exactly 4, separately inventoried in the Ledger and not part of the 36 source candidates.

Before any export, independently confirm that the pinned commit exists and that each source candidate's path, Git blob SHA-1, byte count, and review status still match the inventory. Do not silently substitute the moving branch head for the pinned source commit. If the pin or inventory differs, stop and create a new reviewed inventory version.

## 4. Migration classes and exact-path rule

There are three distinct classes:

1. **Source candidates:** only the 36 exact paths marked `export=true` in the Manifest may be considered for export. Every file remains subject to content review and trusted-machine SHA-256 calculation.
2. **Bootstrap artifacts:** exactly four destination-generated files listed in the Ledger. They are separately authored/reviewed artifacts, not copied source candidates. Their hashes and contents must be independently verified.
3. **Excluded, deferred, or rewrite-required material:** do not export unless a new inventory version explicitly reviews and approves it. This includes generated results, private inputs, real PDFs, race mappings, odds, predictions, databases, model files, logs, caches, credentials, excluded workflows, and unlisted paths.

The Manifest's `export` field is authoritative for source candidates. A bootstrap artifact does not become a source candidate by appearing in the Ledger's separate bootstrap table.

## 5. Pre-export verification

On a trusted machine, before creating any staging content:

- verify the source commit pin and source tree;
- reconcile all 41 Manifest entries against the Ledger;
- confirm exactly 36 source candidates and 4 separate bootstrap artifacts;
- verify that no excluded or unlisted path has entered the allowlist;
- review the actual contents of every candidate and bootstrap artifact;
- identify private data, secrets, real runner/race information, and generated outputs by content, not only by filename;
- calculate SHA-256 from the actual exported bytes and record it in the appropriate controlled record;
- have a reviewer independently verify the selected paths, hashes, and destination paths.

Do not treat a Git blob SHA-1 as an exported-file SHA-256. Do not populate an expected SHA-256 from a commit ID or a guessed value.

## 6. Build a clean staging directory

Use a newly created, empty staging directory on the trusted machine. Populate it only by explicitly selecting reviewed paths from the 36 source candidates and the separately approved bootstrap artifacts.

Do not copy the source working directory or repository wholesale. Do not use `git archive`, recursive directory copies, branch exports, or any operation that could include unlisted files. Do not copy the source `.git` directory or any source Git object database.

Before proceeding, enumerate every staged file and compare the complete path set against the approved source allowlist plus the separately approved bootstrap list. Inspect the bytes and independently recompute SHA-256 for every staged file. Any unexpected path or hash mismatch is a stop condition.

## 7. Initialize a new Git history

Initialize Git in the reviewed staging directory as a new repository. The new repository must have no source remote and no imported source history.

The first commit must be created solely from the reviewed staging contents. It must not contain source commits, source refs, source branches, source tags, source bundles, or source Git objects. Record provenance in a sanitized migration record or initial commit message without embedding secrets or private inputs.

Do not compare source and destination branch/tag refs or reachable commit counts as an acceptance requirement. Such parity would contradict the Clean-History design.

## 8. Destination creation and first push

Only after separate authorization to create the repository:

- create a new, standalone repository under the user's intended account;
- set visibility to **Private** at creation;
- leave it empty (do not initialize with a README, license, or .gitignore);
- confirm the exact owner and repository URL;
- keep GitHub Actions disabled.

Only after a separate explicit authorization to push, re-confirm the destination identity, Private visibility, and empty state. Push only the new initial commit and the explicitly approved destination branch. Never use `git push --mirror`, force-push, or any operation that transfers source refs or deletes unrelated destination refs.

If the destination is not empty, its identity or visibility is uncertain, or Actions are not disabled, stop before pushing.

## 9. Post-push independent verification

After an authorized first push, independently verify:

- the destination owner and repository identity;
- repository visibility is Private;
- only the approved initial commit and approved files are present;
- every destination file's SHA-256 matches the reviewed staging record;
- no source-history objects, imported source commits, source branches, source tags, or source refs were transferred;
- no unexpected files, private inputs, or secrets are present;
- GitHub Actions remain disabled.

Do not require source/destination branch parity, tag parity, or reachable-commit-count parity. The intended result is a new history, not a mirror.

## 10. Actions, secrets, and private inputs

Actions must remain disabled during bootstrap and verification. Review workflow files and permissions before any separate authorization to enable Actions. The adapted read-only test workflow is not permission to activate it.

Repository secrets, variables, environments, private manifests, PDFs, databases, and other inputs are not part of the Git export. Each transfer or configuration action requires separate authorization after destination identity and Private visibility are independently confirmed. Never commit secret values or private inputs.

## 11. Public source and PR preservation

Keep the existing public fork, its `main` branch, and public PR #1 untouched. A Git history migration does not transfer GitHub PR metadata, reviews, comments, checks, labels, or timeline. Clean-History does not remove information already disclosed in the public repository, its history, forks, caches, or existing clones.

Any replacement PR in a private destination is a separate action requiring explicit authorization and will have its own number and review history.

## 12. Stop conditions and rollback

Stop immediately if:

- the source pin, Manifest, Ledger, or candidate contents differ from the reviewed inventory;
- a path is missing, unexpected, duplicated, or outside the exact approved path set;
- any SHA-256 or byte-count verification fails;
- any private input, secret, or prohibited generated result appears in staging or the destination;
- the destination identity, empty state, or Private visibility cannot be confirmed;
- Actions are enabled unexpectedly;
- any source history, ref, branch, tag, bundle, or Git object is found in the new repository;
- an authorization boundary is unclear or a requested operation exceeds its separate approval.

Before a push, discard or quarantine the staging attempt and rebuild from the approved inventory after review. After a push, stop further operations and preserve evidence; do not force-push, rewrite history, delete the repository, or alter the public source as an improvised rollback. Obtain explicit direction for any corrective action.

## 13. Current status

- Source candidates: 36; no export has been performed by this runbook.
- Bootstrap artifacts: 4, separately inventoried.
- Manifest expected SHA-256 values: all 41 remain null until actual trusted export bytes are produced and verified.
- Destination repository: not confirmed or created by this runbook.
- Export, push, secret transfer, private-input transfer, Actions activation, and replacement PR: not authorized or performed by this document.
- Gate A: NOT STARTED.
- CONFLICT-001: remains FAIL until this replacement and the corresponding Ledger changes pass independent acceptance audit.

This document is a plan and control specification only. It does not authorize migration or imply that any destination exists.
