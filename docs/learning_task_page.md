# Lavoisier Learning Task Page

This page defines what you need to understand well enough to explain Lavoisier to a chemical-engineering recruiter, professor, or research supervisor.

## Project Scope Decision

The first Lavoisier MVP will focus on:

- material class: MOFs only;
- application context: post-combustion-style CO2/N2 adsorption screening;
- first dataset target: CRAFTED 2.0.0, pending manual approval;
- evidence type: computational GCMC screening records;
- controlled comparison slice: one temperature, one force field, one charge method, and fixed pressure/metric basis.

We are not starting with direct air capture because DAC needs very low CO2 partial pressure and water/humidity behavior. That is important, but it makes the first MVP harder to defend. CO2/N2 post-combustion-style screening fits CRAFTED more naturally because the dataset includes CO2 and N2 adsorption data.

## What You Should Be Able To Explain

By the end of the learning track, you should be able to explain:

1. What MOFs are and why they are used in adsorption screening.
2. Why carbon capture is not just about high CO2 uptake.
3. Why CO2/N2 separation matters for post-combustion capture.
4. Why pressure, temperature, gas composition, and humidity affect comparability.
5. What GCMC simulation evidence means and why it is not the same as experiment.
6. Why Lavoisier is different from asking a generic LLM to summarize a paper.
7. Why a backend comparability engine is the core differentiator.

## Core Concepts To Learn

### 1. Carbon Capture Context

Know the difference between:

- post-combustion capture: separating CO2 from flue gas, often CO2/N2-rich mixtures;
- direct air capture: separating dilute CO2 from ambient air, where humidity is a major issue.

Key explanation:

> Lavoisier starts with post-combustion-style CO2/N2 screening because the first dataset target naturally supports CO2 and N2 adsorption comparisons under controlled simulation conditions.

### 2. Adsorption Basics

Learn:

- adsorption vs absorption;
- adsorbent vs adsorbate;
- isotherm;
- uptake capacity;
- selectivity;
- heat of adsorption;
- regeneration.

Key explanation:

> A useful adsorbent must capture enough CO2, prefer CO2 over other gases, release CO2 without excessive energy, and remain stable under relevant conditions.

### 3. MOFs

Learn:

- metal nodes;
- organic linkers;
- pore size;
- surface area;
- pore volume;
- tunability;
- why hypothetical and known MOF spaces are huge.

Key explanation:

> MOFs are attractive for screening because their structures can be varied in many ways, creating a large candidate space that cannot be tested one material at a time.

### 4. Screening Metrics

Know what each metric means:

- `co2_uptake`: how much CO2 a material adsorbs;
- `n2_uptake`: how much N2 adsorbs under comparable conditions;
- `co2_n2_selectivity`: preference for CO2 over N2;
- `heat_of_adsorption`: how strongly CO2 binds;
- `surface_area`: internal area available for adsorption;
- `pore_volume`: available pore volume;
- `density`: mass/volume property relevant to practical packing.

Key warning:

> Highest CO2 uptake is not automatically best. A material can have high uptake but poor selectivity or difficult regeneration.

### 5. Comparability

Understand why Lavoisier blocks weak comparisons.

Two records may not be comparable if they differ in:

- pressure;
- temperature;
- gas composition;
- force field;
- charge method;
- evidence type;
- humidity condition;
- material family.

Key explanation:

> Lavoisier can approve that a value was extracted correctly while still blocking it from ranked comparison if the measurement conditions are not comparable.

### 6. Computational Evidence

For the first dataset, understand:

- GCMC means Grand Canonical Monte Carlo simulation;
- simulation results depend on assumptions such as force field and charge method;
- computational results are useful for screening but are not experimental proof.

Key explanation:

> The first MVP uses computational records as screening evidence only. Lavoisier does not claim that the top-ranked material is experimentally validated.

### 7. Software Differentiator

Understand the difference between Lavoisier and a generic LLM.

A generic LLM gives:

```text
summary or answer
```

Lavoisier gives:

```text
structured record
source/provenance
validation warnings
comparability status
rank eligibility
exportable review table
```

Key explanation:

> Lavoisier turns AI-assisted reading into a controlled engineering review pipeline. The backend enforces domain rules before records can be ranked.

### 8. Polymorphs And Isomers In Carbon Capture

Learn the distinction:

- a **polymorph** is a different crystal structure of the same chemical material;
- an **isomer** has the same molecular formula but a different arrangement of atoms;
- a **structural or framework isomer** in a MOF can contain similar building blocks arranged into a different network or topology;
- a **linker positional isomer** has a functional group attached at a different position on the organic linker.

Why this matters for MOF screening:

- different crystal forms can have different pore sizes, accessible surface areas, adsorption sites, and framework flexibility;
- moving a functional group on a linker can change whether it points into the pore and how strongly it interacts with CO2;
- two records using the same material name or chemical formula may represent different structures and should not be merged automatically;
- polymorph or isomer identity can affect CO2 uptake, CO2/N2 selectivity, heat of adsorption, diffusion, water stability, and regeneration;
- activation, solvent removal, defects, or exposure to water can transform a framework into a different phase.

Isomerism also matters for liquid amine capture. Structural isomers of an amine can have different basicity, carbamate stability, CO2 solubility, absorption/desorption rates, cyclic capacity, and regeneration energy. Polymorphism is less central for liquid solvent systems because the working absorbent is not normally a crystalline solid.

Carbonate polymorphs such as calcite, aragonite, and vaterite matter in CO2 mineralization. This is related to permanent carbon storage or utilization, but it is outside the first Lavoisier post-combustion adsorption MVP.

Key explanation:

> Lavoisier must identify the specific material form, not just the material name. The same formula or MOF family can contain polymorphs, framework isomers, or linker isomers with meaningfully different adsorption performance.

Fields that may later be needed:

- `chemical_formula`;
- `polymorph_or_phase`;
- `framework_topology`;
- `linker_isomer`;
- `crystal_structure_id`;
- `activation_state`;
- `sample_source`.

Useful examples and further reading:

- [Structural isomerism and fluorination effects on CO2 adsorption in copper-tetrazolate MOFs](https://doi.org/10.1021/cm200593p);
- [Positional effects of methyl-substituted linker isomers on MOF structure and CO2/CH4 adsorption](https://doi.org/10.1039/C8DT01017J);
- [CO2 solubility and species distribution in structural isomers of aqueous alkanolamines](https://doi.org/10.1016/j.ijggc.2013.03.027);
- [Calcium carbonate crystallization and polymorphism in CO2 mineralization](https://doi.org/10.3389/fenrg.2017.00017).

## Learning Tasks

### Task 1: Build A Glossary

Create a glossary with short definitions for:

- MOF
- adsorbent
- adsorbate
- adsorption
- absorption
- isotherm
- uptake
- selectivity
- Henry coefficient
- heat of adsorption
- regeneration
- flue gas
- post-combustion capture
- direct air capture
- GCMC
- force field
- partial charge
- pore limiting diameter
- pore volume
- surface area

Deliverable:

- `docs/glossary.md`

### Task 2: Explain The Problem In One Page

Write one page answering:

- Why carbon-capture material screening matters.
- Why MOFs are a reasonable first material class.
- Why comparing reported adsorption values is hard.
- Why Lavoisier focuses on comparability before ranking.

Deliverable:

- `docs/problem_explanation.md`

### Task 3: Study The First Dataset Target

Read the Lavoisier source research report and summarize:

- what CRAFTED contains;
- why it is computational evidence;
- what conditions must be fixed before comparison;
- why COFs are excluded from the MVP;
- what licence/provenance checks are required before download.

Deliverable:

- `docs/crafted_dataset_notes.md`

### Task 4: Define A Comparable Record

Write a concrete example of two comparable records and two non-comparable records.

Include:

- material ID;
- material class;
- CO2 uptake;
- N2 uptake or selectivity;
- temperature;
- pressure;
- force field;
- charge method;
- evidence type;
- comparability decision;
- reason.

Deliverable:

- `docs/comparability_examples.md`

### Task 5: Recruiter Explanation

Prepare a 60-second explanation:

> I built Lavoisier to help structure and compare carbon-capture MOF screening records. The key challenge is that adsorption data is only meaningful under its operating and simulation conditions. Lavoisier extracts or ingests records, validates required context, blocks non-comparable records from ranking, and exports a reviewable table with provenance and warnings. It does not replace experiments or claim to discover a best material; it makes early-stage screening more transparent and reproducible.

Deliverable:

- `docs/recruiter_pitch.md`

## Suggested Study Order

1. Learn adsorption vocabulary.
2. Learn what MOFs are.
3. Learn post-combustion CO2/N2 separation.
4. Learn key screening metrics.
5. Learn why operating/simulation conditions matter.
6. Read the CRAFTED source notes.
7. Explain why Lavoisier is a backend comparability tool, not just an LLM wrapper.

## What Not To Overclaim

Do not say:

- Lavoisier discovers new MOFs.
- Lavoisier proves which material is best.
- Computational GCMC results are experimental validation.
- CO2 uptake alone determines usefulness.
- All carbon-capture adsorbents can be compared with one universal score.

Say instead:

> Lavoisier helps produce a transparent, source-linked, comparison-aware shortlist for human review.
