# CRAFTED Approval Checklist

Lavoisier must not ingest real CRAFTED data until this checklist is completed.
The goal is to preserve source lineage and avoid making claims from data we are
not approved to use or redistribute.

## Dataset Target

- Source: CRAFTED 2.0.0 adsorption isotherm dataset
- Platform: Zenodo
- DOI: `10.5281/zenodo.8190237`
- Registry key: `crafted_2_0_0`
- Current Lavoisier status: `recommended_for_manual_approval_review`

## Approval Gate

Complete these before downloading or parsing the real archive:

- Confirm exact license for generated CRAFTED files.
- Confirm exact license for inherited MOF structure files.
- Confirm required attribution text.
- Confirm whether raw data can be committed to Git.
- Confirm whether processed slices can be committed to Git.
- Confirm whether derived review exports can be shared publicly.
- Record the archive URL, version, download date, and checksum.
- Keep raw files untouched under `data/raw/crafted_2_0_0/` only if approved.

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

