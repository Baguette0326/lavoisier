# Lavoisier End-of-Summer MVP PRD

## Product definition

Lavoisier is a local backend-first decision-support tool for reviewing and shortlisting MOF carbon-capture adsorption records. It turns a documented dataset into a transparent comparison: the user selects a controlled MOF/GCMC slice, checks whether records are comparable, adjusts screening priorities, inspects tradeoffs, and exports a reviewable shortlist.

The first domain is MOFs for post-combustion-style CO2/N2 screening using CRAFTED-like computational GCMC records. Lavoisier does not discover materials or replace process and experimental validation. â€œAI-assistedâ€ describes possible future assistance; the MVPâ€™s core value is deterministic, inspectable screening.

## Problem statement

Public MOF carbon-capture screening data is difficult to compare responsibly. A high CO2 uptake can be misleading when pressure, temperature, adsorbate, force field, charge method, evidence type, selectivity, or regeneration implications differ. Students and early-stage researchers need a faster way to narrow a dataset without hiding these limitations behind a black-box score.

## Target user and job

The primary user is a chemical-engineering student or research assistant performing an initial MOF screening review. Their job is to turn one approved CRAFTED-style dataset slice into a defensible shortlist for deeper literature, process, or experimental review.

## Recruiter-facing significance

The MVP should demonstrate that its author can:

- translate adsorption and process constraints into a usable data model;
- build a reproducible ingestion, validation, scoring, and reporting workflow;
- distinguish computational, predicted, and experimental evidence;
- communicate uncertainty and prevent invalid comparisons;
- test decision logic and explain engineering tradeoffs to a non-specialist.

The strongest portfolio claim is not â€œAI found the best material.â€ It is â€œI built a transparent screening workflow that makes heterogeneous evidence safer and faster to review.â€

## Core record

The unit of comparison is a **material-performance record**, not a material alone. Each record represents one material evaluated under a stated capture context and set of conditions.

Minimum required fields:

- material identifier;
- evidence type;
- source/provenance identifier;
- material class, fixed to MOF for the MVP;
- capture context, fixed to post-combustion-style CO2/N2 screening for the MVP;
- simulation method, force field, and charge method for computational records;
- temperature and pressure, when applicable;
- gas composition or measurement basis, when applicable;
- at least one screening metric.

Supported screening metrics may include CO2 uptake, CO2/N2 selectivity, heat of adsorption, surface area, pore volume, density, and humidity evidence. Units and metric definitions must be explicit. Missing information remains visible and affects confidence; it is never silently inferred.

## User workflow

1. The user opens Lavoisier and loads the bundled approved demonstration dataset or uploads a compatible CSV.
2. Lavoisier validates required fields, units, evidence labels, and condition metadata. Blocking errors stop ranking; non-blocking gaps produce warnings.
3. The user selects one capture context and a comparable subset of records.
4. The user chooses available criteria and adjusts their weights. Lavoisier shows the scoring direction and normalizes active weights.
5. Lavoisier ranks the subset and displays each candidateâ€™s score, component contributions, provenance, evidence type, missing-data warnings, and engineering tradeoff flags.
6. The user changes a weight and can see why the order changed.
7. The user marks or selects candidates for human review and exports a shortlist plus a compact screening report containing the filters, weights, warnings, and source metadata.

## Functional requirements

### Dataset and provenance

- Ship one small, legally usable, manually approved CRAFTED-like MOF dataset slice with enough records to demonstrate ranking changes.
- Associate every record with a source-registry entry, retrieval date, licence/access note, and evidence type.
- Keep computational GCMC evidence visibly distinct from experimental or other predicted evidence.
- Do not merge aliases, convert ambiguous units, or approve a source automatically.

### Validation and comparability

- Validate required columns, numeric coercion, supported units, and allowed categorical values.
- Treat missing material class, simulation method, force field, charge method, provenance, or metric units as blocking for official ranking.
- Warn when operating conditions, humidity evidence, or recommended metrics are absent.
- Prevent or prominently warn against ranking records from incompatible contexts or conditions together.

### Screening and explanation

- Filter by controlled comparison slice before ranking.
- Rank with deterministic, adjustable weighted criteria only.
- Show the contribution of each active criterion to the final score.
- Show missing-data and tradeoff flags beside each record.
- Label all output as a screening shortlist, not a validated leaderboard or recommendation.

### Export

- Export the ranked/selected records as CSV.
- Export or render a screening summary containing dataset/source, filters, weights, ranking timestamp, warnings, and limitations.
- A reviewer must be able to reproduce the displayed order from the exported inputs and settings.

## User stories

1. As a chemical-engineering student, I want to load a documented adsorbent dataset so that I can begin screening without writing one-off analysis code.
2. As a reviewer, I want invalid or ambiguous records flagged before ranking so that I do not compare misleading values.
3. As a reviewer, I want to isolate one capture context and comparable conditions so that the shortlist has a defensible basis.
4. As a reviewer, I want to adjust criterion weights so that I can explore different engineering priorities.
5. As a reviewer, I want to see component scores and tradeoff warnings so that I understand why a material ranks highly.
6. As a reviewer, I want evidence type and provenance attached to every result so that I can judge the strength of each claim.
7. As a reviewer, I want to export the shortlist and its settings so that another person can reproduce and challenge my screening decision.
8. As a recruiter, I want a short guided demo so that I can see the candidate connect chemical-engineering judgment, software design, testing, and responsible data use.

## Implementation boundaries

Keep the product as a small set of testable modules:

- **record contract:** canonical field names, units, allowed values, and comparability keys;
- **validation gate:** blocking errors and review warnings;
- **screening engine:** filters, normalized weighted scoring, component contributions, and deterministic ordering;
- **review flags:** missing-data, evidence, humidity, selectivity, and regeneration warnings;
- **provenance registry:** source and approval metadata;
- **report builder:** reproducible export metadata and shortlist output;
- **Streamlit interface:** orchestration and presentation only.

The current schema, ranking, flags, source registry, and Streamlit scaffold are starting points. The MVP should deepen these modules rather than add unrelated features.

## Testing decisions

Tests should assert external behavior, not internal implementation. Minimum coverage:

- schema acceptance and blocking failures;
- unit/category validation and comparability warnings;
- ranking direction, weight normalization, missing-value behavior, ties, and repeatability;
- correct component contributions and tradeoff flags;
- provenance preserved through filtering, ranking, and export;
- one end-to-end fixture from approved input to reproducible shortlist.

## Success criteria

The MVP is complete when:

- a fresh local install can run the app and tests using documented commands;
- one approved demonstration dataset can complete the full workflow;
- users cannot silently create an official ranking across incompatible capture contexts;
- every displayed candidate includes provenance, evidence type, and review warnings;
- changing a weight produces an explainable, reproducible ranking change;
- the exported shortlist preserves filters, weights, warnings, and source metadata;
- the full recruiter demo takes no more than five minutes;
- the README states the scientific and product limitations without overclaiming AI.

## Non-goals

- discovering, generating, or optimizing new materials;
- DFT, GCMC, molecular-dynamics, or process-simulation execution;
- predicting adsorption properties with machine learning;
- declaring a universally â€œbestâ€ adsorbent;
- replacing literature review, techno-economic analysis, experiments, or process design;
- automated scraping or ingestion from restricted sources;
- automatic dataset approval, entity resolution, or ambiguous unit conversion;
- production deployment, accounts, collaboration, or a general-purpose paper reader;
- supporting COFs, zeolites, activated carbons, amines, membranes, or other carbon-capture technology families in the MVP.

## Milestone plan

### M1 â€” Freeze the comparison contract

Define the MOF material-performance record, canonical units, CRAFTED-style comparability keys, and blocking versus warning conditions. Add representative valid and invalid fixtures. Exit condition: the contract can describe every record in the planned demo dataset without silent assumptions.

### M2 â€” Integrate one approved dataset

Complete licence/provenance review, create a small processed demonstration table, and link every row to the source registry. Exit condition: the dataset passes validation and its transformation is documented and reproducible.

### M3 â€” Complete the screening loop

Add context/evidence filters, strengthen validation, expose component contributions, and make missing-data handling explicit. Exit condition: tests prove deterministic ranking and prevent or clearly block incompatible comparisons.

### M4 â€” Make the result reviewable

Present provenance and warning details, add human shortlist selection, and produce a screening summary with settings and limitations. Exit condition: an exported result can be independently reproduced and reviewed.

### M5 â€” Portfolio hardening

Run the clean-install path, complete the end-to-end test, refine README screenshots and limitations, and rehearse the demo. Exit condition: a recruiter can understand the engineering problem, workflow, tradeoff, and result in five minutes without setup improvisation.

## Five-minute demo script

1. **Frame the problem (30 seconds):** â€œAdsorbent datasets contain promising numbers measured or predicted under different conditions. Lavoisier helps create a reviewable shortlist without pretending those numbers are universally comparable.â€
2. **Load evidence (30 seconds):** Open the approved demonstration dataset and show its source, licence note, evidence type, and record count.
3. **Validate (45 seconds):** Show the validation summary and explain one blocking comparability rule and one non-blocking missing-data warning.
4. **Choose the engineering case (45 seconds):** Select the controlled post-combustion-style CO2/N2 MOF/GCMC slice and filter to comparable records.
5. **Screen candidates (60 seconds):** Adjust uptake, selectivity, and heat-of-adsorption weights. Show the ranking and component contributions.
6. **Challenge the result (45 seconds):** Open a top record, point out its provenance and a tradeoff or evidence warning, then change one weight to explain a ranking change.
7. **Hand off for review (30 seconds):** Select candidates and export the shortlist/screening summary.
8. **Close (15 seconds):** â€œThe output is a reproducible screening decision for further review, not a claim that the top-ranked material is experimentally or economically best.â€

## Open decisions before implementation

- Which exact CRAFTED force field, charge method, pressure basis, and metric will be the default demo slice?
- Which approved dataset can legally ship as a small repository fixture?
- What exact condition fields define a comparable subset for that dataset?
- Should the screening summary be a rendered page, Markdown file, or PDF after CSV export?
