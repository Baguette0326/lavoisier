# QMOF Join Notes

Status: source inspected and local join-path check implemented.

## Source

QMOF is a public database of DFT-computed properties for MOFs and related
coordination polymers. The local inspection used the official Figshare record:

```text
QMOF Database
DOI: 10.6084/m9.figshare.13147324.v18
License: CC BY 4.0
Modified: 2026-07-02
```

The downloaded archive contains:

- `qmof.csv`;
- `qmof.json`;
- `qmof_structure_data.json`;
- relaxed and unrelaxed structure archives.

Only `qmof.csv` and `README.md` were extracted for the join inspection.

## Useful Fields

The QMOF table includes fields that could eventually enrich Lavoisier's
candidate records:

- QMOF ID;
- source name;
- MOFid and MOFkey;
- topology;
- pore-limiting diameter;
- largest cavity diameter;
- density;
- volume;
- synthesized/source flag;
- source DOI;
- PBE-D3(BJ) DFT outputs such as band gap.

These are descriptors and provenance fields. They are not CO2/N2 adsorption
measurements, so they must remain separate from CRAFTED ranking metrics.

## Local Inspection

Command:

```bash
python scripts/inspect_qmof_join.py
```

The script compares:

- QMOF raw `name`;
- QMOF normalized `name`, with only a terminal `_FSR` stripped;
- CRAFTED `RAC_DBSCAN/CRAFTED_MOF_geometric.csv` `FrameworkName`;
- current `reports/crafted_real_slice_export/ranked_records.csv` `material_id`.

It exports:

- `join_summary.json`;
- `join_summary.md`;
- `matched_qmof_descriptors.csv`.

## Result

```text
QMOF rows: 20372
QMOF unique names: 20372
QMOF _FSR names: 16040
CRAFTED geometric FrameworkName IDs: 690
Ranked material IDs: 1352

QMOF raw name -> CRAFTED geometric FrameworkName:
matched: 0 / 20372
match fraction: 0.0

QMOF normalized name -> CRAFTED geometric FrameworkName:
matched: 217 / 20372
match fraction: 0.0107

QMOF normalized name -> current ranked material IDs:
matched: 215 / 20372
match fraction: 0.0106
```

Interpretation:

- QMOF is joinable, but not as clean as CoRE MOF 2014 for the immediate
  descriptor-enrichment step.
- Raw QMOF names do not match CRAFTED names because many CSD-source entries use
  a suffix such as `_FSR`.
- Controlled `_FSR` stripping recovers 217 matches against the CRAFTED MOF
  geometry file.
- More aggressive suffix stripping should not be used without a stronger
  identity check, such as MOFid/MOFkey or structure hash comparison.

## Join Policy

Use this conservative policy:

```text
join QMOF to CRAFTED only by CSD-style name after controlled _FSR stripping
do not fuzzy-match QMOF names
do not join by QMOF ID
keep QMOF DFT/geometric descriptors separate from CRAFTED adsorption metrics
mark missing QMOF descriptors explicitly
prefer CoRE 2014 for the first descriptor integration
use QMOF as a later enrichment layer once the CoRE adapter is stable
```
