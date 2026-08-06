"""Local inspection helpers for approved CRAFTED archives.

This module does not approve, ingest, or rank CRAFTED data. It only inspects
local files after the user has completed license/provenance review.
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

import pandas as pd

from carbonsense.export import calculate_sha256


TABULAR_SUFFIXES = {".csv", ".tsv", ".txt"}

COLUMN_HINTS = {
    "material_id": ("material", "mof", "structure", "name", "id"),
    "gas": ("gas", "adsorbate", "component"),
    "pressure": ("pressure", "press", "p_bar", "pressure_bar"),
    "temperature": ("temperature", "temp", "t_k", "temperature_k"),
    "uptake": ("uptake", "loading", "adsorption", "amount"),
    "force_field": ("forcefield", "force_field", "ff"),
    "charge_method": ("charge", "charges", "charge_method"),
    "enthalpy": ("enthalpy", "heat", "qst"),
}

CRAFTED_RESULT_FILE_PATTERN = re.compile(
    r"^(?P<charge_method>[^_]+)_(?P<material_id>.+)_(?P<force_field>UFF|DREIDING)_(?P<gas>CO2|N2)_(?P<temperature_k>\d+)\.csv$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FileInspection:
    """Inspection summary for one file."""

    path: str
    suffix: str
    size_bytes: int
    checksum_sha256: str
    is_tabular: bool
    row_count: int | None
    columns: tuple[str, ...]


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith("._"):
            yield path


def _read_tabular_sample(path: Path) -> pd.DataFrame | None:
    suffix = path.suffix.casefold()
    if suffix not in TABULAR_SUFFIXES:
        return None
    separator = "\t" if suffix == ".tsv" else None
    try:
        return pd.read_csv(path, sep=separator, engine="python", nrows=5000)
    except Exception:
        return None


def _count_tabular_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            line_count = sum(1 for _ in handle)
    except OSError:
        return None
    return max(line_count - 1, 0)


def inspect_file(path: Path, root: Path) -> FileInspection:
    """Inspect one local file relative to an archive/folder root."""
    sample = _read_tabular_sample(path)
    relative_path = str(path.relative_to(root))
    return FileInspection(
        path=relative_path,
        suffix=path.suffix.casefold(),
        size_bytes=path.stat().st_size,
        checksum_sha256=calculate_sha256(path),
        is_tabular=sample is not None,
        row_count=_count_tabular_rows(path) if sample is not None else None,
        columns=tuple(str(column) for column in sample.columns) if sample is not None else (),
    )


def inspect_path(path: Path) -> list[FileInspection]:
    """Inspect a folder or zip archive and return file summaries."""
    if path.is_dir():
        root = path
        return [inspect_file(file_path, root) for file_path in _iter_files(root)]
    if path.suffix.casefold() == ".zip":
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with zipfile.ZipFile(path) as archive:
                archive.extractall(root)
            return [inspect_file(file_path, root) for file_path in _iter_files(root)]
    raise ValueError(f"Unsupported CRAFTED inspection path: {path}")


def build_archive_manifest(inspections: list[FileInspection]) -> pd.DataFrame:
    """Return a tabular manifest for inspected files."""
    return pd.DataFrame(asdict(inspection) for inspection in inspections)


def build_candidate_column_map(inspections: list[FileInspection]) -> dict[str, list[dict[str, str]]]:
    """Map likely semantic fields to candidate source columns."""
    candidates: dict[str, list[dict[str, str]]] = {field: [] for field in COLUMN_HINTS}
    for inspection in inspections:
        for column in inspection.columns:
            normalized = column.casefold().replace(" ", "_")
            for field, hints in COLUMN_HINTS.items():
                if any(hint in normalized for hint in hints):
                    candidates[field].append({"file": inspection.path, "column": column})
    return candidates


def _first_matching_column(columns: Iterable[str], hints: tuple[str, ...]) -> str | None:
    for column in columns:
        normalized = column.casefold().replace(" ", "_")
        if any(hint in normalized for hint in hints):
            return column
    return None


def build_pressure_availability(root: Path, inspections: list[FileInspection]) -> pd.DataFrame:
    """Summarize gas/pressure/temperature availability for likely isotherm tables."""
    rows: list[dict[str, object]] = []
    for inspection in inspections:
        if not inspection.is_tabular:
            continue
        path = root / inspection.path
        sample = _read_tabular_sample(path)
        if sample is None:
            continue
        gas_column = _first_matching_column(sample.columns, COLUMN_HINTS["gas"])
        pressure_column = _first_matching_column(sample.columns, COLUMN_HINTS["pressure"])
        if gas_column is None or pressure_column is None:
            continue
        temperature_column = _first_matching_column(sample.columns, COLUMN_HINTS["temperature"])
        force_field_column = _first_matching_column(sample.columns, COLUMN_HINTS["force_field"])
        charge_method_column = _first_matching_column(sample.columns, COLUMN_HINTS["charge_method"])
        material_column = _first_matching_column(sample.columns, COLUMN_HINTS["material_id"])

        grouped_columns = [gas_column, pressure_column]
        optional_columns = [temperature_column, force_field_column, charge_method_column]
        grouped_columns.extend(column for column in optional_columns if column is not None)
        grouped = sample.groupby(grouped_columns, dropna=False)
        for key, group in grouped:
            values = key if isinstance(key, tuple) else (key,)
            row = {
                "source_file": inspection.path,
                "gas": values[0],
                "pressure_bar": values[1],
                "record_count": len(group),
                "material_count": group[material_column].nunique() if material_column else None,
            }
            offset = 2
            if temperature_column is not None:
                row["temperature_k"] = values[offset]
                offset += 1
            if force_field_column is not None:
                row["force_field"] = values[offset]
                offset += 1
            if charge_method_column is not None:
                row["charge_method"] = values[offset]
            rows.append(row)
    return pd.DataFrame(rows)


def write_inspection_outputs(source_path: Path, output_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Inspect a local CRAFTED folder/archive and write review artifacts."""
    if source_path.is_dir() and (source_path / "ISOTHERM_FILES").exists():
        return write_crafted_folder_inspection_outputs(source_path, output_dir)

    if source_path.is_dir():
        root = source_path
        inspections = inspect_path(source_path)
    elif source_path.suffix.casefold() == ".zip":
        temp_dir_context = TemporaryDirectory()
        root = Path(temp_dir_context.name)
        with zipfile.ZipFile(source_path) as archive:
            archive.extractall(root)
        inspections = [inspect_file(file_path, root) for file_path in _iter_files(root)]
    else:
        raise ValueError(f"Unsupported CRAFTED inspection path: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "archive_manifest.csv"
    pressure_path = output_dir / "pressure_availability.csv"
    column_map_path = output_dir / "candidate_column_map.json"
    summary_path = output_dir / "inspection_summary.md"

    manifest = build_archive_manifest(inspections)
    manifest.to_csv(manifest_path, index=False)
    pressure_availability = build_pressure_availability(root, inspections)
    pressure_availability.to_csv(pressure_path, index=False)
    column_map = build_candidate_column_map(inspections)
    column_map_path.write_text(json.dumps(column_map, indent=2), encoding="utf-8")
    summary_path.write_text(
        build_inspection_summary(source_path, inspections, pressure_availability),
        encoding="utf-8",
    )
    if source_path.suffix.casefold() == ".zip":
        temp_dir_context.cleanup()
    return manifest_path, pressure_path, column_map_path, summary_path


def _parse_crafted_result_filename(path: Path, root: Path, data_kind: str) -> dict[str, object] | None:
    match = CRAFTED_RESULT_FILE_PATTERN.match(path.name)
    if not match:
        return None
    groups = match.groupdict()
    return {
        "path": str(path.relative_to(root)),
        "suffix": path.suffix.casefold(),
        "size_bytes": path.stat().st_size,
        "dataset_section": path.parent.name,
        "data_kind": data_kind,
        "charge_method": groups["charge_method"],
        "material_id": groups["material_id"],
        "force_field": groups["force_field"].upper(),
        "gas": groups["gas"].upper(),
        "temperature_k": int(groups["temperature_k"]),
    }


def _read_pressure_grid_bar(path: Path) -> tuple[float, ...]:
    pressures: list[float] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            raw_pressure = line.split(",", 1)[0]
            try:
                pressures.append(float(raw_pressure) / 100000.0)
            except ValueError:
                continue
    return tuple(pressures)


def _build_crafted_result_manifest(root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for section_name, data_kind in (("ISOTHERM_FILES", "isotherm"), ("ENTHALPY_FILES", "enthalpy")):
        section = root / section_name
        if not section.exists():
            continue
        for path in _iter_files(section):
            parsed = _parse_crafted_result_filename(path, root, data_kind)
            if parsed is not None:
                rows.append(parsed)
    return pd.DataFrame(rows)


def _build_crafted_pressure_availability(root: Path, manifest: pd.DataFrame) -> pd.DataFrame:
    if manifest.empty:
        return pd.DataFrame()
    isotherms = manifest[manifest["data_kind"] == "isotherm"].copy()
    if isotherms.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    grouped_columns = ["gas", "temperature_k", "force_field", "charge_method"]
    for key, group in isotherms.groupby(grouped_columns, dropna=False):
        gas, temperature_k, force_field, charge_method = key
        sample_path = root / str(group.iloc[0]["path"])
        pressure_grid = _read_pressure_grid_bar(sample_path)
        material_count = int(group["material_id"].nunique())
        for pressure_bar in pressure_grid:
            rows.append(
                {
                    "gas": gas,
                    "pressure_bar": pressure_bar,
                    "temperature_k": temperature_k,
                    "force_field": force_field,
                    "charge_method": charge_method,
                    "record_count": material_count,
                    "material_count": material_count,
                    "source_file_count": len(group),
                    "source_section": "ISOTHERM_FILES",
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["gas", "temperature_k", "force_field", "charge_method", "pressure_bar"]
    )


def write_crafted_folder_inspection_outputs(source_path: Path, output_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Write a CRAFTED-specific fast inspection for the extracted archive folder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "archive_manifest.csv"
    pressure_path = output_dir / "pressure_availability.csv"
    column_map_path = output_dir / "candidate_column_map.json"
    summary_path = output_dir / "inspection_summary.md"

    manifest = _build_crafted_result_manifest(source_path)
    manifest.to_csv(manifest_path, index=False)
    pressure_availability = _build_crafted_pressure_availability(source_path, manifest)
    pressure_availability.to_csv(pressure_path, index=False)
    column_map = {
        "material_id": [{"source": "filename", "field": "material_id"}],
        "gas": [{"source": "filename", "field": "gas"}],
        "pressure": [{"source": "isotherm_csv", "field": "pressure[Pa]", "converted_to": "pressure_bar"}],
        "temperature": [{"source": "filename", "field": "temperature_k"}],
        "uptake": [{"source": "isotherm_csv", "field": "mean_volume[mol/kg]"}],
        "force_field": [{"source": "filename", "field": "force_field"}],
        "charge_method": [{"source": "filename", "field": "charge_method"}],
        "enthalpy": [{"source": "enthalpy_csv", "field": "source file rows"}],
    }
    column_map_path.write_text(json.dumps(column_map, indent=2), encoding="utf-8")
    summary_path.write_text(
        build_crafted_folder_inspection_summary(source_path, manifest, pressure_availability),
        encoding="utf-8",
    )
    return manifest_path, pressure_path, column_map_path, summary_path


def build_crafted_folder_inspection_summary(
    source_path: Path,
    manifest: pd.DataFrame,
    pressure_availability: pd.DataFrame,
) -> str:
    """Build a human-readable summary for a CRAFTED-specific inspection."""
    isotherm_count = int((manifest["data_kind"] == "isotherm").sum()) if not manifest.empty else 0
    enthalpy_count = int((manifest["data_kind"] == "enthalpy").sum()) if not manifest.empty else 0
    mof_like_count = int(manifest["material_id"].nunique()) if "material_id" in manifest else 0
    lines = [
        "# CRAFTED Archive Inspection",
        "",
        f"- Source path: `{source_path}`",
        f"- Parsed isotherm files: {isotherm_count}",
        f"- Parsed enthalpy files: {enthalpy_count}",
        f"- Unique material identifiers in parsed result files: {mof_like_count}",
        f"- Pressure availability rows: {len(pressure_availability)}",
        "",
        "## Interpretation",
        "",
        "This inspection is CRAFTED-specific and uses filename metadata plus",
        "representative pressure grids. It does not approve, ingest, rank, or",
        "commit raw CRAFTED data.",
        "",
        "Use `pressure_availability.csv` to choose the first exact-match CO2/N2",
        "pressure pair for the parser.",
    ]
    return "\n".join(lines) + "\n"


def build_inspection_summary(
    source_path: Path,
    inspections: list[FileInspection],
    pressure_availability: pd.DataFrame,
) -> str:
    """Build a human-readable inspection summary."""
    tabular_count = sum(1 for inspection in inspections if inspection.is_tabular)
    pressure_rows = len(pressure_availability)
    lines = [
        "# CRAFTED Archive Inspection",
        "",
        f"- Source path: `{source_path}`",
        f"- Files inspected: {len(inspections)}",
        f"- Tabular files detected: {tabular_count}",
        f"- Pressure availability rows: {pressure_rows}",
        "",
        "## Interpretation",
        "",
        "This inspection does not approve, ingest, or rank CRAFTED data. It only",
        "summarizes local file structure after license/provenance review.",
        "",
        "Use `pressure_availability.csv` to decide whether the preferred",
        "post-combustion pressure pair is available as exact source records.",
    ]
    return "\n".join(lines) + "\n"
