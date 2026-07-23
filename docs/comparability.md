# Comparability Engine

CarbonSense treats extraction, approval, comparability, and ranking as separate steps.

A record can be extracted correctly and still be blocked from ranked comparison if the operating conditions are not comparable.

## MVP Rule Set

The backend comparability engine is intentionally conservative. By default, rank eligibility requires:

- material class is MOF;
- same capture context;
- same evidence type, currently computational GCMC;
- same simulation method;
- same force field;
- same charge method;
- numeric temperature within 5 K of the comparison scope baseline;
- numeric pressure within 0.05 bar of the comparison scope baseline;
- optional humidity condition matching the comparison scope baseline when that rule is enabled.

The first non-missing record in the active review scope is used as the baseline. This is simple and testable for the MVP. Later versions should support explicit user-selected baselines or named comparison groups.

## Statuses

- `comparable`: record may enter ranked comparison.
- `needs_review`: key context is missing or not reported.
- `not_comparable`: context differs beyond the conservative rule set.
- `partially_comparable`: reserved for later use.

## Why This Exists

A generic LLM can summarize a paper but may still compare values measured under different pressure, temperature, gas-mixture, force-field, charge-method, material-family, humidity, or evidence conditions.

CarbonSense makes those assumptions explicit in backend code. The result is an exportable table with:

- `comparability_status`
- `comparability_reasons`
- `rank_eligible`

This keeps ranking secondary to engineering review quality.
