"""CoRE MOF 2014 enrichment adapter.

The adapter treats CoRE CIF files as descriptor/provenance records. It does not
try to infer structural identity beyond exact CSD-style identifier matching.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tarfile

import pandas as pd


CORE2014_SOURCE_DOI = "10.5281/zenodo.3986573"
CORE2014_SOURCE_VERSION = "CoRE MOF 2014 DDEC"
CORE2014_LICENSE = "CC BY 4.0"

CORE2014_CIF_TAG_COLUMNS = {
    "_chemical_formula_structural": "core_formula_structural",
    "_chemical_formula_sum": "core_formula_sum",
    "_cell_length_a": "core_cell_length_a",
    "_cell_length_b": "core_cell_length_b",
    "_cell_length_c": "core_cell_length_c",
    "_cell_angle_alpha": "core_cell_angle_alpha",
    "_cell_angle_beta": "core_cell_angle_beta",
    "_cell_angle_gamma": "core_cell_angle_gamma",
    "_cell_volume": "core_cell_volume",
    "_cell_formula_units_Z": "core_cell_formula_units_z",
    "_symmetry_space_group_name_H-M": "core_space_group_hm",
    "_symmetry_Int_Tables_number": "core_int_tables_number",
}

CORE2014_NUMERIC_COLUMNS = [
    "core_cell_length_a",
    "core_cell_length_b",
    "core_cell_length_c",
    "core_cell_angle_alpha",
    "core_cell_angle_beta",
    "core_cell_angle_gamma",
    "core_cell_volume",
    "core_cell_formula_units_z",
    "core_int_tables_number",
]


@dataclass(frozen=True)
class Core2014Record:
    """One extracted CoRE MOF 2014 descriptor/provenance record."""

    material_id: str
    core_match_status: str
    core_source_file: str | None
    core_original_filename: str | None
    core_had_clean_suffix: bool | None
    core_file_checksum_sha256: str | None
    core_source_version: str
    core_source_doi: str
    core_license: str
    core_formula_structural: str | None = None
    core_formula_sum: str | None = None
    core_cell_length_a: float | None = None
    core_cell_length_b: float | None = None
    core_cell_length_c: float | None = None
    core_cell_angle_alpha: float | None = None
    core_cell_angle_beta: float | None = None
    core_cell_angle_gamma: float | None = None
    core_cell_volume: float | None = None
    core_cell_formula_units_z: float | None = None
    core_space_group_hm: str | None = None
    core_int_tables_number: float | None = None


def normalize_core2014_member_name(path: str) -> str | None:
    """Return the material ID for a CoRE CIF member name."""
    name = Path(path).name
    if not name.endswith(".cif") or name.startswith("._"):
        return None
    stem = Path(name).stem
    if stem.endswith("_clean"):
        stem = stem.removesuffix("_clean")
    return stem.strip() or None


def _strip_cif_value(value: str) -> str:
    text = value.strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    return text


def _parse_simple_cif_tags(text: str) -> dict[str, object]:
    values: dict[str, object] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("_"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        tag, value = parts
        column = CORE2014_CIF_TAG_COLUMNS.get(tag)
        if not column:
            continue
        values[column] = _strip_cif_value(value)
    for column in CORE2014_NUMERIC_COLUMNS:
        if column in values:
            values[column] = pd.to_numeric(values[column], errors="coerce")
    return values


def _record_from_member(member: tarfile.TarInfo, payload: bytes) -> Core2014Record | None:
    material_id = normalize_core2014_member_name(member.name)
    if material_id is None:
        return None
    text = payload.decode("utf-8", errors="ignore")
    parsed = _parse_simple_cif_tags(text)
    original_filename = Path(member.name).name
    return Core2014Record(
        material_id=material_id,
        core_match_status="matched_core2014",
        core_source_file=member.name,
        core_original_filename=original_filename,
        core_had_clean_suffix=Path(original_filename).stem.endswith("_clean"),
        core_file_checksum_sha256=hashlib.sha256(payload).hexdigest(),
        core_source_version=CORE2014_SOURCE_VERSION,
        core_source_doi=CORE2014_SOURCE_DOI,
        core_license=CORE2014_LICENSE,
        **parsed,
    )


def load_core2014_records(archive_path: Path) -> pd.DataFrame:
    """Load CoRE MOF 2014 CIF metadata from a local tar archive."""
    if not archive_path.exists():
        raise FileNotFoundError(f"CoRE MOF 2014 archive not found: {archive_path}")

    records: list[Core2014Record] = []
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            record = _record_from_member(member, handle.read())
            if record is not None:
                records.append(record)
    return pd.DataFrame([record.__dict__ for record in records]).sort_values("material_id").reset_index(drop=True)


def build_core2014_enrichment(core_records: pd.DataFrame, target_ids: set[str]) -> pd.DataFrame:
    """Return one enrichment row per target material ID, preserving missing matches."""
    if "material_id" not in core_records.columns:
        raise ValueError("CoRE records must include material_id.")
    targets = pd.DataFrame({"material_id": sorted(target_ids)})
    deduped = core_records.drop_duplicates(subset=["material_id"], keep="first")
    enriched = targets.merge(deduped, on="material_id", how="left", validate="one_to_one")
    enriched["core_match_status"] = enriched["core_match_status"].fillna("missing_core2014")
    for column, value in (
        ("core_source_version", CORE2014_SOURCE_VERSION),
        ("core_source_doi", CORE2014_SOURCE_DOI),
        ("core_license", CORE2014_LICENSE),
    ):
        if column not in enriched.columns:
            enriched[column] = value
        else:
            enriched[column] = enriched[column].fillna(value)
    return enriched


def join_core2014_enrichment(screening: pd.DataFrame, enrichment: pd.DataFrame) -> pd.DataFrame:
    """Attach CoRE MOF 2014 descriptor/provenance columns to screening records."""
    if screening.empty:
        return screening.copy()
    if "material_id" not in screening.columns:
        raise ValueError("Screening table must include material_id before CoRE enrichment join.")
    if "material_id" not in enrichment.columns:
        raise ValueError("CoRE enrichment table must include material_id before join.")

    deduped = enrichment.drop_duplicates(subset=["material_id"], keep="first")
    joined = screening.merge(deduped, on="material_id", how="left", validate="many_to_one")
    joined["core_match_status"] = joined["core_match_status"].fillna("missing_core2014")
    for column, value in (
        ("core_source_version", CORE2014_SOURCE_VERSION),
        ("core_source_doi", CORE2014_SOURCE_DOI),
        ("core_license", CORE2014_LICENSE),
    ):
        if column not in joined.columns:
            joined[column] = value
        else:
            joined[column] = joined[column].fillna(value)
    return joined


def load_crafted_geometric_target_ids(path: Path) -> set[str]:
    """Load CRAFTED geometric FrameworkName IDs as the CoRE join target."""
    if not path.exists():
        raise FileNotFoundError(f"CRAFTED geometric descriptor file not found: {path}")
    frame = pd.read_csv(path, usecols=["FrameworkName"])
    return set(frame["FrameworkName"].dropna().astype(str).str.strip())
