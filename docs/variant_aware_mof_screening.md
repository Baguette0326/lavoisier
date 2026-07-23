# Variant-Aware MOF Screening

Status: candidate post-provenance roadmap item.

This feature direction came from a scope discussion about polymorphism,
isomerism, and structural identity in MOF screening. It should not replace the
current immediate backend work: provenance logging, CRAFTED source approval, and
real CRAFTED ingestion.

## Why It Matters

A MOF name alone may not identify a unique, comparable material. Related records
can differ by crystal polymorph, topology, linker position, activation state,
or sample preparation. Lavoisier should eventually avoid treating those
records as one interchangeable material.

The feature belongs in the identity and comparability layer, not as another
arbitrary performance metric.

## Identity Hierarchy

Use this hierarchy when the backend becomes ready for variant-aware records:

```text
material family
  -> structural variant
  -> prepared sample / activation state
  -> performance measurement
```

The current MVP only models the performance-measurement layer and basic MOF
scope fields. Variant-aware work adds the upper identity layers.

## Variant Categories

Keep these distinctions explicit:

- crystal polymorph;
- framework or topological isomer;
- linker positional isomer;
- geometric isomer;
- conformational state, such as open versus closed;
- chemical analogue;
- sample, activation, or preparation-state difference.

Confirmed different variants must not be silently merged. Unknown variant
identity should produce a warning. Sample and activation differences should
remain separate from structural-variant differences.

## Proposed Fields

Candidate fields:

- `material_family_id`
- `structural_variant_id`
- `variant_type`
- `linker_id`
- `linker_isomer_label`
- `topology`
- `space_group`
- `structure_database_id`
- `structure_hash`
- `activation_state`
- `variant_assignment_confidence`

These should be added only when a concrete source or manually curated benchmark
can support them.

## Comparability Rules

Future comparability checks should:

- never merge confirmed different variants;
- warn when variant identity is unknown;
- keep activation and sample-preparation differences separate;
- block official comparisons when operating conditions or evidence types remain
  incompatible.

## Analysis Concepts

The current ranking score answers:

> Which record looks strongest within a controlled comparison slice?

Variant-aware analysis could add:

- **Family Differentiation Score:** how strongly related variants differ.
- **Factor Opportunity Score:** which structural factor looks worth studying.

A transparent opportunity score could use:

```text
O_factor =
  differentiation strength
  * evidence quality
  * attribution confidence
  * post-combustion relevance
```

An optional research-gap multiplier could highlight missing humidity, cycling,
experimental, or process data. Any such score must be labelled as a prioritising
signal, not a causal conclusion.

## Candidate Factors

Possible factors:

- topology;
- pore-limiting diameter;
- largest cavity diameter;
- surface area;
- density;
- open metal sites;
- interpenetration;
- flexibility;
- linker identity or position;
- metal identity;
- functional groups;
- hydrophobicity;
- activation state;
- water stability.

## Validation Approach

Do not jump to ML feature importance. Start with:

- a manually curated held-out benchmark of 3-5 MOF families and 10-30 records;
- published structural or linker-isomer pairs;
- NIST experimental isotherms and identity/alias checks;
- CRAFTED force-field sensitivity;
- published VSA/process rankings showing that simple adsorption metrics can
  fail.

Initial analysis should use matched comparisons, standardised effects,
bootstrap intervals, and leave-one-family/source-out checks. Associations must
not be labelled causal.

## Reference Leads To Verify

- Structural isomer example: DOI `10.1021/cm200593p`
- Ligand positional-isomer example: DOI `10.1039/C8DT01017J`
- Process-metric validation: DOI `10.1016/j.ijggc.2015.12.033`
- Force-field/process uncertainty: DOI `10.1039/D3EE00858D`
- NIST adsorption database: <https://adsorption.nist.gov/>

These are leads for future verification. Do not cite or use them as evidence in
the codebase until they are reviewed directly.

## Placement In Roadmap

Variant-aware screening should begin only after:

1. the current CRAFTED-like fixture pipeline is stable;
2. provenance and transformation logs exist;
3. a real CRAFTED slice has been inspected or approved;
4. material identity fields can be traced to a reliable source.

Until then, this is a roadmap concept, not MVP scope.
