# Lavoisier Recruiter Talking Points

## 30-Second Summary

Lavoisier is a local software tool for reviewing carbon-capture MOF screening records. It takes a controlled CRAFTED CO2/N2 GCMC slice, validates and filters the records, ranks candidates with explicit engineering metrics, attaches provenance from CoRE MOF 2014 where possible, and uses baseline ML estimates to flag candidate records that deserve deeper review.

The main idea is not "AI discovers the best MOF." The main idea is making carbon-capture material screening more reproducible, traceable, and easier for an engineer to inspect.

## Why This Is Significant

Carbon-capture materials are often compared across papers, datasets, simulations, and conditions that are not directly equivalent. A high CO2 uptake number alone can be misleading if the pressure, temperature, force field, charge method, evidence type, or structural identity is different.

Lavoisier helps by forcing the comparison into a controlled slice, preserving source lineage, showing what was excluded or blocked, and separating computational screening from experimental validation.

## Chemical-Engineering Relevance

- Focuses on post-combustion-style CO2/N2 adsorption screening.
- Uses engineering metrics such as CO2 uptake, CO2/N2 selectivity, heat of adsorption, surface area, pore volume, and density.
- Treats comparability as an engineering constraint, not just a data-cleaning detail.
- Flags regeneration-related tradeoffs through heat of adsorption instead of ranking only by capacity.
- Keeps evidence type visible so GCMC results are not mistaken for lab validation.

## Software And Data Engineering Relevance

- Built a backend pipeline with schema validation, filtering, ranking, export logs, and reproducible reports.
- Kept raw dataset handling licence-aware instead of committing uncontrolled research data.
- Added transformation logs so outputs can answer where a result came from and what was filtered out.
- Built a Streamlit UI over generated outputs rather than hardcoding results into the interface.
- Added tests around parsing, comparability, ranking, ML triage, property prediction, and virtual-lab reports.

## Where ML Fits

The ML layer is descriptor-based decision support. It uses structural descriptors to estimate target adsorption properties and compare those estimates against supplied candidate claims.

The model is deliberately limited:

- it uses `RandomForestRegressor` baselines;
- it uses repeated held-out validation for feature-set decisions;
- it applies target-specific feature policies because CoRE enrichment helped some targets but not all;
- it does not use the target metric itself as an input feature;
- it reports uncertainty and warnings instead of making final viability claims.

## How This Differs From Asking A Generic LLM

A generic LLM can summarize a paper, but it will not automatically enforce controlled comparison rules, preserve transformation logs, separate excluded and blocked records, apply consistent ranking weights, or track source/licence/provenance fields in a reproducible export.

Lavoisier is narrower but more accountable: the rules, inputs, outputs, and limitations are inspectable.

## Biggest Limitation

The current MVP is mostly built around computational CRAFTED GCMC data and descriptor enrichment. It is useful for screening and triage, but not enough to prove real-world material performance. The next scientific step would be adding experimental validation sources such as NIST adsorption data and testing whether the ranking agrees with independent measurements.

## Strong Answer To "What Would You Improve Next?"

I would add an experimental validation layer, starting with carefully matched NIST adsorption records. The goal would be to compare whether candidates that look strong in the controlled GCMC slice also look plausible against independent experimental data. I would keep the same provenance-first design so the app shows where the computational and experimental evidence agree or disagree.

## Short Resume Bullet

Built Lavoisier, a Python/Streamlit carbon-capture MOF screening tool that parses controlled CRAFTED CO2/N2 GCMC records, ranks candidates with explicit engineering metrics, enriches provenance with CoRE MOF descriptors, and uses descriptor-based ML estimates for reviewable candidate triage.
