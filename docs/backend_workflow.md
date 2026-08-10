# Backend Workflow

Lavoisier is backend-first. The Streamlit app is only a thin demonstration layer.

## Controlled MVP Scope

- Material class: MOF only
- Source target: CRAFTED 2.0.0 after manual approval
- Evidence type: computational GCMC
- Application context: post-combustion-style CO2/N2 adsorption screening
- Controlled slice: one temperature, one force field, one charge method, and fixed pressure/metric basis

## Pipeline

```text
source registry
  -> source approval
  -> raw data kept out of Git unless redistribution is explicitly approved
  -> CRAFTED adapter / processed fixture
  -> schema validation
  -> comparability engine
  -> rank eligibility
  -> ranking
  -> exportable review tables
  -> transformation/provenance log
```

## Why Backend First

The differentiator is not a chat UI. It is the domain rule layer that prevents weak comparisons.

Lavoisier must be able to say:

```text
This value was extracted correctly,
but it is not rank-eligible because force field, charge method,
temperature, pressure, or material class differ from the comparison scope.
```

## Current Backend Modules

- `schema.py`: required fields and warning checks
- `comparability.py`: rank eligibility and blocking reasons
- `ranking.py`: ranking that excludes non-eligible records by default
- `crafted_adapter.py`: CRAFTED-like schema and controlled-slice adapter skeleton
- `pipeline.py`: end-to-end backend flow for validation, slice selection, comparability, ranking, and export metadata
- `export.py`: ranked, blocked, and metadata export files
- `ingestion/`: deterministic CSV and structured-text candidate extraction

## Fixture Command

Run the backend fixture pipeline:

```bash
python scripts/run_backend_fixture.py
```

It uses `data/crafted_like_fixture.csv`, a synthetic CRAFTED-like fixture. The output is written to:

```text
reports/backend_fixture_export/ranked_records.csv
reports/backend_fixture_export/excluded_records.csv
reports/backend_fixture_export/blocked_records.csv
reports/backend_fixture_export/screening_metadata.json
reports/backend_fixture_export/transformation_log.json
```

`excluded_records.csv` contains records outside the controlled slice, such as
non-MOF records or records using a different force field, charge method, or
temperature. `blocked_records.csv` contains records inside the controlled slice
that still failed comparability checks. Blocked rows include `block_type` and
`block_reason`, so a missing pair, pressure mismatch, condition mismatch, or
manual-review case is not silently hidden behind a generic rank failure. These
files demonstrate the backend contract only. They are not research findings.

`screening_metadata.json` summarizes the screening run: source label, source
status, controlled slice settings, ranking weights, row counts, and limitations.
`transformation_log.json` is the export receipt. It records the source file,
source checksum, license/source status, row counts, applied filters, generated
files, transformation steps, timestamp, and limitations. Every exported result
should be able to answer:

```text
Where did this result come from?
What was filtered out?
Why was it filtered or blocked?
Which exact settings and files produced the result?
```

## CRAFTED Archive Inspection Command

After completing `docs/crafted_approval_checklist.md` and downloading CRAFTED
locally, inspect the archive before parser work:

```bash
python scripts/inspect_crafted_archive.py path/to/crafted/archive-or-folder
```

The inspection writes:

```text
reports/crafted_archive_inspection/archive_manifest.csv
reports/crafted_archive_inspection/pressure_availability.csv
reports/crafted_archive_inspection/candidate_column_map.json
reports/crafted_archive_inspection/inspection_summary.md
```

This step does not ingest or rank real data. It only shows what files, columns,
gases, pressures, and conditions are available so the first exact-match slice
can be chosen responsibly.

## Real CRAFTED Slice Command

After local approval, download, extraction, and archive inspection, run the
selected exact slice:

```bash
python scripts/run_crafted_real_slice.py
```

The current selected slice is:

```text
CO2 = 0.2 bar
N2 = 1.0 bar
T = 298 K
force field = UFF
charge method = DDEC
```

The command writes ignored local outputs:

```text
data/processed/crafted_2_0_1/crafted_isotherm_long.csv
data/processed/crafted_2_0_1/crafted_screening_slice.csv
data/processed/crafted_2_0_1/crafted_parser_blocked_records.csv
reports/crafted_real_slice_export/
```

Do not commit those real processed outputs until public-sharing rights are
reviewed separately.

## Next Backend Milestones

1. Complete `docs/crafted_approval_checklist.md` before downloading or parsing
   real CRAFTED data.
2. Run `scripts/inspect_crafted_archive.py` on the approved local archive.
3. Choose exact CRAFTED force field, charge method, temperature, and pressure
   pair after archive inspection.
4. Run `scripts/run_crafted_real_slice.py` locally and review generated outputs.
5. Replace the synthetic fixture with a small approved processed CRAFTED slice
   only after processed-data sharing is approved.
6. Replace the synthetic transformation log with one backed by approved CRAFTED
   archive checksums and inspected source-file lineage.
7. Only then improve the UI around this backend.

## Roadmap Concepts After Provenance

- Variant-aware MOF identity and comparability:
  see `docs/variant_aware_mof_screening.md`.
