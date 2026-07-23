"""Schema validation for MOF carbon-capture screening records."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


REQUIRED_COLUMNS = {"material_id", "material_class", "evidence_type"}

RECOMMENDED_COLUMNS = [
    "source",
    "capture_context",
    "simulation_method",
    "force_field",
    "charge_method",
    "temperature_k",
    "pressure_bar",
    "adsorbate",
    "co2_uptake_mmol_g",
    "n2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
    "humidity_flag",
]

NUMERIC_COLUMNS = [
    "temperature_k",
    "pressure_bar",
    "co2_uptake_mmol_g",
    "n2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
]


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating an uploaded or approved dataset."""

    is_valid: bool
    missing_required: list[str]
    available_recommended: list[str]
    warnings: list[str]


def validate_material_table(frame: pd.DataFrame) -> ValidationResult:
    """Validate the minimum schema needed for screening."""
    columns = {str(column) for column in frame.columns}
    missing_required = sorted(REQUIRED_COLUMNS - columns)
    available_recommended = [column for column in RECOMMENDED_COLUMNS if column in columns]
    warnings: list[str] = []
    if frame.empty:
        warnings.append("The dataset has no records.")
    if "material_id" in columns:
        missing_ids = int(frame["material_id"].isna().sum())
        duplicate_ids = int(frame["material_id"].dropna().duplicated().sum())
        if missing_ids:
            warnings.append(f"{missing_ids} record(s) have no material identifier.")
        if duplicate_ids:
            warnings.append(f"{duplicate_ids} duplicate material identifier(s) detected; review aliases before merging.")
    if "evidence_type" in columns:
        evidence_values = set(frame["evidence_type"].dropna().astype(str).str.lower())
        if len(evidence_values) > 1:
            warnings.append("Mixed evidence types detected; keep computational and experimental records separate.")
    if "material_class" in columns:
        non_mof_count = int(frame["material_class"].dropna().astype(str).str.casefold().ne("mof").sum())
        if non_mof_count:
            warnings.append(f"{non_mof_count} non-MOF record(s) detected; exclude them from the MVP comparison.")
    if "simulation_method" in columns:
        non_gcmc_count = int(frame["simulation_method"].dropna().astype(str).str.casefold().ne("gcmc").sum())
        if non_gcmc_count:
            warnings.append(f"{non_gcmc_count} non-GCMC record(s) detected; review before comparison.")
    scoring_columns = [column for column in NUMERIC_COLUMNS if column in columns]
    if not scoring_columns:
        warnings.append("No supported numeric screening columns found; all ranking scores will be zero.")
    for column in scoring_columns:
        invalid_count = int((pd.to_numeric(frame[column], errors="coerce").isna() & frame[column].notna()).sum())
        if invalid_count:
            warnings.append(f"{invalid_count} non-numeric value(s) in `{column}` will score as missing.")
    for context_column in ("temperature_k", "pressure_bar", "force_field", "charge_method"):
        if context_column not in columns:
            warnings.append(f"`{context_column}` is missing; CRAFTED-style comparability cannot be checked fully.")
    return ValidationResult(
        is_valid=not missing_required,
        missing_required=missing_required,
        available_recommended=available_recommended,
        warnings=warnings,
    )
