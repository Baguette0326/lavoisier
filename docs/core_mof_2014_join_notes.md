# CoRE MOF 2014 Join Notes

Status: join-path researched and locally inspected.

## Source

CRAFTED states that its MOF structures were taken from CoRE MOF 2014. The local
CRAFTED README also states that the 690 MOF-related CIF files in
`CIF_FILES/DDEC` were downloaded from:

```text
Computation-Ready Experimental Metal-Organic Framework (CoRE MOF) 2014 DDEC Database
DOI: 10.5281/zenodo.3986573
License: CC BY 4.0
```

The CoRE-MOF package also lists CoRE MOF 2014 as dataset `2014`, points to
`10.5281/zenodo.3228673`, and states a CC BY 4.0 data license.

## Local Inspection

Command:

```bash
python scripts/inspect_core2014_join.py
```

The script compares exact identifiers from:

- CoRE MOF 2014 DDEC archive filenames;
- CRAFTED `CIF_FILES/DDEC/*.cif` filenames;
- CRAFTED `RAC_DBSCAN/CRAFTED_MOF_geometric.csv` `FrameworkName`;
- current `reports/crafted_real_slice_export/ranked_records.csv` `material_id`.

It strips the CoRE `_clean` suffix before matching and does not fuzzy-match.

## Result

```text
CoRE MOF 2014 DDEC IDs: 2932
CRAFTED DDEC CIF IDs: 1357
CRAFTED geometric FrameworkName IDs: 690
Ranked material IDs: 1352

CRAFTED DDEC CIF IDs -> CoRE 2014:
matched: 679 / 1357
match fraction: 0.5004

CRAFTED geometric FrameworkName -> CoRE 2014:
matched: 679 / 690
match fraction: 0.9841

Current ranked material IDs -> CoRE 2014:
matched: 675 / 1352
match fraction: 0.4993
```

Interpretation:

- CoRE MOF 2014 is a clean join target for the CRAFTED MOF subset.
- The CRAFTED geometric file is the best join anchor: `FrameworkName` matches
  CoRE 2014 IDs for about 98.4% of its MOF-style entries.
- The full CRAFTED DDEC CIF folder and current ranked records include many
  numeric-leading IDs, likely COF-derived records, which should not be joined
  to CoRE MOF by fuzzy matching.

## Join Policy

Use this conservative policy:

```text
join only by exact identifier match
normalize CoRE filenames by removing _clean
do not fuzzy-match numeric-leading CRAFTED IDs
mark missing CoRE matches explicitly
keep CoRE-derived descriptors separate from CRAFTED adsorption metrics
```

## Next Implementation Step

Build a CoRE MOF 2014 enrichment adapter that extracts safe metadata from the
matched CoRE CIFs, such as:

- CSD-style identifier;
- chemical formula if present;
- cell parameters;
- source file checksum;
- whether the CoRE file was `_clean`;
- CoRE source DOI/license attribution.

Do not add chemistry-derived features to the ML model until the adapter can
prove exact join coverage and provenance for each enriched record.
