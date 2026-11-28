# JRA result-PDF research utilities

This repository snapshot contains a small, local-only toolkit for validating a reviewed JRA result-PDF manifest, acquiring official result PDFs, inspecting PDF page geometry, and validating staged extraction/reconciliation records.

It is **not** a betting service, model deployment, historical database, or complete race-data collection system. No private race manifest, PDF, extracted runner data, odds, predictions, database, model, or generated report belongs in Git or GitHub Actions artifacts.

## Requirements

- Python 3.11+
- Install the pinned runtime dependency:

```sh
python -m pip install -r requirements.txt
```

The direct PDF backend dependency is PyMuPDF. `requirements.txt` pins PyMuPDF 2.2 and the transitive packages resolved by CI on Python 3.11, so the installation is repeatable. The data validation and report-building modules otherwise use Python's standard library and local `scripts.*` modules.

PyMuPDF is dual-licensed under AGPL-3.0 or a commercial license. Review its license terms before redistributing or embedding it in another product.

## Local command-line tools

Run commands from the repository root so the `scripts` namespace package resolves correctly. Use private local paths for all inputs and outputs.

### Validate a reviewed manifest and download official PDFs

```sh
python -m scripts.download_jra_pdfs \\
  --manifest /path/to/private_input/pdf_manifest.csv \\
  --out /path/to/private_output/pdfs
```

Optional count checks can be supplied explicitly with `--expected-races N` and `--expected-pdfs N`. Use `--resume` only when the output directory contains a prior download audit; reuse requires matching URL, filename, PDF signature, byte count, and SHA-256.

The downloader accepts HTTPS result-PDF URLs on the official JRA hosts only, validates redirects, checks the PDF signature, applies a 50 MiB per-file ceiling, and writes a local CSV/JSON acquisition audit. It does not modify a database. The network request is performed only when this command is explicitly run; CI never downloads JRA content.

### Audit a private mapping

```sh
python -m scripts.jra_pdf_mapping_audit \\
  --mapping /path/to/private_input/race_pdf_mapping.csv \\
  --manifest /path/to/private_input/pdf_manifest.csv \\
  --output /path/to/private_output/mapping_audit.json
```

### Inspect PDF geometry

```sh
python -m scripts.inspect_jra_pdf_layout \\
  --pdf-dir /path/to/private_output/pdfs \\
  --out /path/to/private_output/layout_audit.json
```

The layout report contains page geometry, counts, source filenames, and PDF SHA-256 values. It deliberately does not emit extracted raw text, horse names, jockey names, or odds. Treat the report and its filenames as private metadata nonetheless.

### Build local progress/audit reports

The report builders take explicit JSON input and output paths:

- `scripts.build_jra_pdf_progress_report`: `--input`, `--output`
- `scripts.build_jra_pdf_batch_report`: `--input`, `--output`
- `scripts.build_jra_pdf_integrated_progress`: `--input`, `--output`
- `scripts.build_jra_pdf_audit_report`: `--input`, `--output`

The remaining `scripts.jra_pdf_*` modules provide reusable parsing, geometry, reconciliation, validation, and state-machine functions; they are library modules rather than standalone commands.

## Tests and CI

Run the synthetic unit tests locally:

```sh
python -m unittest discover -s tests -p 'test_*jra_pdf*.py' -v
```

The read-only GitHub Actions workflow installs `requirements.txt`, imports PyMuPDF, and runs synthetic tests. It does not use private inputs, download JRA PDFs, upload artifacts, or write repository contents.

## Data handling

- Keep the reviewed manifest, mapping CSV, downloaded PDFs, extracted text, staged runner records, real progress ledgers, and all generated reports outside the repository.
- Do not commit real race IDs, runner names, odds, results, database files, model files, logs, or credentials.
- Do not upload private files as Actions artifacts or attach them to issues/PRs.
- Keep `private_input/`, `private_output/`, `output/`, `data/`, `datasets/`, `snapshots/`, `models/`, and `logs/` local and ignored.
- The tools are read-only with respect to the existing historical SQLite database; they do not migrate data into it.

Before running any real acquisition, verify the source URL, data-use terms, output location, disk capacity, and local backup. This README does not authorize acquisition or transfer of private data.
