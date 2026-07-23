"""Transparent multi-criteria ranking for adsorbent screening."""

from __future__ import annotations

import numpy as np
import pandas as pd

from carbonsense.comparability import filter_rank_eligible


DEFAULT_WEIGHTS = {
    "co2_uptake_mmol_g": 0.30,
    "co2_n2_selectivity": 0.20,
    "heat_of_adsorption_kj_mol": 0.20,
    "surface_area_m2_g": 0.10,
    "pore_volume_cm3_g": 0.10,
    "density_g_cm3": 0.10,
}


def minmax_score(series: pd.Series, maximize: bool = True) -> pd.Series:
    """Return a 0-1 score for numeric values, preserving missing values as 0."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(0.0, index=series.index)
    minimum = numeric.min()
    maximum = numeric.max()
    if np.isclose(maximum, minimum):
        scored = pd.Series(1.0, index=series.index)
    else:
        scored = (numeric - minimum) / (maximum - minimum)
    if not maximize:
        scored = 1 - scored
    return scored.fillna(0.0)


def target_range_score(series: pd.Series, low: float, high: float) -> pd.Series:
    """Score values highest inside a target range and lower outside it."""
    numeric = pd.to_numeric(series, errors="coerce")
    midpoint = (low + high) / 2
    half_width = (high - low) / 2
    if half_width <= 0:
        raise ValueError("Target range must have high > low.")
    distance = (numeric - midpoint).abs()
    score = 1 - (distance - half_width).clip(lower=0) / max(abs(midpoint), half_width)
    return score.clip(lower=0, upper=1).fillna(0.0)


def rank_materials(
    frame: pd.DataFrame,
    weights: dict[str, float] | None = None,
    require_rank_eligible: bool = True,
) -> pd.DataFrame:
    """Rank materials with transparent weighted criteria."""
    active_weights = weights or DEFAULT_WEIGHTS
    result = filter_rank_eligible(frame) if require_rank_eligible else frame.copy()
    total_weight = sum(weight for column, weight in active_weights.items() if column in result.columns)
    if total_weight <= 0:
        result["screening_score"] = 0.0
        return result

    score = pd.Series(0.0, index=result.index)
    for column, weight in active_weights.items():
        if column not in result.columns:
            continue
        normalized_weight = weight / total_weight
        if column == "heat_of_adsorption_kj_mol":
            component = target_range_score(result[column], low=25, high=60)
        elif column == "density_g_cm3":
            component = minmax_score(result[column], maximize=False)
        else:
            component = minmax_score(result[column], maximize=True)
        result[f"{column}_score"] = component
        score += normalized_weight * component
    result["screening_score"] = score.round(4)
    return result.sort_values("screening_score", ascending=False)
