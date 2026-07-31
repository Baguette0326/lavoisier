"""Domain-specific comparability checks for MOF carbon-capture records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

import pandas as pd


class ComparabilityStatus(StrEnum):
    """Whether a record can participate in ranked comparison."""

    COMPARABLE = "comparable"
    PARTIALLY_COMPARABLE = "partially_comparable"
    NOT_COMPARABLE = "not_comparable"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ComparabilityRules:
    """Conservative rule settings for one review scope."""

    require_capture_context: bool = True
    require_evidence_type: bool = True
    require_material_class: bool = True
    require_simulation_method: bool = True
    require_force_field: bool = True
    require_charge_method: bool = True
    require_temperature: bool = True
    require_pressure: bool = True
    require_humidity: bool = False
    temperature_tolerance_k: float = 5.0
    pressure_tolerance_bar: float = 0.05
    allowed_evidence_types: tuple[str, ...] = ("computational_gcmc", "computational")
    allowed_material_classes: tuple[str, ...] = ("mof",)
    allowed_simulation_methods: tuple[str, ...] = ("gcmc",)


DEFAULT_RULES = ComparabilityRules()


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _numeric_or_none(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def _baseline_value(frame: pd.DataFrame, column: str) -> object | None:
    if column not in frame.columns:
        return None
    values = frame[column].dropna()
    if values.empty:
        return None
    return values.iloc[0]


def _same_as_baseline(row: pd.Series, baseline: object | None, column: str) -> bool:
    if baseline is None or column not in row.index:
        return False
    return _normalize_text(row[column]) == _normalize_text(baseline)


def _within_tolerance(row: pd.Series, baseline: object | None, column: str, tolerance: float) -> bool:
    if baseline is None or column not in row.index:
        return False
    row_value = _numeric_or_none(row[column])
    baseline_value = _numeric_or_none(baseline)
    if row_value is None or baseline_value is None:
        return False
    return abs(row_value - baseline_value) <= tolerance


def evaluate_row_comparability(
    row: pd.Series,
    frame: pd.DataFrame,
    rules: ComparabilityRules = DEFAULT_RULES,
) -> tuple[ComparabilityStatus, tuple[str, ...], bool]:
    """Evaluate one record against conservative comparability rules."""
    reasons: list[str] = []

    capture_baseline = _baseline_value(frame, "capture_context")
    evidence_baseline = _baseline_value(frame, "evidence_type")
    material_class_baseline = _baseline_value(frame, "material_class")
    simulation_baseline = _baseline_value(frame, "simulation_method")
    force_field_baseline = _baseline_value(frame, "force_field")
    charge_method_baseline = _baseline_value(frame, "charge_method")
    temp_baseline = _baseline_value(frame, "temperature_k")
    pressure_baseline = _baseline_value(frame, "pressure_bar")
    humidity_baseline = _baseline_value(frame, "humidity_condition")

    material_class = _normalize_text(row.get("material_class", ""))
    if rules.require_material_class:
        if not material_class:
            reasons.append("material class is missing")
        elif material_class not in rules.allowed_material_classes:
            reasons.append(f"material class `{row.get('material_class')}` is outside the MOF MVP scope")
        elif not _same_as_baseline(row, material_class_baseline, "material_class"):
            reasons.append("material class differs from comparison scope")

    evidence = _normalize_text(row.get("evidence_type", ""))
    if rules.require_evidence_type:
        if not evidence:
            reasons.append("evidence type is missing")
        elif evidence not in rules.allowed_evidence_types:
            reasons.append(f"evidence type `{row.get('evidence_type')}` is not recognized")
        elif not _same_as_baseline(row, evidence_baseline, "evidence_type"):
            reasons.append("evidence type differs from comparison scope")

    simulation = _normalize_text(row.get("simulation_method", ""))
    if rules.require_simulation_method:
        if not simulation:
            reasons.append("simulation method is missing")
        elif simulation not in rules.allowed_simulation_methods:
            reasons.append(f"simulation method `{row.get('simulation_method')}` is outside the GCMC MVP scope")
        elif not _same_as_baseline(row, simulation_baseline, "simulation_method"):
            reasons.append("simulation method differs from comparison scope")

    if rules.require_force_field:
        if not _normalize_text(row.get("force_field", "")):
            reasons.append("force field is missing")
        elif not _same_as_baseline(row, force_field_baseline, "force_field"):
            reasons.append("force field differs from comparison scope")

    if rules.require_charge_method:
        if not _normalize_text(row.get("charge_method", "")):
            reasons.append("charge method is missing")
        elif not _same_as_baseline(row, charge_method_baseline, "charge_method"):
            reasons.append("charge method differs from comparison scope")

    if rules.require_capture_context:
        if not _normalize_text(row.get("capture_context", "")):
            reasons.append("capture context is missing")
        elif not _same_as_baseline(row, capture_baseline, "capture_context"):
            reasons.append("capture context differs from comparison scope")

    if rules.require_temperature:
        if _numeric_or_none(row.get("temperature_k")) is None:
            reasons.append("temperature_k is missing or non-numeric")
        elif not _within_tolerance(row, temp_baseline, "temperature_k", rules.temperature_tolerance_k):
            reasons.append("temperature differs beyond tolerance")

    if rules.require_pressure:
        if _numeric_or_none(row.get("pressure_bar")) is None:
            reasons.append("pressure_bar is missing or non-numeric")
        elif not _within_tolerance(row, pressure_baseline, "pressure_bar", rules.pressure_tolerance_bar):
            reasons.append("pressure differs beyond tolerance")

    if rules.require_humidity:
        humidity = _normalize_text(row.get("humidity_condition", ""))
        if not humidity:
            reasons.append("humidity condition is missing")
        elif humidity in {"unknown", "not reported", "nan"}:
            reasons.append("humidity condition is not reported")
        elif not _same_as_baseline(row, humidity_baseline, "humidity_condition"):
            reasons.append("humidity condition differs from comparison scope")

    if not reasons:
        return ComparabilityStatus.COMPARABLE, (), True
    if any("missing" in reason or "not reported" in reason for reason in reasons):
        return ComparabilityStatus.NEEDS_REVIEW, tuple(reasons), False
    return ComparabilityStatus.NOT_COMPARABLE, tuple(reasons), False


def _block_type_for_reasons(reasons: Iterable[str]) -> str:
    """Classify a non-eligible record into a stable review category."""
    reason_text = "; ".join(reasons).casefold()
    if not reason_text:
        return ""
    if "missing" in reason_text or "not reported" in reason_text:
        if "co2" in reason_text or "n2" in reason_text or "pair" in reason_text:
            return "incomplete_pair"
        if "temperature" in reason_text or "pressure" in reason_text:
            return "condition_mismatch"
        return "missing_required_metric"
    if "pressure" in reason_text:
        return "pressure_mismatch"
    if (
        "temperature" in reason_text
        or "force field" in reason_text
        or "charge method" in reason_text
        or "evidence type" in reason_text
        or "simulation method" in reason_text
        or "capture context" in reason_text
        or "material class" in reason_text
    ):
        return "condition_mismatch"
    if "unit" in reason_text:
        return "invalid_units"
    return "manual_review_required"


def add_comparability_columns(
    frame: pd.DataFrame,
    rules: ComparabilityRules = DEFAULT_RULES,
) -> pd.DataFrame:
    """Add comparability status, block reasons, and rank eligibility columns."""
    result = frame.copy()
    statuses: list[str] = []
    reason_strings: list[str] = []
    block_types: list[str] = []
    eligible: list[bool] = []
    for _, row in result.iterrows():
        status, reasons, is_eligible = evaluate_row_comparability(row, result, rules)
        statuses.append(status.value)
        reason_strings.append("; ".join(reasons))
        block_types.append("" if is_eligible else _block_type_for_reasons(reasons))
        eligible.append(is_eligible)
    result["comparability_status"] = statuses
    result["comparability_reasons"] = reason_strings
    result["block_type"] = block_types
    result["block_reason"] = reason_strings
    result["rank_eligible"] = eligible
    return result


def filter_rank_eligible(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only records explicitly eligible for ranking."""
    if "rank_eligible" not in frame.columns:
        return frame.copy()
    return frame[frame["rank_eligible"] == True].copy()  # noqa: E712 - pandas boolean mask
