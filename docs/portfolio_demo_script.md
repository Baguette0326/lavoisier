# Lavoisier Portfolio Demo Script

## One-Sentence Pitch

Lavoisier is a local decision-support prototype for carbon-capture MOF screening that keeps adsorption performance, structural provenance, ML estimates, and limitations visible in one review workflow.

## Why It Matters

Carbon-capture material rankings can be misleading when records come from different pressures, temperatures, force fields, evidence types, or structure sources. Lavoisier narrows the comparison to one controlled CRAFTED CO2/N2 GCMC slice, enriches records with CoRE MOF provenance when available, and produces a shortlist that a human can review instead of treating the highest adsorption number as automatically best.

## Demo Flow

1. Open **Ranked MOF Screening**.
   Show that the app ranks a controlled slice, not all MOFs in the world. Point out the score, CO2 uptake, CO2/N2 selectivity, heat of adsorption, CoRE match status, and the selected-material score breakdown.

2. Open **Candidate Virtual Lab**.
   Show how a new synthetic candidate is checked against descriptor-based ML estimates. Explain that the model flags gaps between supplied claims and expected properties, but does not prove experimental viability.

3. Open **Provenance / Limitations**.
   Show the transformation receipt, controlled slice settings, feature-source policy, and known limitations. This is the main difference between the project and simply pasting a paper into a generic LLM.

## What To Say If Asked About AI

The AI/ML part is used as reviewable decision support. It estimates target properties from descriptors, applies target-specific feature policies, and flags uncertainty. The ranking and evidence rules are still explicit, auditable, and constrained by the selected data slice.

For shorter interview-ready answers, see [`recruiter_talking_points.md`](recruiter_talking_points.md).

## What Not To Claim

- Do not claim Lavoisier discovered a new best MOF.
- Do not claim CRAFTED GCMC data is experimental lab validation.
- Do not claim the model can generalize to every carbon-capture material.
- Do not claim unsupported automated literature ingestion is complete.
