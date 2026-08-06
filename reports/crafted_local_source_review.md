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

