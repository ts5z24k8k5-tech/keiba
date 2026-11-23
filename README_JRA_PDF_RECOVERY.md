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
