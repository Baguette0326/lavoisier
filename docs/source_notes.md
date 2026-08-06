# Source Notes

These are leads only. Do not download or ingest any dataset until licence, access method, and redistribution status are reviewed.

## OpenDAC

OpenDAC 2023 is a major public source lead for direct-air-capture sorbent discovery. The associated paper describes more than 38 million DFT calculations across more than 8,400 MOF materials for CO2 and/or H2O adsorption.

OpenDAC 2025 is a later source lead that expands the scope with nearly 70 million DFT single-point calculations across 15,000 MOFs for CO2, H2O, N2, and O2 adsorption.

Use case for Lavoisier:

- source-monitoring target;
- possible approved dataset after access/licence review;
- benchmark for computational evidence, not experimental proof.

## NIST / ISODB-Style Adsorption Data

Adsorption-isotherm databases may provide experimental or literature-derived adsorption measurements. They are useful but require careful metadata handling because pressure, temperature, gas mixture, and material naming conventions differ.

Use case for Lavoisier:

- experimental/literature evidence source if licensing permits;
- source of pressure-temperature-specific adsorption data.

## CoRE MOF And MOF Structure Datasets

MOF structure datasets can provide structural descriptors such as pore size, surface area, density, and topology. They may need to be linked to adsorption datasets before screening.

Use case for Lavoisier:

- material descriptor source;
- not sufficient by itself unless adsorption target data is available.

## CRAFTED 2.0.1

CRAFTED is the first real-data target for the MVP because it is directly aligned
with computational CO2/N2 adsorption screening. The project now targets the
official `2.0.1` Zenodo record because `2.0.0` has a newer bugfix release that
replaces MOF uptake and enthalpy values at 2 and 5 bar.

Local-only download is approved after source review. Raw CRAFTED files must stay
out of Git. Processed slices and derived review exports require separate review
before public GitHub sharing.

Use case for Lavoisier:

- first approved computational GCMC source target;
- controlled MOF-only post-combustion-style CO2/N2 slice;
- provenance test for archive checksum, source file lineage, and processed
  review exports.

## Key Risk

Computational, predicted, and experimental records must remain visibly separate in the software. A material ranked highly in a computational dataset is a review candidate, not a validated capture material.
