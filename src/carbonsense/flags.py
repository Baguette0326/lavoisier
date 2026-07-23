"""Tradeoff and missing-data flags for screened materials."""

from __future__ import annotations

import pandas as pd


def _numeric(value: object) -> float | None:
    """Return a finite numeric value or None for messy uploaded data."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def build_tradeoff_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable warning flags without removing records."""
    result = frame.copy()
    flags: list[str] = []
    for _, row in result.iterrows():
        row_flags: list[str] = []
        uptake = _numeric(row.get("co2_uptake_mmol_g"))
        selectivity = _numeric(row.get("co2_n2_selectivity"))
        heat = _numeric(row.get("heat_of_adsorption_kj_mol"))
        humidity_value = row.get("humidity_condition", row.get("humidity_flag", ""))
        evidence_value = row.get("evidence_type", "")
        humidity = "" if pd.isna(humidity_value) else str(humidity_value).strip().lower()
        evidence = "" if pd.isna(evidence_value) else str(evidence_value).strip().lower()

        if uptake is not None and selectivity is not None and uptake > 4 and selectivity < 10:
            row_flags.append("high uptake but weak selectivity")
        if heat is not None and heat > 80:
            row_flags.append("high heat of adsorption may increase regeneration penalty")
        if not humidity:
            row_flags.append("humidity stability not reported")
        if evidence in {"computational", "computational_gcmc", "predicted", "dft", "simulation", "gcmc"}:
            row_flags.append("computational evidence requires experimental validation")
        flags.append("; ".join(row_flags))
    result["review_flags"] = flags
    return result
