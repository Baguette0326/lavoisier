# Summer Roadmap

This roadmap records the original phase sequence. The refined MVP requirements, exit criteria, and recruiter demo are defined in [`end_of_summer_mvp_prd.md`](end_of_summer_mvp_prd.md).

## Phase 1: Product Scaffold

Goal: make the app real enough to click through with uploaded CSV data.

Deliverables:

- Streamlit app shell
- dataset upload
- schema validation
- weighted ranking
- tradeoff flags
- exportable shortlist
- tests for scoring and validation

See `docs/learning_task_page.md` for the parallel technical-learning track needed to explain the engineering significance of the project.

## Phase 2: Source Discovery

Goal: identify legal, usable carbon-capture material datasets.

Priority sources:

- OpenDAC 2023 and OpenDAC 2025
- NIST adsorption database or ISODB-style sources
- CoRE MOF / curated MOF structure-property datasets
- Zenodo, Figshare, and Dataverse materials datasets
- GitHub repositories with explicit licences

Deliverables:

- `config/source_registry.yaml`
- source check script
- provenance report
- manual approval checklist

## Phase 3: Approved Dataset Integration

Goal: integrate one real, approved dataset.

Deliverables:

- raw data kept out of Git if redistribution is restricted
- metadata file
- approved processed table
- column mapping
- first dashboard ranking

## Phase 4: Explainability And Monitoring

Goal: make the software feel like decision support.

Deliverables:

- feature contribution summary
- missing-data and tradeoff warnings
- source-monitoring report
- change report when new records are added

Variant-aware MOF identity and comparability is a candidate later roadmap item,
not current MVP scope. See `docs/variant_aware_mof_screening.md`.

Condition-transfer prediction is also future scope, not current MVP scope. The
future question is: given one MOF tested or simulated at one temperature/pressure
slice, how might it perform at another slice? A defensible version should first
use available isotherm curves or interpolation, then only use ML as a
condition-transfer estimate with uncertainty and clear limits.

## End-Of-Summer Demo

Demo script:

1. open Lavoisier;
2. load approved dataset;
3. select capture context;
4. adjust ranking weights;
5. inspect top candidates;
6. view warnings and evidence type;
7. export shortlist;
8. show source registry and monitoring report.
