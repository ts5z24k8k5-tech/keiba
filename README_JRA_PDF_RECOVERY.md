# JRA official PDF recovery (research-only)

This workflow downloads official JRA result PDFs for local research. It does not
write to the repository, the historical SQLite database, or any model.

## Required private secret

Do **not** commit the race manifest. Add a repository Actions secret named
`JRA_PDF_MANIFEST_B64` containing the Base64-encoded contents of the reviewed
`jra_official_pdf_manifest_23.csv` file. The manifest covers 23 official PDFs
and 149 target race IDs.

On macOS, create the value with:

```sh
base64 < jra_official_pdf_manifest_23.csv | tr -d '\n'
```

Copy the output into Settings → Secrets and variables → Actions → New repository
secret. Keep the original CSV outside the repository. The `.gitignore` excludes
`private_input/` and `output/jra_pdfs/` as an additional safeguard.

## Run

After this workflow has reached the default branch, open Actions → **Research -
acquire official JRA PDFs** → Run workflow. It runs only by manual dispatch.

The job validates the manifest, runs unit tests, downloads only HTTPS PDFs from
the official JRA result-PDF path, checks the PDF signature and minimum size,
and records byte counts and SHA-256 hashes. The output is published as a
7-day Actions artifact.

## Public-repository stop condition

The repository must be **private** before this workflow is run. GitHub Actions
artifacts can be downloaded by people who have read access to the repository;
for a public repository, that means the PDF artifact must be treated as public.
The workflow now checks repository visibility before restoring the secret or
downloading anything, and stops unless visibility is `private`. It also uploads
an artifact only after the full acquisition and layout-audit steps succeed.
Do not remove this guard to work around the current public-repository setting.

## Safety boundaries

- `permissions: contents: read`; no repository write permission.
- No scheduled or push trigger.
- No SQLite, model, prediction, odds, or training-data writes.
- The manifest is restored from an Actions secret and is not uploaded as an artifact.
- Downloaded PDFs and acquisition audit are separate from any later parsing or
  database restoration.
- A successful download does not establish that extracted rows are correct.
  PDF parsing, race-ID/horse-ID matching, and staged database validation remain
  separate steps.

## Parser acceptance boundary

The research branch also contains `scripts/segment_jra_pdf_text.py`, a strict
race-block segmenter. It accepts a block only when the official heading's date,
venue and race number match the reviewed target mapping. It does not parse
runner rows, resolve horse IDs, or write to SQLite.

See `docs/JRA_PDF_PARSER_ACCEPTANCE.md` for runner-field provenance,
non-finisher handling, staging requirements and the acceptance gates before
any database promotion. The PR test workflow runs downloader, race-segmentation, and coordinate-geometry
unit tests on updates to this isolated research branch. Coordinate grouping is
currently validated only with synthetic fixtures, not real JRA PDF binaries.
