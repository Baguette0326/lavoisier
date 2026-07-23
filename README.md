# CarbonSense

CarbonSense is a software-first chemical-engineering portfolio project: a transparent backend-first review tool for screening MOF carbon-capture adsorption records from public or user-supplied datasets.

The project does not claim to discover a new best material. It helps users compare records from a controlled MOF/GCMC screening slice, understand tradeoffs, and produce a reviewable shortlist with provenance and comparability warnings.

The canonical end-of-summer scope, milestones, and demo are defined in [`docs/end_of_summer_mvp_prd.md`](docs/end_of_summer_mvp_prd.md).

## Summer Deliverable

By the end of summer, the target is a working local web app that can:

- load an approved materials dataset or user-uploaded CSV;
- validate required columns and units;
- filter records by controlled comparison scope;
- rank materials using adjustable criteria;
- flag tradeoffs such as high uptake but high regeneration penalty;
- explain which variables drive the ranking;
- export a shortlist and screening report;
- maintain a source registry for future automated monitoring.

The app opens with a small synthetic demo dataset so the review workflow can be explored without downloading data or calling an external service. Demo records are clearly labelled and are not research findings.

## Product Framing

Carbon-capture material screening is heavily studied in research settings. The software opportunity here is different: make complex screening data easier to inspect, rank, and review without overclaiming scientific certainty.

The tool is designed for human-in-the-loop screening:

```text
source registry -> dataset review -> schema validation -> ranking -> explainability -> human-approved shortlist
```

## Initial Scope

Focus on MOFs for post-combustion-style CO2/N2 adsorption screening. The first target source is CRAFTED 2.0.0 after manual licence/provenance approval.

Candidate variables:

- material identifier
- material class
- source and provenance
- capture context
- simulation method
- force field
- charge method
- pressure
- temperature
- CO2 uptake
- N2 uptake
- CO2/N2 selectivity
- Henry coefficient
- heat of adsorption
- surface area
- pore volume
- pore limiting diameter
- largest cavity diameter
- density
- water or humidity indicator
- experimental vs computational status

## Not In Scope Yet

- generating new MOFs;
- running DFT, GCMC, or molecular dynamics;
- claiming experimental validity from computational predictions;
- scraping restricted sites;
- automatically ingesting data without licence/provenance review;
- treating different force fields, charge methods, temperatures, pressures, or material classes as directly comparable.

## Installation

Use Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run The App

```bash
streamlit run app/streamlit_app.py
```

## Run Checks

```bash
python -m pytest
python scripts/check_sources.py
```

## Data Policy

Raw datasets are not committed by default. Every approved dataset should have source metadata, licence notes, retrieval date, and a clear statement of whether it is experimental, computational, predicted, or mixed.

The deterministic staging layer for CSV and structured text is documented in [`docs/ingestion.md`](docs/ingestion.md). Extraction results remain pending for human review; ingestion does not approve records or convert units.

## Current Status

Early product scaffold. The app supports upload-based screening logic first. Automated source monitoring is planned after the ranking and validation workflow is stable.
