# Lavoisier MVP Architecture

This document explains how the current MVP fits together. It is meant for a recruiter, reviewer, or future contributor who wants the system shape without reading every module first.

## Core Workflow

```text
approved/local source files
        |
        v
CRAFTED parser and schema validation
        |
        v
controlled CO2/N2 slice selection
        |
        v
comparability checks and review flags
        |
        v
ranking and export package
        |
        +--> Streamlit demo UI
        |
        +--> descriptor-based ML prediction
        |
        +--> virtual-lab candidate review reports
```

## Main Data Path

1. `scripts/run_crafted_real_slice.py`
   Loads the locally approved CRAFTED files, joins CRAFTED geometric descriptors, optionally joins CoRE MOF 2014 provenance fields, runs the controlled-slice screening pipeline, and exports review files.

2. `src/carbonsense/pipeline.py`
   Coordinates validation, filtering, comparability checks, ranking, and export metadata.

3. `src/carbonsense/comparability.py`
   Blocks or warns on records that should not be treated as directly comparable.

4. `src/carbonsense/ranking.py`
   Calculates deterministic screening scores from explicit engineering metrics and weights.

5. `src/carbonsense/export.py`
   Writes ranked, excluded, blocked, metadata, and transformation-log outputs so results can be traced back to their source and filtering choices.

## Descriptor And ML Path

1. `scripts/evaluate_descriptor_feature_sets.py`
   Compares baseline CRAFTED geometric descriptors against CoRE-enriched descriptors using repeated held-out validation.

2. `src/carbonsense/property_prediction.py`
   Trains target-specific `RandomForestRegressor` baselines for supported adsorption targets. The model uses structural descriptors, not the target metrics themselves, to avoid direct leakage.

3. `src/carbonsense/virtual_lab.py`
   Combines descriptor-based estimates, nearest-neighbor context, supplied-vs-predicted gap checks, and rule-based decision support for unfamiliar candidates.

4. `scripts/run_virtual_lab_demo.py`
   Generates synthetic candidate review packets that demonstrate how the virtual-lab workflow behaves for consistent, incomplete, and suspicious records.

## UI Path

`app/streamlit_app.py` is a recruiter-demo interface over the generated reports. It does not replace the backend pipeline. It reads exported CSV/JSON/Markdown files and presents three review views:

- ranked MOF screening records;
- candidate virtual-lab assessments;
- provenance, transformation logs, and limitations.

## Important Boundaries

- Lavoisier ranks and reviews existing records; it does not generate new MOFs.
- CRAFTED adsorption records are computational GCMC outputs, not experimental proof.
- CoRE MOF 2014 fields are structural/provenance enrichment, not additional adsorption measurements.
- The ML models are baseline decision-support estimates; they are not final viability judgments.
- Raw research datasets are kept out of the committed repo unless licence and attribution rules explicitly allow inclusion.

## Current Extension Points

- Add NIST/experimental adsorption data as a future validation layer.
- Expand identifier resolution for CoRE/QMOF joins without merging uncertain structural variants.
- Add condition-transfer modeling only after enough comparable pressure/temperature records exist.
- Deploy the Streamlit app or a static demo once public-data packaging is resolved.
