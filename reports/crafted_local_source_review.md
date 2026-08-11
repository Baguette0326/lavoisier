# CRAFTED Local Source Review

This report records the local-only CRAFTED approval and inspection result used
to choose the first parser target. It does not commit raw CRAFTED data.

## Source

- Dataset: CRAFTED 2.0.1 adsorption isotherm dataset
- DOI: `10.5281/zenodo.10120180`
- Archive: `CRAFTED-2.0.1.tar.xz`
- Expected MD5 from Zenodo: `e11e4f84cdd484db7811bc758faaed37`
- Local MD5 verified: `E11E4F84CDD484DB7811BC758FAAED37`
- Local raw path: `data/raw/crafted_2_0_1/`
- Git policy: raw data and archive-inspection exports remain ignored

## License Review

- Generated CRAFTED files: `CDLA-Sharing-1.0`
- MOF-related inherited CIF lineage: `CC-BY-4.0` from CoRE-MOF-2014
- COF-related inherited CIF lineage: `MIT` from CURATED-COFs
- RASPA-derived gas definition files: `MIT`

Raw data should not be pushed to GitHub. Any processed public slice requires
separate review before committing.

## Local Inspection Result

The extracted archive contains:

- `ISOTHERM_FILES/`
- `ENTHALPY_FILES/`
- `CIF_FILES/`
- `FORCEFIELDS/`
- `INPUT_FILES/`
- `RAC_DBSCAN/`

The optimized local inspection parsed:

- 97,704 isotherm files
- 97,704 enthalpy files
- 1,357 unique material identifiers in parsed result files

At `298 K / UFF / DDEC`, exact pressure points are available for both CO2 and N2
at:

```text
0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0 bar
```

The preferred post-combustion target was:

```text
CO2 = 0.15 bar
N2 = 0.85 bar
T = 298 K
```

Those exact pressure points are not present. Following the no-interpolation rule,
the first parser target should use the closest available exact pair:

```text
CO2 = 0.2 bar
N2 = 1.0 bar
T = 298 K
force field = UFF
charge method = DDEC
```

## Parser Target

The first real parser should produce:

- long isotherm table for the selected files and pressure points
- derived screening table with one row per material
- blocked records for missing or unmatched pairs
- transformation log recording intended pressures, actual pressures, checksum,
  and the no-interpolation limitation

## First Local Parser Run

The first local parser run used:

```text
python scripts/run_crafted_real_slice.py
```

Outputs were written to ignored local folders:

- `data/processed/crafted_2_0_1/`
- `reports/crafted_real_slice_export/`

Run result:

- long records: 2,714
- screening records: 1,352
- parser-blocked records: 5
- ranked records: 1,352
- backend-blocked records: 0

The 5 parser-blocked records had non-positive uptake values that would make
CO2/N2 selectivity undefined or infinite. They were excluded from the official
ranked table under `block_type = invalid_selectivity_denominator`.

## First Local ML Triage Run

The first local weakly supervised ML triage run used:

```text
python scripts/run_ml_triage.py
```

Outputs were written to the ignored local folder:

- `reports/crafted_ml_triage/`

Run result:

- classified records: 1,352
- model: `RandomForestClassifier`
- label source: weak supervision from transparent engineering rules
- holdout accuracy against rule-derived labels: 0.9970

Rule-derived class counts:

- `promising_candidate`: 19
- `balanced_candidate`: 218
- `rank_ready`: 338
- `poor_selectivity`: 553
- `low_capacity`: 224

This classifier is a review aid only. It learns the rule-derived triage labels;
it does not prove experimental success and does not override measured ranking,
comparability checks, or human review.
