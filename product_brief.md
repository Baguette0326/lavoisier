# Lavoisier Product Brief

## One-Line Pitch

Lavoisier is a human-in-the-loop backend and demo dashboard for screening MOF carbon-capture adsorption records using transparent comparability checks, provenance, and tradeoff explanations.

## User

Primary user:

- undergraduate chemical-engineering student;
- research assistant;
- materials-discovery learner;
- early-stage researcher comparing public MOF adsorption datasets.

The user is not assumed to be a computational chemistry expert.

## Problem

MOF carbon-capture screening datasets are hard to use directly. A material can look promising on one metric, such as CO2 uptake, while being weak on another, such as selectivity, regeneration implications, simulation assumptions, or data completeness.

The unresolved software problem is not producing another black-box model. It is helping a human reviewer make a defensible shortlist.

## Product Promise

Lavoisier helps answer:

- Which candidates look promising under my constraints?
- Why are they ranked highly?
- What tradeoffs or missing data make them risky?
- Is the record inside the controlled MOF/GCMC comparison slice?
- What changed when a new source or dataset was added?

## MVP Features

1. CSV upload
2. Schema validation
3. Column mapping
4. Adjustable weighted ranking
5. Tradeoff flags
6. Explainability summary
7. Exportable shortlist
8. Source registry
9. New-source check report

## Human Review Gates

Human approval is required before:

- adding a dataset to `data/approved`;
- merging datasets;
- converting units with ambiguous definitions;
- treating aliases as the same material;
- using computational predictions as experimental evidence;
- updating the official leaderboard.

## Success Criteria

By the end of summer:

- the app runs locally;
- one public dataset source is documented and manually approved;
- the app can rank at least one approved dataset;
- generated shortlists include provenance and warning flags;
- the README makes limits clear;
- no restricted data or credentials are committed.
