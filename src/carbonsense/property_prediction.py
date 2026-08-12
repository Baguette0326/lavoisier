"""Descriptor-based adsorption property prediction for unfamiliar MOFs.

This module is intentionally separate from weakly supervised triage. It trains
regression baselines from structural descriptors and controlled-condition fields
to estimate adsorption metrics for a candidate. Target adsorption metrics are
never used as model features.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

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
MODERATE_RELATIVE_GAP = 0.15
LARGE_RELATIVE_GAP = 0.35


@dataclass(frozen=True)
class PropertyPredictionResult:
    """Predicted adsorption properties and model metadata."""

    predicted_properties: dict[str, float | None]
    prediction_summary: dict[str, object]


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
        prediction = float(final_model.predict(candidate_features.loc[:, feature_columns])[0])
        predictions[target] = round(prediction, 4)
        target_summaries[target] = {
            "status": "predicted",
            "training_records": training_records,
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
