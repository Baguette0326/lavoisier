"""CRAFTED dataset adapter skeleton.

This module defines the controlled MVP slice for CRAFTED 2.0.0 without
downloading or parsing the real archive. Real ingestion must wait for human
license/provenance approval and archive inspection.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


CRAFTED_REQUIRED_COLUMNS = {
    "material_id",
    "material_class",
    "evidence_type",
    "simulation_method",
    "force_field",
    "charge_method",
    "temperature_k",
    "pressure_bar",
    "co2_uptake_mmol_g",
    "n2_uptake_mmol_g",
}


@dataclass(frozen=True)
class CraftedSliceConfig:
    """Controlled CRAFTED subset configuration for the MVP."""

    material_class: str = "MOF"
    evidence_type: str = "computational_gcmc"
    simulation_method: str = "GCMC"
    temperature_k: float = 298.0
    force_field: str | None = None
    charge_method: str | None = None


def validate_crafted_like_table(frame: pd.DataFrame) -> list[str]:
    """Return schema warnings for a CRAFTED-like processed table."""
    columns = {str(column) for column in frame.columns}
    warnings: list[str] = []
    missing = sorted(CRAFTED_REQUIRED_COLUMNS - columns)
    if missing:
        warnings.append(f"Missing CRAFTED MVP column(s): {', '.join(missing)}")
    if "material_class" in columns:
        non_mof_count = int(frame["material_class"].dropna().astype(str).str.casefold().ne("mof").sum())
        if non_mof_count:
            warnings.append(f"{non_mof_count} non-MOF record(s) must be excluded from the MVP slice.")
    if "evidence_type" in columns:
        invalid_evidence = int(
            frame["evidence_type"].dropna().astype(str).str.casefold().ne("computational_gcmc").sum()
        )
        if invalid_evidence:
            warnings.append(f"{invalid_evidence} record(s) are not labelled computational_gcmc.")
    return warnings


def select_controlled_crafted_slice(
    frame: pd.DataFrame,
    config: CraftedSliceConfig,
) -> pd.DataFrame:
    """Select the conservative MOF/GCMC comparison slice from processed CRAFTED-like data."""
    result = frame.copy()
    for column, expected in (
        ("material_class", config.material_class),
        ("evidence_type", config.evidence_type),
        ("simulation_method", config.simulation_method),
    ):
        if column in result.columns:
            result = result[result[column].astype(str).str.casefold() == expected.casefold()]
    if "temperature_k" in result.columns:
        result = result[pd.to_numeric(result["temperature_k"], errors="coerce").eq(config.temperature_k)]
    if config.force_field and "force_field" in result.columns:
        result = result[result["force_field"].astype(str).str.casefold() == config.force_field.casefold()]
    if config.charge_method and "charge_method" in result.columns:
        result = result[result["charge_method"].astype(str).str.casefold() == config.charge_method.casefold()]
    return result.copy()
