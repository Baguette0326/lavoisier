"""Descriptor-based adsorption property prediction for unfamiliar MOFs.

This module is intentionally separate from weakly supervised triage. It trains
regression baselines from structural descriptors and controlled-condition fields
to estimate adsorption metrics for a candidate. Target adsorption metrics are
never used as model features.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


STRUCTURAL_DESCRIPTOR_FEATURES = (
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
    "pore_limiting_diameter_a",
    "largest_cavity_diameter_a",
    "void_fraction",
)

CORE2014_DESCRIPTOR_FEATURES = (
    "core_cell_length_a",
    "core_cell_length_b",
    "core_cell_length_c",
    "core_cell_angle_alpha",
    "core_cell_angle_beta",
    "core_cell_angle_gamma",
    "core_cell_volume",
    "core_cell_formula_units_z",
    "core_int_tables_number",
)

CONDITION_FEATURES = (
    "temperature_k",
    "co2_pressure_bar",
    "n2_pressure_bar",
)

PREDICTION_TARGETS = (
    "co2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
)

MINIMUM_TARGET_RECORDS = 5
HOLDOUT_TARGET_RECORDS = 20
DEFAULT_EVALUATION_RANDOM_SEEDS = (11, 23, 42, 71, 101)
MODERATE_RELATIVE_GAP = 0.15
LARGE_RELATIVE_GAP = 0.35


@dataclass(frozen=True)
class PropertyPredictionResult:
    """Predicted adsorption properties and model metadata."""

    predicted_properties: dict[str, float | None]
    prediction_summary: dict[str, object]


@dataclass(frozen=True)
class FeatureSetEvaluationResult:
    """Held-out evaluation comparing descriptor feature sets."""

    target_results: dict[str, dict[str, dict[str, object]]]
    comparison_summary: dict[str, object]


def _numeric_frame(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    return frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")


def _candidate_frame(candidate: Mapping[str, object], feature_columns: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame([{column: candidate.get(column) for column in feature_columns}]).apply(
        pd.to_numeric,
        errors="coerce",
    )


def _available_features(reference_frame: pd.DataFrame) -> list[str]:
    descriptor_features = [column for column in STRUCTURAL_DESCRIPTOR_FEATURES if column in reference_frame.columns]
    condition_features = [column for column in CONDITION_FEATURES if column in reference_frame.columns]
    return descriptor_features + condition_features


def _available_named_features(reference_frame: pd.DataFrame, feature_columns: Sequence[str]) -> list[str]:
    return [column for column in feature_columns if column in reference_frame.columns]


def _supplied_descriptor_count(candidate: Mapping[str, object]) -> int:
    supplied = 0
    for column in STRUCTURAL_DESCRIPTOR_FEATURES:
        value = pd.to_numeric(pd.Series([candidate.get(column)]), errors="coerce").iloc[0]
        if not pd.isna(value):
            supplied += 1
    return supplied


def _build_regressor() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=200,
                    random_state=42,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(float(np.mean(values)), 4)


def _std(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(float(np.std(values, ddof=1)), 4)


def _forest_prediction_interval(model: Pipeline, candidate_features: pd.DataFrame) -> dict[str, float | None]:
    """Estimate model spread from random-forest tree predictions."""
    regressor = model.named_steps["regressor"]
    imputer = model.named_steps["imputer"]
    transformed_candidate = imputer.transform(candidate_features)
    tree_predictions = np.array([tree.predict(transformed_candidate)[0] for tree in regressor.estimators_])
    if len(tree_predictions) == 0:
        return {
            "approx_p10": None,
            "approx_p90": None,
            "tree_std": None,
        }
    return {
        "approx_p10": round(float(np.percentile(tree_predictions, 10)), 4),
        "approx_p90": round(float(np.percentile(tree_predictions, 90)), 4),
        "tree_std": round(float(np.std(tree_predictions)), 4),
    }


def _supplied_prediction_comparison(
    candidate: Mapping[str, object],
    predictions: Mapping[str, float | None],
) -> dict[str, dict[str, object]]:
    comparisons: dict[str, dict[str, object]] = {}
    for target, predicted_value in predictions.items():
        supplied_value = pd.to_numeric(pd.Series([candidate.get(target)]), errors="coerce").iloc[0]
        if pd.isna(supplied_value):
            comparisons[target] = {
                "status": "not_supplied",
                "supplied_value": None,
                "predicted_value": predicted_value,
            }
            continue
        supplied_float = float(supplied_value)
        if predicted_value is None:
            comparisons[target] = {
                "status": "not_predicted",
                "supplied_value": round(supplied_float, 4),
                "predicted_value": None,
            }
            continue
        delta = supplied_float - predicted_value
        denominator = max(abs(predicted_value), 1e-9)
        relative_gap = abs(delta) / denominator
        if relative_gap > LARGE_RELATIVE_GAP:
            status = "large_supplied_prediction_gap"
        elif relative_gap > MODERATE_RELATIVE_GAP:
            status = "moderate_supplied_prediction_gap"
        else:
            status = "consistent_with_descriptor_prediction"
        comparisons[target] = {
            "status": status,
            "supplied_value": round(supplied_float, 4),
            "predicted_value": predicted_value,
            "delta_supplied_minus_predicted": round(float(delta), 4),
            "relative_gap": round(float(relative_gap), 4),
        }
    return comparisons


def _gap_warnings(comparisons: Mapping[str, Mapping[str, object]]) -> list[str]:
    warnings: list[str] = []
    for target, comparison in comparisons.items():
        if comparison.get("status") == "large_supplied_prediction_gap":
            warnings.append(
                f"{target} supplied value differs strongly from descriptor-based prediction; review provenance or assumptions"
            )
    return warnings


def predict_candidate_properties(
    reference_frame: pd.DataFrame,
    candidate: Mapping[str, object],
    targets: Sequence[str] = PREDICTION_TARGETS,
) -> PropertyPredictionResult:
    """Predict adsorption targets from descriptors for one unfamiliar candidate."""
    feature_columns = _available_features(reference_frame)
    descriptor_columns = [column for column in STRUCTURAL_DESCRIPTOR_FEATURES if column in reference_frame.columns]
    supplied_descriptor_count = _supplied_descriptor_count(candidate)
    warnings: list[str] = []

    if not descriptor_columns:
        warnings.append("reference table has no supported structural descriptor columns")
    if supplied_descriptor_count == 0:
        warnings.append("candidate has no supported structural descriptors; property predictions were skipped")
    if not feature_columns:
        supplied_prediction_comparison = _supplied_prediction_comparison(
            candidate,
            {target: None for target in targets},
        )
        return PropertyPredictionResult(
            predicted_properties={target: None for target in targets},
            prediction_summary={
                "method": "RandomForestRegressor descriptor baseline",
                "feature_policy": "structural descriptors plus controlled-condition fields; target adsorption metrics excluded",
                "feature_columns": [],
                "candidate_descriptor_count": supplied_descriptor_count,
                "candidate_descriptor_required_count": len(STRUCTURAL_DESCRIPTOR_FEATURES),
                "target_summaries": {},
                "supplied_prediction_comparison": supplied_prediction_comparison,
                "warnings": warnings,
                "official_use_policy": "Descriptor predictions are baseline estimates, not simulation or laboratory validation.",
            },
        )

    candidate_features = _candidate_frame(candidate, feature_columns)
    if candidate_features.loc[:, descriptor_columns].notna().sum(axis=1).iloc[0] == 0:
        supplied_prediction_comparison = _supplied_prediction_comparison(
            candidate,
            {target: None for target in targets},
        )
        return PropertyPredictionResult(
            predicted_properties={target: None for target in targets},
            prediction_summary={
                "method": "RandomForestRegressor descriptor baseline",
                "feature_policy": "structural descriptors plus controlled-condition fields; target adsorption metrics excluded",
                "feature_columns": feature_columns,
                "candidate_descriptor_count": supplied_descriptor_count,
                "candidate_descriptor_required_count": len(STRUCTURAL_DESCRIPTOR_FEATURES),
                "target_summaries": {},
                "supplied_prediction_comparison": supplied_prediction_comparison,
                "warnings": warnings,
                "official_use_policy": "Descriptor predictions are baseline estimates, not simulation or laboratory validation.",
            },
        )

    predictions: dict[str, float | None] = {}
    target_summaries: dict[str, dict[str, object]] = {}
    feature_frame = _numeric_frame(reference_frame, feature_columns)
    has_any_feature = feature_frame.notna().any(axis=1)

    for target in targets:
        if target not in reference_frame.columns:
            predictions[target] = None
            target_summaries[target] = {
                "status": "skipped_missing_target_column",
                "training_records": 0,
            }
            continue

        target_values = pd.to_numeric(reference_frame[target], errors="coerce")
        usable_rows = has_any_feature & target_values.notna()
        training_records = int(usable_rows.sum())
        if training_records < MINIMUM_TARGET_RECORDS:
            predictions[target] = None
            target_summaries[target] = {
                "status": "skipped_insufficient_training_records",
                "training_records": training_records,
                "minimum_required_records": MINIMUM_TARGET_RECORDS,
            }
            continue

        x = feature_frame.loc[usable_rows, feature_columns]
        y = target_values.loc[usable_rows]

        holdout_summary: dict[str, float | int | None] = {
            "test_records": 0,
            "test_mae": None,
            "test_r2": None,
        }
        if training_records >= HOLDOUT_TARGET_RECORDS:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y,
                test_size=0.2,
                random_state=42,
            )
            holdout_model = _build_regressor()
            holdout_model.fit(x_train, y_train)
            test_predictions = holdout_model.predict(x_test)
            holdout_summary = {
                "test_records": int(len(x_test)),
                "test_mae": round(float(mean_absolute_error(y_test, test_predictions)), 4),
                "test_r2": round(float(r2_score(y_test, test_predictions)), 4) if len(x_test) >= 2 else None,
            }

        final_model = _build_regressor()
        final_model.fit(x, y)
        candidate_feature_frame = candidate_features.loc[:, feature_columns]
        prediction = float(final_model.predict(candidate_feature_frame)[0])
        interval = _forest_prediction_interval(final_model, candidate_feature_frame)
        predictions[target] = round(prediction, 4)
        target_summaries[target] = {
            "status": "predicted",
            "training_records": training_records,
            "prediction_interval_method": "random_forest_tree_prediction_p10_p90",
            **interval,
            **holdout_summary,
        }

    supplied_prediction_comparison = _supplied_prediction_comparison(candidate, predictions)
    warnings.extend(_gap_warnings(supplied_prediction_comparison))

    return PropertyPredictionResult(
        predicted_properties=predictions,
        prediction_summary={
            "method": "RandomForestRegressor descriptor baseline",
            "target_source": "reference table adsorption metrics",
            "feature_policy": "structural descriptors plus controlled-condition fields; target adsorption metrics excluded",
            "feature_columns": feature_columns,
            "descriptor_features": list(STRUCTURAL_DESCRIPTOR_FEATURES),
            "condition_features": [column for column in CONDITION_FEATURES if column in feature_columns],
            "candidate_descriptor_count": supplied_descriptor_count,
            "candidate_descriptor_required_count": len(STRUCTURAL_DESCRIPTOR_FEATURES),
            "target_summaries": target_summaries,
            "supplied_prediction_comparison": supplied_prediction_comparison,
            "warnings": warnings,
            "official_use_policy": "Descriptor predictions are baseline estimates, not simulation or laboratory validation.",
        },
    )


def evaluate_property_prediction_feature_sets(
    reference_frame: pd.DataFrame,
    *,
    targets: Sequence[str] = PREDICTION_TARGETS,
    feature_sets: Mapping[str, Sequence[str]] | None = None,
    random_seeds: Sequence[int] = DEFAULT_EVALUATION_RANDOM_SEEDS,
) -> FeatureSetEvaluationResult:
    """Compare repeated held-out prediction quality for descriptor feature sets."""
    active_feature_sets = feature_sets or {
        "crafted_geometric": (*STRUCTURAL_DESCRIPTOR_FEATURES, *CONDITION_FEATURES),
        "crafted_geometric_plus_core2014": (
            *STRUCTURAL_DESCRIPTOR_FEATURES,
            *CORE2014_DESCRIPTOR_FEATURES,
            *CONDITION_FEATURES,
        ),
    }
    target_results: dict[str, dict[str, dict[str, object]]] = {}

    for target in targets:
        target_results[target] = {}
        if target not in reference_frame.columns:
            for feature_set_name in active_feature_sets:
                target_results[target][feature_set_name] = {
                    "status": "skipped_missing_target_column",
                    "feature_columns": [],
                    "training_records": 0,
                    "test_records": 0,
                    "test_mae": None,
                    "test_r2": None,
                }
            continue

        target_values = pd.to_numeric(reference_frame[target], errors="coerce")
        for feature_set_name, raw_feature_columns in active_feature_sets.items():
            feature_columns = _available_named_features(reference_frame, raw_feature_columns)
            if not feature_columns:
                target_results[target][feature_set_name] = {
                    "status": "skipped_no_available_features",
                    "feature_columns": [],
                    "training_records": 0,
                    "test_records": 0,
                    "test_mae": None,
                    "test_r2": None,
                }
                continue

            feature_frame = _numeric_frame(reference_frame, feature_columns)
            usable_rows = feature_frame.notna().any(axis=1) & target_values.notna()
            usable_count = int(usable_rows.sum())
            if usable_count < HOLDOUT_TARGET_RECORDS:
                target_results[target][feature_set_name] = {
                    "status": "skipped_insufficient_holdout_records",
                    "feature_columns": feature_columns,
                    "training_records": usable_count,
                    "test_records": 0,
                    "test_mae": None,
                    "test_r2": None,
                    "minimum_required_records": HOLDOUT_TARGET_RECORDS,
                }
                continue

            x = feature_frame.loc[usable_rows, feature_columns]
            y = target_values.loc[usable_rows]
            split_metrics: list[dict[str, float | int | None]] = []
            for seed in random_seeds:
                x_train, x_test, y_train, y_test = train_test_split(
                    x,
                    y,
                    test_size=0.2,
                    random_state=seed,
                )
                model = _build_regressor()
                model.fit(x_train, y_train)
                predictions = model.predict(x_test)
                split_metrics.append(
                    {
                        "random_seed": seed,
                        "test_records": int(len(x_test)),
                        "test_mae": round(float(mean_absolute_error(y_test, predictions)), 4),
                        "test_r2": round(float(r2_score(y_test, predictions)), 4) if len(x_test) >= 2 else None,
                    }
                )
            mae_values = [float(metric["test_mae"]) for metric in split_metrics if metric["test_mae"] is not None]
            r2_values = [float(metric["test_r2"]) for metric in split_metrics if metric["test_r2"] is not None]
            target_results[target][feature_set_name] = {
                "status": "evaluated",
                "feature_columns": feature_columns,
                "usable_records": usable_count,
                "training_records_per_split": int(len(x_train)),
                "test_records_per_split": int(len(x_test)),
                "split_count": len(split_metrics),
                "random_seeds": list(random_seeds),
                "test_mae": _mean(mae_values),
                "test_mae_std": _std(mae_values),
                "test_r2": _mean(r2_values),
                "test_r2_std": _std(r2_values),
                "split_metrics": split_metrics,
            }

    comparison_summary: dict[str, object] = {
        "method": "RandomForestRegressor repeated holdout feature-set comparison",
        "baseline_feature_set": "crafted_geometric",
        "candidate_feature_set": "crafted_geometric_plus_core2014",
        "target_comparisons": {},
        "use_policy": (
            "Use CoRE descriptors in the predictor only when held-out metrics improve or remain comparable "
            "and the added provenance/coverage tradeoff is acceptable."
        ),
    }
    target_comparisons = comparison_summary["target_comparisons"]
    assert isinstance(target_comparisons, dict)
    for target, results in target_results.items():
        baseline = results.get("crafted_geometric", {})
        candidate = results.get("crafted_geometric_plus_core2014", {})
        baseline_mae = baseline.get("test_mae")
        candidate_mae = candidate.get("test_mae")
        if baseline_mae is None or candidate_mae is None:
            target_comparisons[target] = {
                "status": "not_comparable",
                "baseline_test_mae": baseline_mae,
                "candidate_test_mae": candidate_mae,
                "mae_delta_candidate_minus_baseline": None,
            }
            continue
        mae_delta = round(float(candidate_mae) - float(baseline_mae), 4)
        baseline_splits = baseline.get("split_metrics", [])
        candidate_splits = candidate.get("split_metrics", [])
        split_deltas: list[float] = []
        if isinstance(baseline_splits, list) and isinstance(candidate_splits, list):
            for baseline_split, candidate_split in zip(baseline_splits, candidate_splits, strict=False):
                baseline_split_mae = baseline_split.get("test_mae") if isinstance(baseline_split, dict) else None
                candidate_split_mae = candidate_split.get("test_mae") if isinstance(candidate_split, dict) else None
                if baseline_split_mae is not None and candidate_split_mae is not None:
                    split_deltas.append(round(float(candidate_split_mae) - float(baseline_split_mae), 4))
        improvement_count = sum(1 for delta in split_deltas if delta < 0)
        split_count = len(split_deltas)
        improvement_fraction = round(improvement_count / split_count, 4) if split_count else None
        if mae_delta < 0 and improvement_fraction is not None and improvement_fraction >= 0.6:
            status = "candidate_feature_set_stably_improved_mae"
        elif mae_delta > 0 and improvement_fraction is not None and improvement_fraction <= 0.4:
            status = "candidate_feature_set_stably_worse_mae"
        elif mae_delta < 0:
            status = "candidate_feature_set_mixed_improved_mae"
        elif mae_delta > 0:
            status = "candidate_feature_set_mixed_worse_mae"
        else:
            status = "candidate_feature_set_tied_mae"
        target_comparisons[target] = {
            "status": status,
            "baseline_test_mae": baseline_mae,
            "candidate_test_mae": candidate_mae,
            "mae_delta_candidate_minus_baseline": mae_delta,
            "split_mae_deltas_candidate_minus_baseline": split_deltas,
            "candidate_improved_split_count": improvement_count,
            "comparable_split_count": split_count,
            "candidate_improved_split_fraction": improvement_fraction,
            "baseline_test_r2": baseline.get("test_r2"),
            "candidate_test_r2": candidate.get("test_r2"),
        }

    return FeatureSetEvaluationResult(target_results=target_results, comparison_summary=comparison_summary)
