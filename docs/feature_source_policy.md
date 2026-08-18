# Feature Source Policy

Status: current working policy for the Lavoisier MVP.

This page records which dataset should supply each feature type and why. The
rule is not "use the database with the most columns." The rule is:

```text
use the most direct, provenance-safe, high-coverage source for the feature role,
then keep extra sources only when repeated validation shows they help.
```

## Source Roles

| Source | Role in Lavoisier | Current use |
| --- | --- | --- |
| CRAFTED | Controlled GCMC adsorption performance and CRAFTED geometric descriptors | Primary ranking and ML reference slice |
| CoRE MOF 2014 | Crystal structure/provenance descriptors for matched MOFs | Joined enrichment layer |
| QMOF | Quantum/chemistry descriptors and identity fingerprints | Future enrichment layer, not active predictor input |
| NIST/experimental isotherm sources | Experimental adsorption evidence | Future validation source, not MVP predictor input |

## Feature-Level Policy

| Feature | Current source | Role | Rationale |
| --- | --- | --- | --- |
| `co2_uptake_mmol_g` | CRAFTED | Prediction target / ranking metric | Direct GCMC adsorption result under the controlled slice |
| `n2_uptake_mmol_g` | CRAFTED | Derived selectivity input | Direct GCMC adsorption result under the controlled slice |
| `co2_n2_selectivity` | CRAFTED | Prediction target / ranking metric | Derived from matched CRAFTED CO2/N2 uptake under the same slice |
| `heat_of_adsorption_kj_mol` | CRAFTED | Prediction target / ranking metric | Direct CRAFTED simulated adsorption-energy evidence |
| `surface_area_m2_g` | CRAFTED geometric | Predictor feature | Same CRAFTED workflow and high coverage |
| `pore_volume_cm3_g` | CRAFTED geometric | Predictor feature | Same CRAFTED workflow and high coverage |
| `density_g_cm3` | CRAFTED geometric | Predictor feature | Already aligned with the controlled CRAFTED slice |
| `pore_limiting_diameter_a` | CRAFTED geometric | Predictor feature | Directly relevant geometric descriptor with high coverage |
| `largest_cavity_diameter_a` | CRAFTED geometric | Predictor feature | Directly relevant geometric descriptor with high coverage |
| `void_fraction` | CRAFTED geometric | Predictor feature | Directly relevant geometric descriptor with high coverage |
| `core_formula_structural` | CoRE MOF 2014 | Provenance / future chemistry feature | Useful identity metadata, not yet treated as numeric predictor input |
| `core_formula_sum` | CoRE MOF 2014 | Provenance / future chemistry feature | Useful identity metadata, not yet treated as numeric predictor input |
| `core_cell_length_a/b/c` | CoRE MOF 2014 | Predictor feature for selected targets | Crystal metadata with strong join coverage |
| `core_cell_angle_alpha/beta/gamma` | CoRE MOF 2014 | Predictor feature for selected targets | Crystal metadata with strong join coverage |
| `core_cell_volume` | CoRE MOF 2014 | Predictor feature for selected targets | Repeated holdout suggests it can help some targets |
| `core_cell_formula_units_z` | CoRE MOF 2014 | Predictor feature for selected targets | Crystal metadata with strong join coverage |
| `core_int_tables_number` | CoRE MOF 2014 | Predictor feature for selected targets | Numeric space-group descriptor; use cautiously |
| `core_space_group_hm` | CoRE MOF 2014 | Provenance / future categorical feature | Not currently used because categorical encoding policy is not implemented |
| `info.mofid.mofid` | QMOF later | Identity / fingerprint | Useful later, but QMOF join coverage is smaller |
| `info.mofid.mofkey` | QMOF later | Identity / fingerprint | Useful later, but not active MVP predictor input |
| `outputs.pbe.bandgap` | QMOF later | Quantum descriptor | Potential future chemistry feature, requires separate validation |

## Current Target-Specific ML Policy

Repeated 80/20 holdout evaluation currently supports this policy:

| Prediction target | Feature-source policy | Reason |
| --- | --- | --- |
| `co2_uptake_mmol_g` | CRAFTED geometric + CoRE numeric descriptors + condition fields | CoRE stably improved MAE across repeated splits |
| `co2_n2_selectivity` | CRAFTED geometric + condition fields only | CoRE worsened repeated-holdout MAE |
| `heat_of_adsorption_kj_mol` | CRAFTED geometric + CoRE numeric descriptors + condition fields | CoRE stably improved MAE across repeated splits |

This is an empirical MVP policy, not a permanent scientific rule. If the
reference slice changes, rerun:

```bash
python scripts/evaluate_descriptor_feature_sets.py
```

## Why Not Decide From Tree Impurity Alone?

Decision-tree impurity and built-in random-forest feature importance can be
useful diagnostics, but they should not decide the source policy by themselves.

Reasons:

- impurity is specific to one model family;
- continuous and high-cardinality features can look artificially important;
- correlated descriptors can hide each other's importance;
- a feature can reduce impurity on the current dataset but fail on new MOFs;
- impurity does not measure licence, join confidence, or scientific provenance.

Use this priority order instead:

```text
1. scientific meaning
2. provenance and join confidence
3. coverage
4. repeated holdout or cross-validation performance
5. diagnostics such as permutation importance, impurity importance, or SHAP
```

Permutation importance is the preferred next diagnostic because it asks whether
scrambling a feature worsens held-out performance.
