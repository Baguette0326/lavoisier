# CRAFTED Approval Checklist

Lavoisier must not ingest real CRAFTED data until this checklist is completed.
The goal is to preserve source lineage and avoid making claims from data we are
not approved to use or redistribute.

## Dataset Target

- Source: CRAFTED 2.0.1 adsorption isotherm dataset
- Platform: Zenodo
- DOI: `10.5281/zenodo.10120180`
- Registry key: `crafted_2_0_1`
- Archive: `CRAFTED-2.0.1.tar.xz`
- Expected MD5: `e11e4f84cdd484db7811bc758faaed37`
- Current Lavoisier status: `approved_for_local_download_not_for_git_commit`

## Approval Gate

Completed for local-only download:

- Generated CRAFTED files: `CDLA-Sharing-1.0`.
- MOF-related inherited CIF lineage: `CC-BY-4.0` from CoRE-MOF-2014.
- COF-related inherited CIF lineage: `MIT` from CURATED-COFs.
- RASPA-derived gas definition files: `MIT`.
- Raw data must not be committed to Git.
- Processed slices and derived review exports require separate review before
  public GitHub sharing.
- Archive URL, version, download date, and checksum must be recorded after
  download.
- Keep raw files untouched under `data/raw/crafted_2_0_1/`.

## Archive Inspection Questions

Answer these after approval and download:

- Which files contain CO2 isotherms?
- Which files contain N2 isotherms?
- Which files contain enthalpy or heat-of-adsorption values?
- Which files identify force field?
- Which files identify charge method?
- Which files identify temperature and pressure grid?
- Which material identifiers link adsorption values to MOF structures?
- Are material names, structure IDs, and aliases stable enough for matching?

Run the local inspection helper before parser work:

```bash
python scripts/inspect_crafted_archive.py path/to/crafted/archive-or-folder
```

Review `reports/crafted_archive_inspection/pressure_availability.csv` before
choosing the first exact-match pressure pair.

## First Real Slice Decision

Choose one conservative slice before writing the real parser:

- Material class: MOF
- Evidence type: computational GCMC
- Capture context: post-combustion CO2/N2 screening
- Temperature: one value only
- Force field: one value only
- Charge method: one value only
- Pressure or partial-pressure basis: one basis only

Do not compare records outside this slice in the ranked table. Export them as
excluded records with reasons.

## Required Provenance For The First Processed Slice

The processed slice must include or link to:

- Source archive version
- Source archive checksum
- Raw source filename
- Raw source row or record identifier
- Material identifier
- Measurement or simulation conditions
- Unit conversions performed
- Exclusion reason when out of scope
- Limitations

## Stop Conditions

Stop and ask for review if:

- License status is unclear.
- Raw and generated data have different licenses.
- Attribution requirements are unclear.
- Source files do not expose force field, charge method, temperature, or pressure.
- CO2 and N2 records cannot be matched to the same material and conditions.
- The selected slice has too few comparable records to rank honestly.
