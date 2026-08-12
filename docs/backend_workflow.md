# Backend Workflow

Lavoisier is backend-first. The Streamlit app is only a thin demonstration layer.

## Controlled MVP Scope

- Material class: MOF only
- Source target: CRAFTED 2.0.1 after manual approval
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
  -> weakly supervised ML triage
  -> similarity triage for unfamiliar candidates with known descriptors
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

## ML Triage Command

After the measured/rule-based slice has been exported locally, run candidate
classification:

```bash
python scripts/run_ml_triage.py
```

The ML triage layer uses weak supervision: transparent engineering rules create
candidate review labels, then a `RandomForestClassifier` learns those labels
from tabular screening features. This is a review aid only. It does not replace
comparability checks, measured ranking, or human review.

Ignored local outputs:

```text
reports/crafted_ml_triage/classified_records.csv
reports/crafted_ml_triage/ml_triage_summary.json
```

## Similarity Triage For Unfamiliar Candidates

The first virtual-lab-oriented backend primitive is
`triage_unfamiliar_candidate()` in `src/carbonsense/ml_triage.py`.

It accepts:

- a known reference table, such as the ranked CRAFTED slice;
- one unfamiliar candidate represented by the same supported descriptors;
- a requested neighbor count `k`.

It returns:

- nearest known MOF records;
- similarity distances and distance-derived vote weights;
- a predicted review class, such as `promising_candidate`,
  `balanced_candidate`, `poor_selectivity`, or `low_capacity`;
- a cautious R&D recommendation, such as `prioritize_deeper_review`,
  `consider_for_deeper_review`, `review_with_caution`, or
  `deprioritize_until_new_evidence`;
- a benchmark verdict comparing the candidate's core metrics against known
  records, such as `above_reference_candidate`, `competitive_with_reference`,
  `mixed_against_reference`, or `below_reference_or_risky`;
- a nearest-neighbor advantage verdict showing whether the candidate appears
  better, mixed, or not clearly better than the specific known MOFs it most
  resembles;
- next experiment steps, such as completing missing descriptors, checking
  regeneration risk, validating CO2/N2 selectivity, comparing against nearest
  neighbors under identical assumptions, or adding humidity/cycling evidence;
- warnings when the candidate is missing descriptors or appears far from the
  known reference space.

This does not prove that a new MOF is experimentally viable. It answers a more
defensible first-pass question:

```text
Does this unfamiliar candidate resemble known records that are worth deeper
review, or does it resemble records that were weak, risky, or incomplete?
```

Run the candidate script with a ranked reference table and one candidate JSON
file:

```bash
python scripts/evaluate_unfamiliar_candidate.py \
  --reference reports/crafted_real_slice_export/ranked_records.csv \
  --candidate data/sample_unfamiliar_candidate.json \
  --output-dir reports/unfamiliar_candidate_triage \
  --k 5
```

Ignored local outputs:

```text
reports/unfamiliar_candidate_triage/nearest_neighbors.csv
reports/unfamiliar_candidate_triage/candidate_similarity_summary.json
reports/unfamiliar_candidate_triage/candidate_review_report.md
```

The summary includes metric percentiles for CO2 uptake and CO2/N2 selectivity,
plus a first-pass heat-of-adsorption target-range check. These benchmarks are
separate from nearest-neighbor similarity: they help answer whether the
candidate is merely similar to known materials or actually competitive against
the reference distribution.

`neighbor_advantage_verdict` is narrower than the benchmark verdict. It compares
the candidate against only the nearest known records, so a candidate can be
competitive overall while still showing no clear advantage over the closest
known alternatives.

`next_experiment_steps` turns the verdict into a small virtual-lab work order.
These steps are not automatic lab instructions; they identify the next evidence
that would make the candidate decision less uncertain.

`candidate_review_report.md` is the human-readable export. It summarizes the
candidate verdict, metric benchmarks, nearest-neighbor comparison, nearest
known records, next experiment steps, and limitations for review without
opening the raw JSON.

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
7. Review weakly supervised ML triage output as a secondary review aid.
8. Add a small candidate-input script or API endpoint around similarity triage.
9. Only then improve the UI around this backend.

## Roadmap Concepts After Provenance

- Variant-aware MOF identity and comparability:
  see `docs/variant_aware_mof_screening.md`.
