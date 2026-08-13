# External Validation Notes

Status: early sanity-check workflow, not a formal validation study.

## UiO-66-NH2 External Literature Case

Candidate file:

```text
data/validation_candidates/uio66_nh2_external_literature.json
```

Purpose:

```text
Feed Lavoisier a real MOF outside the local CRAFTED reference slice and check
whether the assessment remains scientifically cautious.
```

Reference-slice membership check:

```bash
rg -i "UiO|UiO-66|UiO66|UIO" reports/crafted_real_slice_export/ranked_records.csv
```

No matching `UiO`/`UiO-66` material name appears in the current local ranked
slice.

Source:

- Cao et al., *Materials* 2018, `UiO-66-NH2/GO Composite: Synthesis, Characterization and CO2 Adsorption Performance`.
- Open-access article: https://pmc.ncbi.nlm.nih.gov/articles/PMC5951473/

Values used:

- `co2_uptake_mmol_g = 2.59`: reported for UiO-66-NH2 at 298 K and 1 bar.
- `co2_n2_selectivity = 22.83`: reported CO2/N2 selectivity from initial-slope calculation at 298 K.
- `heat_of_adsorption_kj_mol = 24.2`: reported average CO2 isosteric heat.
- `surface_area_m2_g = 822`: reported BET surface area.
- `pore_volume_cm3_g = 0.236`: reported total pore volume.

Important mismatch:

The CRAFTED reference slice used by Lavoisier is computational GCMC data at:

```text
CO2 pressure = 0.2 bar
N2 pressure = 1.0 bar
T = 298 K
force field = UFF
charge method = DDEC
```

The UiO-66-NH2 validation candidate uses experimental literature values and
does not provide the full CRAFTED-style descriptor set. A sensible assessment
should therefore be cautious rather than treating the candidate as directly
rank-comparable.

Run:

```bash
python scripts/run_virtual_lab_demo.py \
  --candidate-dir data/validation_candidates \
  --output-dir reports/external_validation_uio66_nh2
```

Expected interpretation:

The exact final decision may change as the reference slice or model changes,
but a credible result should flag incomplete/mismatched evidence rather than
claiming that UiO-66-NH2 is proven better than the CRAFTED candidates.

## Current Run Result

Command:

```bash
python scripts/run_virtual_lab_demo.py \
  --candidate-dir data/validation_candidates \
  --output-dir reports/external_validation_uio66_nh2
```

Observed summary:

```text
final_decision = investigate_assumption_gap
viability_read = potential_but_unresolved
better_than_known_reference = unresolved_due_to_prediction_gap
review_confidence = low
```

Why this makes sense:

- UiO-66-NH2 does not appear by name in the current local CRAFTED ranked slice.
- The candidate's experimental CO2 uptake and CO2/N2 selectivity are better
  than the descriptor model expects from the partial descriptor set.
- The candidate only supplies 2 of the 6 supported structural descriptors.
- The candidate uses experimental literature values at 1 bar, while the
  reference slice uses CRAFTED GCMC data at the controlled 0.2 bar CO2 / 1.0
  bar N2 slice.
- The nearest-neighbor comparison is mixed, and the system recommends
  completing the descriptor set before trusting the assessment.

Interpretation:

This is a good sanity-check result. The tool recognizes that UiO-66-NH2 has
independently reported carbon-capture performance, but it does not overclaim
that the material is directly comparable to the CRAFTED GCMC slice or proven
better than known candidates.
