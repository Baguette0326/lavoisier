"""CRAFTED dataset adapter.

This module supports the synthetic CRAFTED-like fixture and the first local-only
CRAFTED 2.0.1 parser slice. Real CRAFTED raw data remains outside Git.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

CRAFTED_GEOMETRIC_DESCRIPTOR_COLUMNS = {
    "FrameworkName": "material_id",
    "D_is": "largest_cavity_diameter_a",
    "D_fs": "pore_limiting_diameter_a",
    "D_isfs": "largest_included_free_sphere_diameter_a",
    "ASA_m^2/g": "surface_area_m2_g",
    "ASA_m^2/cm^3": "volumetric_surface_area_m2_cm3",
    "Density": "density_g_cm3",
    "AV_Volume_fraction": "void_fraction",
    "AV_cm^3/g": "pore_volume_cm3_g",
    "n_pockets": "pocket_count",
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
    co2_pressure_bar: float | None = None
    n2_pressure_bar: float | None = None


@dataclass(frozen=True)
class CraftedRealSliceConfig:
    """Exact-match parser target for a local CRAFTED 2.0.1 slice."""

    temperature_k: int = 298
    force_field: str = "UFF"
    charge_method: str = "DDEC"
    co2_pressure_bar: float = 0.2
    n2_pressure_bar: float = 1.0
    source_version: str = "CRAFTED 2.0.1"
    capture_context: str = "post-combustion"


def _crafted_result_path(
    root: Path,
    *,
    section: str,
    material_id: str,
    gas: str,
    config: CraftedRealSliceConfig,
) -> Path:
    filename = f"{config.charge_method}_{material_id}_{config.force_field}_{gas}_{config.temperature_k}.csv"
    return root / section / filename


def _read_exact_pressure_row(path: Path, target_pressure_bar: float) -> dict[str, float] | None:
    """Read one exact pressure row from a CRAFTED result CSV."""
    target_pressure_pa = target_pressure_bar * 100000.0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            try:
                pressure_pa = float(parts[0])
                value = float(parts[1])
                uncertainty = float(parts[2]) if len(parts) > 2 else float("nan")
            except ValueError:
                continue
            if abs(pressure_pa - target_pressure_pa) <= 1e-6:
                return {
                    "pressure_bar": pressure_pa / 100000.0,
                    "value": value,
                    "uncertainty": uncertainty,
                    "line_number": float(line_number),
                }
    return None


def _material_ids_for_config(root: Path, config: CraftedRealSliceConfig) -> list[str]:
    pattern = f"{config.charge_method}_*_{config.force_field}_CO2_{config.temperature_k}.csv"
    material_ids: list[str] = []
    for path in sorted((root / "ISOTHERM_FILES").glob(pattern)):
        if path.name.startswith("._"):
            continue
        prefix = f"{config.charge_method}_"
        suffix = f"_{config.force_field}_CO2_{config.temperature_k}.csv"
        material_ids.append(path.name.removeprefix(prefix).removesuffix(suffix))
    return material_ids


def parse_crafted_isotherm_long(
    root: Path,
    config: CraftedRealSliceConfig = CraftedRealSliceConfig(),
    *,
    limit: int | None = None,
) -> pd.DataFrame:
    """Parse selected exact CO2/N2 pressure points into a long table."""
    rows: list[dict[str, object]] = []
    material_ids = _material_ids_for_config(root, config)
    if limit is not None:
        material_ids = material_ids[:limit]

    gas_targets = {"CO2": config.co2_pressure_bar, "N2": config.n2_pressure_bar}
    for material_id in material_ids:
        for gas, target_pressure in gas_targets.items():
            path = _crafted_result_path(root, section="ISOTHERM_FILES", material_id=material_id, gas=gas, config=config)
            if not path.exists():
                continue
            value_row = _read_exact_pressure_row(path, target_pressure)
            if value_row is None:
                continue
            rows.append(
                {
                    "material_id": material_id,
                    "material_class": "MOF",
                    "evidence_type": "computational_gcmc",
                    "simulation_method": "GCMC",
                    "force_field": config.force_field,
                    "charge_method": config.charge_method,
                    "source": config.source_version,
                    "capture_context": config.capture_context,
                    "temperature_k": config.temperature_k,
                    "gas": gas,
                    "pressure_bar": value_row["pressure_bar"],
                    "uptake_mmol_g": value_row["value"],
                    "uptake_error_mmol_g": value_row["uncertainty"],
                    "source_file": str(path.relative_to(root)),
                    "source_record_id": f"{path.name}:line:{int(value_row['line_number'])}",
                }
            )
    return pd.DataFrame(rows)


def _read_heat_of_adsorption(
    root: Path,
    material_id: str,
    config: CraftedRealSliceConfig,
) -> tuple[float | None, str | None, str | None]:
    path = _crafted_result_path(root, section="ENTHALPY_FILES", material_id=material_id, gas="CO2", config=config)
    if not path.exists():
        return None, None, None
    value_row = _read_exact_pressure_row(path, config.co2_pressure_bar)
    if value_row is None:
        return None, str(path.relative_to(root)), None
    return (
        abs(value_row["value"]),
        str(path.relative_to(root)),
        f"{path.name}:line:{int(value_row['line_number'])}",
    )


def build_crafted_screening_slice(
    long_table: pd.DataFrame,
    root: Path,
    config: CraftedRealSliceConfig = CraftedRealSliceConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Derive one-row-per-material screening records and missing-pair blocks."""
    if long_table.empty:
        return pd.DataFrame(), pd.DataFrame()

    rows: list[dict[str, object]] = []
    blocked_rows: list[dict[str, object]] = []
    for material_id, group in long_table.groupby("material_id", sort=True):
        co2 = group[(group["gas"] == "CO2") & (group["pressure_bar"] == config.co2_pressure_bar)]
        n2 = group[(group["gas"] == "N2") & (group["pressure_bar"] == config.n2_pressure_bar)]
        if co2.empty or n2.empty:
            missing = []
            if co2.empty:
                missing.append("CO2")
            if n2.empty:
                missing.append("N2")
            blocked_rows.append(
                {
                    "material_id": material_id,
                    "material_class": "MOF",
                    "evidence_type": "computational_gcmc",
                    "simulation_method": "GCMC",
                    "force_field": config.force_field,
                    "charge_method": config.charge_method,
                    "source": config.source_version,
                    "capture_context": config.capture_context,
                    "temperature_k": config.temperature_k,
                    "pressure_bar": config.co2_pressure_bar,
                    "block_type": "incomplete_pair",
                    "block_reason": f"missing matched {'/'.join(missing)} point for selected exact pressure pair",
                    "rank_eligible": False,
                }
            )
            continue

        co2_row = co2.iloc[0]
        n2_row = n2.iloc[0]
        if co2_row["uptake_mmol_g"] <= 0 or n2_row["uptake_mmol_g"] <= 0:
            blocked_rows.append(
                {
                    "material_id": material_id,
                    "material_class": "MOF",
                    "evidence_type": "computational_gcmc",
                    "simulation_method": "GCMC",
                    "force_field": config.force_field,
                    "charge_method": config.charge_method,
                    "source": config.source_version,
                    "capture_context": config.capture_context,
                    "temperature_k": config.temperature_k,
                    "pressure_bar": config.co2_pressure_bar,
                    "block_type": "invalid_selectivity_denominator",
                    "block_reason": "CO2/N2 selectivity requires positive matched CO2 and N2 uptake values",
                    "rank_eligible": False,
                }
            )
            continue
        heat, heat_source_file, heat_source_record_id = _read_heat_of_adsorption(root, material_id, config)
        selectivity = (co2_row["uptake_mmol_g"] / n2_row["uptake_mmol_g"]) / (
            config.co2_pressure_bar / config.n2_pressure_bar
        )
        rows.append(
            {
                "material_id": material_id,
                "material_class": "MOF",
                "evidence_type": "computational_gcmc",
                "simulation_method": "GCMC",
                "force_field": config.force_field,
                "charge_method": config.charge_method,
                "source": config.source_version,
                "capture_context": config.capture_context,
                "temperature_k": config.temperature_k,
                "pressure_bar": config.co2_pressure_bar,
                "co2_pressure_bar": config.co2_pressure_bar,
                "n2_pressure_bar": config.n2_pressure_bar,
                "co2_uptake_mmol_g": co2_row["uptake_mmol_g"],
                "n2_uptake_mmol_g": n2_row["uptake_mmol_g"],
                "co2_n2_selectivity": selectivity,
                "heat_of_adsorption_kj_mol": heat,
                "co2_source_file": co2_row["source_file"],
                "co2_source_record_id": co2_row["source_record_id"],
                "n2_source_file": n2_row["source_file"],
                "n2_source_record_id": n2_row["source_record_id"],
                "heat_source_file": heat_source_file,
                "heat_source_record_id": heat_source_record_id,
                "humidity_condition": "dry simulation",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(blocked_rows)


def parse_crafted_real_slice(
    root: Path,
    config: CraftedRealSliceConfig = CraftedRealSliceConfig(),
    *,
    limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Parse the first approved local CRAFTED slice into long/screening/blocked tables."""
    long_table = parse_crafted_isotherm_long(root, config, limit=limit)
    screening, blocked = build_crafted_screening_slice(long_table, root, config)
    return long_table, screening, blocked


def load_crafted_mof_geometric_descriptors(path: Path) -> pd.DataFrame:
    """Load CRAFTED-provided MOF geometric descriptors with Lavoisier names."""
    raw = pd.read_csv(path)
    missing = sorted(set(CRAFTED_GEOMETRIC_DESCRIPTOR_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Missing CRAFTED geometric descriptor column(s): {', '.join(missing)}")

    result = raw[list(CRAFTED_GEOMETRIC_DESCRIPTOR_COLUMNS)].rename(columns=CRAFTED_GEOMETRIC_DESCRIPTOR_COLUMNS)
    result["material_id"] = result["material_id"].astype(str)
    numeric_columns = [column for column in result.columns if column != "material_id"]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["descriptor_source"] = "CRAFTED 2.0.1 RAC_DBSCAN/CRAFTED_MOF_geometric.csv"
    result["descriptor_type"] = "geometric_zeopp"
    return result


def join_crafted_geometric_descriptors(screening: pd.DataFrame, descriptors: pd.DataFrame) -> pd.DataFrame:
    """Attach CRAFTED geometric descriptors while preserving unmatched rows."""
    if screening.empty:
        return screening.copy()
    if "material_id" not in screening.columns:
        raise ValueError("Screening table must include material_id before descriptor join.")
    if "material_id" not in descriptors.columns:
        raise ValueError("Descriptor table must include material_id before descriptor join.")

    descriptor_columns = [column for column in descriptors.columns if column != "material_id"]
    deduped = descriptors.drop_duplicates(subset=["material_id"], keep="first")
    joined = screening.merge(deduped, on="material_id", how="left", validate="many_to_one")
    joined["descriptor_match_status"] = joined[descriptor_columns].notna().any(axis=1).map(
        {True: "matched_crafted_mof_geometric", False: "missing_crafted_mof_geometric"}
    )
    return joined


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
