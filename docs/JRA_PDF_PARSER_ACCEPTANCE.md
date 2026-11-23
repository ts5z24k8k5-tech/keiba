# JRA PDF parser acceptance contract (research-only)

## Scope and boundary

The first parser layer is **race-block segmentation only**. It is not a runner-row parser and does not write to SQLite.

Input:
- One already-downloaded official JRA PDF, identified by its SHA-256.
- Extracted page text in original page order.
- A private expected-race mapping containing `race_id`, `date`, `venue`, and `race_no`.

Output:
- One text block per requested race, plus parsed heading identity (date, venue, meeting number/day, race number).
- A failed/missing/duplicate identity is a hard error, never a best-effort assignment.

The mapping and source PDFs remain private research inputs. Do not commit them, extracted race text, horse names, horse IDs, odds, predictions, or database snapshots to this public repository.

## Why race-number-only segmentation is not acceptable

A meeting PDF can contain many races, and a race number by itself is not a unique identity. A segment is accepted only when all three independently supplied values match:
1. Calendar date from the PDF heading.
2. Japanese venue name mapped to the expected venue.
3. Race number, also consistent with the final two digits of the 12-digit target `race_id`.

Meeting number and meeting day are retained as additional audit metadata. Duplicate headings, missing headings, malformed IDs, duplicate target IDs, or any date/venue/race-number mismatch stop the run.

The sample official JRA result PDF shows the date, meeting/venue, meeting day and race number in the race heading, followed by runner rows and race-level payout/pace information:
https://www.jra.go.jp/datafile/seiseki/report/2024/2024-7kyoto1.pdf

## Runner-row parsing: separate next layer

The official PDF includes fields such as frame number, horse number, horse name, sex/age, assigned weight, jockey, trainer, body weight, finish time, margin, win odds and popularity. The exact row parser must be developed against downloaded originals and coordinate-aware text extraction; it must not be inferred from a race-heading test fixture.

Do not populate fields that the PDF does not supply:
- `horse_id` and `jockey_id`: resolve from official result HTML/profile links or an exact existing-DB cross-check. A horse-name-only fuzzy match is never an ID.
- Per-horse `last3f`: the PDF's `上り3F` is a race-level aggregate, not an individual runner's final 3F. Leave it null unless a separate official per-horse source confirms it.
- `finish_rank` for `中` or `失`: do not invent a numeric placing.
- `n(降)`: preserve the raw status and verify final placing against the official final result before converting it.

Starter/history semantics must follow the existing audit policy: `中`, `失`, and demoted runners are actual starters; `除` and `取` are not starters. Starter status and valid numeric finish result are separate concepts.

## Staging schema and DB compatibility

The existing `entries` table in `scripts/build_dataset.py` has a composite primary key `(race_id, horse_no)`. It requires non-null `horse_id` and `horse_name`; fields include `finish_rank`, `result_status`, `finish_seconds`, `margin_text`, `final_win_odds`, `final_popularity`, `last3f`, `body_weight`, `passing_order`, and `draw`.

Because PDF-only extraction cannot guarantee `horse_id`, the parser must first emit a **separate staging dataset** where unresolved identifiers may remain null. No direct insert into `entries` is allowed. A later promotion step may be proposed only after identity resolution and full reconciliation pass.

Keep, at minimum:
- source PDF filename and SHA-256;
- source page index and race-block heading identity;
- raw extracted row text and normalized fields;
- parser version;
- field-level provenance and confidence/status;
- unresolved ID and result-status flags;
- manual-review reason where applicable.

## Acceptance gates before any DB promotion

1. All 23 PDFs pass signature, size, SHA-256 and official-host acquisition checks.
2. Every one of the 149 target race IDs maps to exactly one race block; no target is missing or duplicated.
3. Every race block agrees with expected date, venue and race number.
4. Parsed runner-row count equals the official declared field size for every race.
5. Horse numbers are unique within a race and within the valid range; no duplicate runner row is silently discarded.
6. Runner names and horse numbers reconcile with official result HTML where available; horse IDs are exact profile-link IDs, never fuzzy name guesses.
7. Finish statuses, demotions, withdrawals and exclusions are preserved separately; no fabricated placing or starter count.
8. Race-level payout/pace sections are not mistaken for runner rows.
9. PDF-only unsupported fields remain null.
10. The staging report records all discrepancies. Any unresolved discrepancy blocks that race from promotion.
11. Existing SQLite file hash and row counts remain unchanged during acquisition, parsing and staging tests.
12. A second independent reconciliation compares all promoted rows against the official source before a copied/staged database is considered for model rebuilding.

## Current implementation status

- `scripts/segment_jra_pdf_text.py`: strict date/venue/race-number segmentation only.
- `scripts/jra_pdf_geometry.py`: converts PyMuPDF word tuples into positioned words and groups them into rows with a bounded vertical spread; it does not infer runner fields or semantic columns.\n- `scripts/jra_pdf_columns.py`: assigns positioned words to explicitly configured x-coordinate bands and joins text within each cell. It rejects overlapping bands and unassigned words by default; it does not guess boundaries or interpret field values.\n- `scripts/jra_pdf_runner_fields.py`: strictly normalizes caller-supplied, already-separated cells (frame/horse number, sex-age, assigned weight, body weight, finish/status, time, margin, odds, popularity). It preserves raw cells, rejects unknown or malformed values, leaves blanks null, and does not infer column positions, IDs, or database values.
- `tests/test_jra_pdf_runner_fields.py`: synthetic tests for numeric normalization, full-width digits, non-finishers, demotion handling, malformed values, and unknown fields.
- `scripts/jra_pdf_runner_validation.py`: validates already-extracted runner candidates for race identity, declared field size, unique/in-range horse numbers, source hash/page provenance, raw row/name presence, and conservative finish-status/rank consistency. Unresolved horse IDs remain null; this is validation only, not PDF parsing or DB insertion.\n- Column boundaries must be measured from the original PDF layout and reviewed before use. Synthetic tests demonstrate mechanics only; they do not establish real JRA column coordinates.
- `tests/test_segment_jra_pdf_text.py`: synthetic tests for valid matches, full-width digits, wrong date, wrong venue, missing/duplicate headings, duplicate IDs and race-ID/race-number mismatch.
- Coordinate grouping, explicit column assignment, and runner-candidate validation have synthetic tests only; no real-JRA-PDF geometry, column boundaries, or extracted runner rows have been validated.
- No runner-row parser has been accepted. The new runner-candidate validator checks staged records after extraction; it does not yet extract any fields from a PDF.
- No official PDF has been downloaded or parsed by this workflow.
- No database has been modified.


## Composed race candidate pipeline
- Added `scripts/jra_pdf_race_pipeline.py` to compose explicit column splitting, strict cell normalization, and runner candidate validation for one race.
- The caller supplies already-selected runner rows, measured x-coordinate bands, target race ID, declared field size, PDF SHA-256, and zero-based page index. Every supplied row must parse; unassigned words and count/identity errors fail the race. Results are sorted by horse number.
- The output retains parsed field values and the validation candidate, with horse IDs unresolved. It does not read PDF files, identify runner rows automatically, infer layout, or write to SQLite.
- Added 6 synthetic tests for sorting, non-finisher status, row-count mismatch, unassigned words, provenance, and required fields.
- The first implementation's race-ID regex was corrected during review; column bands are now materialized once so an iterator can safely be reused across rows.
- GitHub Actions has not reported a run for these latest commits. The 6 new tests and previous 8 field tests are therefore not claimed as CI-verified.
- This pipeline is a composition of synthetic-tested primitives, not proof of extraction accuracy. The next gate is to acquire an original JRA PDF, inspect actual row/column geometry, define reviewed row-selection and column-band rules, and compare extracted counts and values against the official result.


## Explicit vertical runner-row selection
- Added `RunnerRowBand` and `select_runner_rows_from_page_words` to the composed race pipeline.
- The caller must provide reviewed y-coordinate intervals for each expected runner row. Each interval must contain exactly one geometric text row; empty bands, multiple rows, overlapping bands, and words outside all configured bands are hard errors.
- This is intentionally operator-configured rather than an automatic horse-row detector. It prevents headers/footers from being silently accepted or discarded, but depends on accurate per-page measurements from original PDFs.
- Added 5 synthetic tests for successful selection and the main failure modes.
- No GitHub Actions run is currently reported for the latest commits, so these tests remain unverified by CI. No real PDF layout has been measured and no real race has been extracted.


## Field-by-field reconciliation (reference-driven)
- Added `scripts/jra_pdf_reconciliation.py` to compare explicitly selected extracted fields against an independently supplied reference mapping.
- Default comparison is exact after Unicode NFKC and whitespace normalization. Numeric tolerance is never implicit; the caller must explicitly configure a decimal tolerance per requested field.
- Differences are classified as `mismatch`, `missing_extracted`, or `missing_reference`. Null on both sides is treated as no difference; this does not prove the field was independently verified.
- Missing keys, duplicate/empty field lists, unrequested tolerances, invalid numeric values, and negative tolerances fail closed.
- Added 9 synthetic tests. No actual official reference dataset has been loaded, and no 149-race reconciliation has been run. The comparator does not promote data or write to SQLite.


## CI follow-up for reconciliation addition
- The first PR CI run after adding the comparator executed 67 tests but failed to import `test_jra_pdf_race_pipeline.py` because a prior edit had left literal backslash-n sequences in its import statement.
- Corrected that test import in commit `4691a426d61d1bd89a47753a77f7dad924a5e7e1`.
- A new workflow run has not yet been returned for the correction; the suite is therefore pending re-verification. The 9 reconciliation tests did pass in the failed run, but the overall suite did not.


## Race-level quality audit (synthetic only)
- Added `scripts/jra_pdf_race_audit.py` to aggregate one race's extracted horse numbers and per-runner reconciliation reports.
- Checks missing, duplicate, and out-of-range horse numbers; counts field-level mismatches and missing values; identifies runners without a comparison report; summarizes missing/unexpected race IDs across the expected manifest.
- Exposes separate `structurally_complete` and `fully_reconciled` flags. Structural completeness alone is not proof of correctness. Full reconciliation requires a report for every expected horse number and zero differences in every report.
- Added 10 synthetic tests, including invalid identity and incomplete comparison cases.
- The latest commit has no reported Actions run yet. Tests are not claimed as CI-verified. No actual JRA PDF or independent official reference dataset has been processed; no database writes or promotion logic exist.


## Local aggregate audit CLI (synthetic only)
- Added `scripts/build_jra_pdf_audit_report.py` to load a private JSON staging file, validate its schema, and produce a compact aggregate JSON quality report using the race-audit module.
- Input requires the expected race-ID inventory plus per-race expected field size, extracted horse numbers, and per-runner reconciliation reports. IDs must be 12-digit strings; unknown keys, duplicate lists, malformed statuses, and invalid data types fail closed.
- The CLI writes only the requested report file and does not modify its input, PDFs, SQLite, or model files. The staging JSON and report belong in ignored local paths such as `private_input/` and `output/`; never commit them.
- Added 7 synthetic tests for report contents, complete/incomplete reconciliation, strict schema failures, and input immutability.
- This is an orchestration/serialization layer only. No private staging data has been supplied to it, no original PDF has been acquired, and no actual JRA race has been audited. New tests are pending CI verification.
- Example (run locally after preparing the private staging JSON): `python -m scripts.build_jra_pdf_audit_report --input private_input/jra_pdf_staging.json --output output/jra_pdf_audit.json`.


### Local audit input shape (synthetic example only)

The following is a schema example, not JRA data. Store the real file under the ignored `private_input/` directory.

```json
{
  "expected_race_ids": ["202410010101", "202410010102"],
  "races": [
    {
      "race_id": "202410010101",
      "expected_runner_count": 2,
      "extracted_horse_nos": [1, 2],
      "reconciliations": [
        {
          "race_id": "202410010101",
          "horse_no": 1,
          "compared_fields": ["finish_rank", "jockey_name"],
          "differences": []
        },
        {
          "race_id": "202410010101",
          "horse_no": 2,
          "compared_fields": ["finish_rank"],
          "differences": [
            {
              "field": "finish_rank",
              "extracted": 3,
              "reference": 2,
              "status": "mismatch"
            }
          ]
        }
      ]
    }
  ]
}
```

A race absent from `races` is reported as missing. A supplied race can be structurally complete while not fully reconciled; every expected horse number needs a reconciliation report with no differences before `fully_reconciled` becomes true. The report is an audit artifact, not an approval to promote rows into the production database.


## Per-race processing progress ledger (synthetic only)
- Added `scripts/jra_pdf_progress.py` with explicit stages: `pending`, `pdf_acquired`, `segmented`, `extracted`, and `reconciled`; exception states are `manual_review` and `blocked`.
- The transition validator rejects skipped stages and prevents a manual-review/blocked race from advancing without explicit resolution. The ledger does not itself mutate state or source files.
- Added `scripts/build_jra_pdf_progress_report.py` to summarize a private progress JSON into counts, missing/unexpected race IDs, and the next action by state. It does not include horse names or extracted race content.
- The report always emits `promotion_authorized: false`; reconciliation is not production approval. DB promotion remains a separate, explicitly approved operation outside this workflow.
- Example input fields: `expected_race_ids` plus `races: [{race_id, status, note_code?}]`. Keep real progress JSON under ignored local paths, never in the public repository.
- Added 14 synthetic tests across the state machine and CLI. CI result pending for the latest commit; no actual race has advanced through this ledger.
- Example: `python -m scripts.build_jra_pdf_progress_report --input private_input/jra_pdf_progress.json --output output/jra_pdf_progress_report.json`.


## PDF-level retry targeting and race coverage (synthetic only)
- Added `scripts/jra_pdf_batch_progress.py` to connect each private PDF key to its expected race IDs and acquisition state.
- States are `pending`, `acquired`, `validated`, and `failed`. Only pending/failed PDF keys appear in the retry target list; acquired/validated PDFs are not needlessly re-downloaded.
- The summary separately reports uncovered race IDs and race IDs mapped by more than one PDF. Unexpected race IDs fail validation rather than being silently ignored.
- Added `scripts/build_jra_pdf_batch_report.py` for local JSON input/output. It never performs network retries itself, downloads PDFs, changes the mapping, or writes to SQLite. The output explicitly states `automatic_network_retry_performed: false` and `promotion_authorized: false`.
- Added 13 synthetic tests across batch mapping and CLI validation. CI status for these newest additions is pending.
- Keep the real PDF mapping/status JSON in ignored local paths. The repository contains no private mapping or source data.
- Example: `python -m scripts.build_jra_pdf_batch_report --input private_input/jra_pdf_batches.json --output output/jra_pdf_batch_report.json`.


## Hash-verified local resume (synthetic tests only)
- Added `--resume` to `scripts/download_jra_pdfs.py`. It consults the previous local `download_audit.csv` and reuses a PDF only if the URL and filename match, the previous row was successful, and the existing file still matches the recorded byte count, PDF signature, and SHA-256.
- Duplicate URL entries in the old audit are treated as ambiguous and are not trusted. Missing, changed, truncated, or mismatched files fall back to the normal download path.
- Reused items are marked `already_verified`; the summary separately reports `pdf_files_reused_verified`. This does not claim a new HTTP fetch occurred.
- Added 7 synthetic tests for valid reuse, repeated resume runs, and fail-closed cases. CI status for this latest addition is pending.
- Usage: `python -m scripts.download_jra_pdfs --manifest private_input/jra_official_pdf_manifest.csv --out output/jra_pdfs --resume`.
- Resume only trusts the local audit as a pointer to the expected hash; the actual file bytes are rehashed each time. No remote download, real PDF verification, SQLite write, or model promotion has been performed by this change.

## PDF batch integrity ledger
- The private PDF batch ledger records a per-PDF attempt count and a stable failure code for failed acquisitions. Acquired/validated entries must also carry a lowercase 64-character SHA-256 and a byte count of at least 1,024; entries missing either value are rejected.
- The local batch report emits these integrity fields alongside the race-ID mapping and retry list. Only pending/failed batches are retry candidates; successful batches are not selected for retry.
- The ledger validates metadata consistency but does not itself hash local files or trigger network retries. The downloader's resume path independently recomputes file size and SHA-256 before reusing a prior PDF.
- Synthetic tests cover invalid hashes/sizes and report serialization. No real PDF has been downloaded in this workflow, so no real-file digest has yet been recorded here.
