# Public Data and Literature Source Research

Research date: 2026-07-15

## Recommendation

Use **CRAFTED 2.0.0 as the first dataset to evaluate for manual approval**, and
keep **NIST/ARPA-E ISODB as the first experimental-data follow-on**.

CRAFTED is the strongest fit for the first Lavoisier demonstration because it
is a manageable 54.7 MB compressed archive, has explicit file-level licensing,
and contains simulated CO2 and N2 adsorption isotherms and adsorption enthalpies
for 690 MOFs at 273 K, 298 K, and 323 K. It is therefore closer to the current
screening contract than structure-only datasets, while remaining small enough
to audit locally. Its main limitation is equally important: these are GCMC
simulation results, not experimental measurements, and results vary with force
field and partial-charge method.

Do not download it automatically. The next gate should be a human review of the
license and archive layout, followed by a checksum-verified download and a small,
reproducible extraction from one consistent simulation protocol. The first slice
should use MOFs only, 298 K, one force field, one charge method, and common
pressure points. Lavoisier should not label that slice as direct-air-capture or
post-combustion evidence until its pressure range and gas basis have been checked.

Primary references:

- [CRAFTED 2.0.0 dataset record and files](https://doi.org/10.5281/zenodo.8190237)
- [CRAFTED paper](https://doi.org/10.1038/s41597-023-02116-z)
- [CDLA-Sharing-1.0 license](https://cdla.dev/sharing-1-0/)

## Source comparison

| Source | Evidence and data | Access and size | License status | Lavoisier fit | Decision |
|---|---|---|---|---|---|
| CRAFTED 2.0.0 | GCMC CO2/N2 isotherms and adsorption enthalpies; MOF/COF CIFs; simulation inputs; 273/298/323 K | Open Zenodo archive; 54.7 MB compressed | Generated files: CDLA-Sharing-1.0. MOF CIF lineage: CC BY 4.0. Some COF and RASPA files: MIT. | Directly supplies uptake curves, CO2/N2 comparisons, temperature, and enthalpy, with explicit computational provenance | **Evaluate first for approval** |
| NIST/ARPA-E ISODB | Experimental and literature-derived single- and multicomponent isotherms, conditions, material IDs, source DOIs | Public web UI and JSON/XML/CSV APIs; query small subsets | Public access is clear, but an explicit blanket data-redistribution license was not found on the reviewed landing pages or repository | Best route to experimental evidence; excellent provenance, but heterogeneous conditions and rights need record-level care | Follow-on; API pilot only after rights review |
| MOFX-DB | More than 3 million simulated adsorption points for CO2, N2 and other gases; textural properties and structures for over 160,000 MOFs/zeolites | Public web/API and bulk download; potentially large | Public availability is stated; no explicit blanket dataset license was found on the reviewed NIST/public interface | Very strong screening fields and NIST-compatible JSON; scale and licensing need a narrow pilot | High-priority follow-on |
| OpenDAC 2023 | More than 38 million DFT calculations on more than 8,400 MOFs with adsorbed CO2 and/or H2O | Public download links; large LMDB/trajectory-style data | Archived helper repository is MIT; the full dataset's license was not made explicit on the current landing page reviewed | Directly DAC-relevant and humidity-aware, but atomic trajectories/energies require substantial transformation and are not experimental uptake curves | Benchmark/research lead, not first ingestion |
| OpenDAC 2025 | Nearly 70 million DFT single-point calculations for CO2, H2O, N2 and O2 in 15,000 MOFs | Gated Hugging Face access requiring identity/organization details; large | Dataset: CC BY 4.0. Model checkpoints use the separate FAIR Chemistry License. Geographic access restrictions are stated | Richest OpenDAC chemistry and gases, but access friction, scale, and atomistic format make it unsuitable for the MVP fixture | Defer |
| CoRE MOF 2024 SI | 8,300 experimental-source structures; 2,664 computation-ready; pore descriptors, density, topology, stability predictions, water data, and TSA files | Open Zenodo record; 335.5 MB total; individual CSVs from 55.5 KB to 1.1 MB | Zenodo record: CC BY 4.0. CSD-derived branches have separate access conditions; unmodified CSD files require a CCDC license | Excellent descriptor and stability enrichment; insufficient alone for CO2 screening, except limited TSA/adsorption supplements | Use later as an enrichment source |
| QMOF | DFT quantum-chemical properties for more than 20,000 MOFs/coordination polymers; structures and electronic properties | Figshare/GitHub; about 385.55 MB for the cited Figshare version | Data: CC BY 4.0; repository code: MIT | Useful structural/electronic enrichment and entity matching; does not provide a uniform experimental CO2/N2 isotherm table | Defer as enrichment |

## Detailed source notes

### 1. CRAFTED 2.0.0

The [Zenodo record](https://doi.org/10.5281/zenodo.8190237) describes 97,704
CO2/N2 isotherm files and the same number of adsorption-enthalpy files. The
simulations cover 690 CoRE-MOF-2014 structures and 667 CURATED-COF structures,
two force fields, six charge schemes, and three temperatures. It explicitly
assigns CDLA-Sharing-1.0 to generated files and identifies the inherited licenses
of structure and force-field inputs.

Likely useful fields:

- material identifier and material family;
- adsorbate, temperature, pressure, and uptake;
- adsorption enthalpy;
- force field and partial-charge method;
- structural/geometrical descriptors;
- simulation input provenance.

Risks and controls:

- Treat every record as `computational_gcmc`, never experimental.
- Keep force field and charge method as comparability keys; do not average them.
- Confirm pressure and uptake units from the archive documentation before mapping.
- Preserve the supplied filenames and source lineage so results remain auditable.
- Attribute both CRAFTED and inherited CoRE MOF structure sources when required.

### 2. NIST/ARPA-E Database of Novel and Emerging Adsorbent Materials

NIST describes ISODB as a centralized collection of single- and multicomponent
isotherms from interlaboratory studies, research-group contributions, and
peer-reviewed articles. Records are organized by adsorbent, adsorbate,
thermodynamic conditions, and measurement type; extracted literature records
remain linked to source DOIs. The public APIs return JSON, XML, and CSV.

Authoritative links:

- [NIST adsorption-data project description and API links](https://www.nist.gov/programs-projects/nist-data-resources-adsorption)
- [NIST adsorption portal](https://adsorption.nist.gov/)
- [Official ISODB GitHub mirror](https://github.com/NIST-ISODB/isodb-library)

Risks and controls:

- Public API access does not by itself establish a blanket redistribution license.
- Some curves are digitized from publisher figures; retain DOI and extraction
  provenance and confirm reuse rights before shipping records in the repository.
- Material aliases, basis units, pressure conventions, activation history, and
  wet/dry conditions can prevent valid comparisons.
- Start with a few CO2 and N2 API records for schema evaluation only; do not bulk
  mirror the database.

### 3. MOFX-DB

[NIST's publication page](https://www.nist.gov/publications/mofx-db-online-database-computational-adsorption-data-nanoporous-materials)
describes more than 3 million simulated adsorption points for seven gases in more
than 160,000 MOFs and zeolites, including pore/textural properties, structures,
and simulation metadata. Its JSON is interoperable with NIST ISODB. The
[public interface](https://mof.tech.northwestern.edu/) exposes search and download
features.

This is arguably the closest large-scale match to Lavoisier's desired columns,
but it should not be the first ingestion: the source is large, combines several
underlying studies/databases, and the reviewed interfaces did not show a single
explicit license covering every downloadable record. A later pilot should query
one named database and one fixed CO2/N2 condition set.

### 4. OpenDAC 2023 and 2025

The [OpenDAC site](https://open-dac.github.io/) reports nearly 40 million DFT
calculations from 170,000 relaxations for ODAC23. The peer-reviewed
[ODAC23 paper](https://doi.org/10.1021/acscentsci.3c01629) describes more than 38
million calculations across more than 8,400 MOFs with CO2 and/or H2O. The
[archived ODAC data helper repository](https://github.com/Open-Catalyst-Project/odac-data)
is MIT-licensed and contains promising-MOF analysis assets, but that code/archive
license should not be assumed to cover every full dataset file without checking
the current download documentation.

The [ODAC25 paper](https://arxiv.org/abs/2508.03162) reports nearly 70 million DFT
single-point calculations across 15,000 MOFs and adds N2 and O2. Its
[Hugging Face access page](https://huggingface.co/facebook/ODAC25) explicitly
licenses the dataset under CC BY 4.0, while model checkpoints use a different FAIR
Chemistry License. Access requires accepting conditions and supplying identity and
organization details; the page also states geographic restrictions.

Risks and controls:

- DFT adsorption energies/forces are not adsorption capacities or selectivities.
- Atomistic LMDB/trajectory data is too large and technically indirect for the
  first dashboard fixture.
- CO2, H2O, N2, and O2 coverage is useful for future humidity/competition work,
  but derived screening metrics must document the scientific method used.

### 5. CoRE MOF 2024

The [CoRE MOF 2024 Zenodo record](https://doi.org/10.5281/zenodo.15055758) is CC
BY 4.0 and clearly separates its public supporting-information set from CSD-based
branches. It provides pore sizes, surface area, pore volume, density, topology,
partial charges, heat capacity, decomposition temperature, solvent-removal and
water-stability predictions, and hydrophobic classification. The record also
contains a small recommended-screening CSV and separate water/TSA archives.

The SI CSVs are attractive for a small descriptor fixture, but they do not by
themselves demonstrate carbon-capture ranking. CSD-modified files require login,
and unmodified CSD files require a CCDC license. Lavoisier should never copy a
license from the Zenodo SI set onto the separate CSD branches.

### 6. QMOF

The [QMOF repository](https://github.com/Andrew-S-Rosen/QMOF) and
[Figshare dataset](https://doi.org/10.6084/m9.figshare.13147324) describe a public
database of DFT-derived quantum-chemical properties for more than 20,000 MOFs and
coordination polymers. The data is CC BY 4.0 and the code repository is MIT.

QMOF is credible and reusable, but its primary value here is descriptor enrichment,
material matching, and future model features. It is not a substitute for a
condition-specific adsorption-isotherm dataset.

## Literature discovery and extraction workflow

Use bibliographic services to find and track papers, not to assume rights to their
full text:

1. Start from source DOIs in ISODB or dataset papers.
2. Resolve bibliographic metadata through the
   [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).
   Crossref says almost all metadata may be used for any purpose, but publisher
   abstracts can still be copyrighted.
3. Use [OpenAlex](https://developers.openalex.org/) for related-work discovery and
   citation graph metadata; its data is CC0.
4. Retrieve full text only from an identified open-access copy whose license
   permits the intended extraction. Store the article DOI, URL, version, license,
   access date, page/table/figure locator, extraction method, and reviewer.
5. Never treat a publicly reachable PDF as automatically licensed for repository
   redistribution. Store derived facts with short quotations only when necessary,
   and keep the source locator.

## Approval checklist for any first ingestion

- Pin the exact dataset version, DOI, retrieval date, and checksum.
- Save the exact license text or canonical license URL used for approval.
- List inherited data sources and their licenses separately.
- Inspect archive filenames and schemas before writing transformations.
- Define evidence type and comparability keys before ranking.
- Preserve original units and add conversions only through reviewed code.
- Keep raw data uncommitted unless redistribution is explicitly approved.
- Create a small processed fixture with attribution and a transformation log.
- Require human sign-off before moving any file into `data/approved`.

## Proposed next action

After human approval, download only the 54.7 MB CRAFTED 2.0.0 archive from its
Zenodo record, verify MD5 `28889d4b7baa19838bee774aaaf748a0`, inspect its
documentation, and produce a no-more-than-50-record comparison fixture. Until
that approval occurs, this report and the source registry are research leads only.
