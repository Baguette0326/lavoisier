"""Canonical field matching, parsing, and unit metadata."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .models import ScalarValue, UnitMetadata, UnitStatus


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    aliases: tuple[str, ...] = ()
    value_type: type = str
    canonical_unit: str | None = None
    quantity_kind: str | None = None


FIELD_DEFINITIONS = (
    FieldDefinition("material_id", ("material", "material_identifier", "mof_id")),
    FieldDefinition("evidence_type", ("evidence", "data_type")),
    FieldDefinition("source", ("reference", "citation")),
    FieldDefinition("capture_context", ("capture_process", "application")),
    FieldDefinition("co2_uptake_mmol_g", ("co2_uptake", "carbon_dioxide_uptake"), float, "mmol/g", "specific_uptake"),
    FieldDefinition("co2_n2_selectivity", ("co2_n2_selectivity_ratio", "selectivity"), float, "1", "ratio"),
    FieldDefinition("heat_of_adsorption_kj_mol", ("heat_of_adsorption", "qst"), float, "kJ/mol", "molar_energy"),
    FieldDefinition("surface_area_m2_g", ("surface_area", "bet_surface_area"), float, "m^2/g", "specific_area"),
    FieldDefinition("pore_volume_cm3_g", ("pore_volume",), float, "cm^3/g", "specific_volume"),
    FieldDefinition("pore_limiting_diameter_a", ("pore_limiting_diameter", "pld"), float, "angstrom", "length"),
    FieldDefinition("largest_cavity_diameter_a", ("largest_cavity_diameter", "lcd"), float, "angstrom", "length"),
    FieldDefinition("density_g_cm3", ("density",), float, "g/cm^3", "density"),
    FieldDefinition("humidity_flag", ("humidity", "water_stability"), bool),
)

_BY_NAME = {definition.name: definition for definition in FIELD_DEFINITIONS}
_UNIT_PATTERN = re.compile(r"\s*[\[(]([^\])]+)[\])]\s*$")
_NUMBER_WITH_UNIT = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*?)\s*$")


def normalize_field_name(value: str) -> str:
    """Normalize labels while preserving chemical digits such as CO2 and N2."""
    normalized = value.strip().lower().replace("²", "2").replace("³", "3").replace("å", "angstrom")
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def match_field(raw_field: str, explicit_mapping: dict[str, str] | None = None) -> tuple[FieldDefinition | None, float]:
    """Match a source label to a canonical definition and return match confidence."""
    if explicit_mapping and raw_field in explicit_mapping:
        target = explicit_mapping[raw_field]
        if target not in _BY_NAME:
            raise ValueError(f"Unknown canonical field in explicit mapping: {target}")
        return _BY_NAME[target], 1.0

    without_unit = _UNIT_PATTERN.sub("", raw_field)
    normalized = normalize_field_name(without_unit)
    if normalized in _BY_NAME:
        return _BY_NAME[normalized], 1.0
    for definition in FIELD_DEFINITIONS:
        if normalized in definition.aliases:
            return definition, 0.9
    return None, 0.0


def parse_candidate_value(raw_value: str, definition: FieldDefinition | None) -> tuple[ScalarValue, str | None, tuple[str, ...]]:
    """Parse only unambiguous scalar values and retain the original text."""
    value = raw_value.strip()
    if definition is None or definition.value_type is str:
        return value, None, ()

    if definition.value_type is bool:
        lowered = value.lower()
        if lowered in {"yes", "true", "1"}:
            return True, None, ()
        if lowered in {"no", "false", "0"}:
            return False, None, ()
        return value, None, ("Boolean value was not recognized and remains text.",)

    match = _NUMBER_WITH_UNIT.fullmatch(value)
    if not match:
        return value, None, ("Numeric value was not recognized and remains text.",)
    number, trailing_unit = match.groups()
    return float(number), trailing_unit or None, ()


def build_unit_metadata(
    raw_field: str,
    definition: FieldDefinition | None,
    value_unit: str | None,
) -> UnitMetadata:
    """Capture unit state; never convert values."""
    if definition is None or definition.canonical_unit is None:
        return UnitMetadata(None, None, None, UnitStatus.NOT_APPLICABLE)

    field_match = _UNIT_PATTERN.search(raw_field)
    source_unit = value_unit or (field_match.group(1).strip() if field_match else None)
    if source_unit is None and normalize_field_name(raw_field) == definition.name:
        source_unit = definition.canonical_unit
    if source_unit is None:
        status = UnitStatus.MISSING
    elif _normalize_unit(source_unit) == _normalize_unit(definition.canonical_unit):
        status = UnitStatus.EXACT
    else:
        status = UnitStatus.REQUIRES_REVIEW
    return UnitMetadata(source_unit, definition.canonical_unit, definition.quantity_kind, status)


def _normalize_unit(unit: str) -> str:
    normalized = unit.strip().lower().replace(" ", "").replace("·", "").replace("−", "-")
    replacements = {"mmolg-1": "mmol/g", "kjmol-1": "kj/mol", "m2g-1": "m^2/g", "cm3g-1": "cm^3/g", "gcm-3": "g/cm^3", "a": "angstrom", "å": "angstrom", "unitless": "1"}
    return replacements.get(normalized, normalized)
