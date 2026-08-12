"""Weakly supervised ML candidate triage for Lavoisier.

The labels in this module are engineering review labels derived from transparent
rules. They are not ground-truth experimental success labels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC_FEATURES = [
    "co2_uptake_mmol_g",
    "n2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
    "temperature_k",
    "co2_pressure_bar",
    "n2_pressure_bar",
]

CATEGORICAL_FEATURES = [
    "force_field",
    "charge_method",
    "evidence_type",
    "simulation_method",
]

TRIAGE_CLASS_ORDER = (
    "manual_review_required",
    "needs_more_data",
    "high_regeneration_risk",
    "poor_selectivity",
    "low_capacity",
    "promising_candidate",
    "balanced_candidate",
    "rank_ready",
)


@dataclass(frozen=True)
class CandidateClassifierResult:
    """Result of weakly supervised candidate classification."""

    classified_records: pd.DataFrame
    training_summary: dict[str, object]


@dataclass(frozen=True)
class SimilarityTriageResult:
    """Result of comparing an unfamiliar candidate with known MOF records."""

    neighbor_records: pd.DataFrame
    prediction_summary: dict[str, object]


def _numeric(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _row_has_missing_required_metrics(row: pd.Series) -> bool:
    for column in ("co2_uptake_mmol_g", "n2_uptake_mmol_g", "co2_n2_selectivity", "heat_of_adsorption_kj_mol"):
        if _numeric(row.get(column)) is None:
            return True
    return False


def label_candidate(row: pd.Series) -> tuple[str, str]:
    """Assign one transparent weak-supervision review label."""
    rank_eligible = row.get("rank_eligible")
    is_blocked = rank_eligible is False or str(rank_eligible).casefold() == "false" or bool(_text(row.get("block_type", "")))
    if is_blocked:
        return "manual_review_required", "record is blocked or not rank-eligible"
    if _row_has_missing_required_metrics(row):
        return "needs_more_data", "one or more required screening metrics are missing"

    uptake = _numeric(row.get("co2_uptake_mmol_g"))
    selectivity = _numeric(row.get("co2_n2_selectivity"))
    heat = _numeric(row.get("heat_of_adsorption_kj_mol"))
    score = _numeric(row.get("screening_score")) or 0.0

    if uptake is None or selectivity is None or heat is None:
        return "needs_more_data", "one or more required screening metrics are missing"
    if heat > 60:
        return "high_regeneration_risk", "CO2 heat of adsorption is above the conservative first-pass range"
    if selectivity < 10:
        return "poor_selectivity", "CO2/N2 selectivity is below the first-pass threshold"
    if uptake < 1:
        return "low_capacity", "CO2 uptake is below the first-pass capacity threshold"
    if uptake >= 4 and selectivity >= 40 and 25 <= heat <= 60 and score >= 0.5:
        return "promising_candidate", "high uptake, strong selectivity, acceptable heat, and strong screening score"
    if uptake >= 2 and selectivity >= 20 and 25 <= heat <= 60:
        return "balanced_candidate", "moderate uptake, useful selectivity, and acceptable heat"
    return "rank_ready", "record is complete and comparable but not in a stronger triage class"


def add_rule_triage_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Add transparent rule-derived candidate triage labels."""
    result = frame.copy()
    labels: list[str] = []
    reasons: list[str] = []
    for _, row in result.iterrows():
        label, reason = label_candidate(row)
        labels.append(label)
        reasons.append(reason)
    result["rule_candidate_class"] = pd.Categorical(labels, categories=TRIAGE_CLASS_ORDER)
    result["rule_candidate_reason"] = reasons
    return result


def _available_features(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = [column for column in NUMERIC_FEATURES if column in frame.columns]
    categorical = [column for column in CATEGORICAL_FEATURES if column in frame.columns]
    return numeric, categorical


def _build_classifier(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    transformers = []
    if numeric_features:
        transformers.append(("numeric", SimpleImputer(strategy="median"), numeric_features))
    if categorical_features:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            )
        )
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", model)])


def _build_similarity_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric_features:
        transformers.append(
            (
                "numeric",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
                numeric_features,
            )
        )
    if categorical_features:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical_features,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _can_split(labels: pd.Series, test_fraction: float) -> bool:
    counts = labels.value_counts()
    test_size = max(1, int(np.ceil(len(labels) * test_fraction)))
    return len(counts) > 1 and counts.min() >= 2 and test_size >= len(counts)


def _top_feature_summary(frame: pd.DataFrame) -> pd.Series:
    summaries: list[str] = []
    for _, row in frame.iterrows():
        scored = []
        for column in ("screening_score", "co2_uptake_mmol_g", "co2_n2_selectivity", "heat_of_adsorption_kj_mol"):
            value = _numeric(row.get(column))
            if value is not None:
                scored.append(f"{column}={value:.4g}")
        summaries.append("; ".join(scored[:3]))
    return pd.Series(summaries, index=frame.index)


def _frame_with_feature_columns(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in feature_columns:
        if column not in result.columns:
            result[column] = np.nan
    return result[feature_columns]


def triage_unfamiliar_candidate(
    reference_frame: pd.DataFrame,
    candidate: pd.Series | dict[str, object],
    *,
    k: int = 5,
) -> SimilarityTriageResult:
    """Compare an unfamiliar candidate against known records using nearest neighbors.

    This is a review aid. It does not prove real-world viability; it explains
    whether the candidate resembles known records that our weak-supervision
    rules consider promising, balanced, weak, or risky.
    """
    if k < 1:
        raise ValueError("k must be at least 1.")

    labelled = add_rule_triage_labels(reference_frame)
    numeric_features, categorical_features = _available_features(labelled)
    if not numeric_features and not categorical_features:
        raise ValueError("No supported similarity features are available.")

    feature_columns = numeric_features + categorical_features
    reference = labelled[labelled["rule_candidate_class"].notna()].copy()
    if reference.empty:
        raise ValueError("At least one labelled reference record is required.")

    candidate_frame = pd.DataFrame([candidate])
    preprocessor = _build_similarity_preprocessor(numeric_features, categorical_features)
    reference_matrix = preprocessor.fit_transform(_frame_with_feature_columns(reference, feature_columns))
    candidate_matrix = preprocessor.transform(_frame_with_feature_columns(candidate_frame, feature_columns))

    neighbor_count = min(k, len(reference))
    model = NearestNeighbors(n_neighbors=neighbor_count, metric="euclidean")
    model.fit(reference_matrix)
    distances, indices = model.kneighbors(candidate_matrix)

    neighbors = reference.iloc[indices[0]].copy()
    neighbor_distances = distances[0]
    weights = 1 / (1 + neighbor_distances)
    neighbors["similarity_distance"] = np.round(neighbor_distances, 4)
    neighbors["similarity_weight"] = np.round(weights, 4)

    class_weights: dict[str, float] = {}
    for label, weight in zip(neighbors["rule_candidate_class"].astype(str), weights, strict=True):
        class_weights[label] = class_weights.get(label, 0.0) + float(weight)
    total_weight = sum(class_weights.values())
    predicted_class = max(class_weights, key=class_weights.get)
    confidence = class_weights[predicted_class] / total_weight if total_weight else 0.0

    missing_candidate_features = [
        column for column in feature_columns if column not in candidate_frame.columns or pd.isna(candidate_frame.iloc[0][column])
    ]
    warnings: list[str] = []
    if missing_candidate_features:
        warnings.append(
            "Candidate is missing supported descriptor(s): " + ", ".join(missing_candidate_features)
        )
    if neighbor_distances[0] > 3:
        warnings.append("Nearest known MOF is far in feature space; treat the prediction as low-confidence.")

    summary = {
        "method": "KNearestNeighbors similarity triage",
        "label_source": "weak_supervision_rule_derived",
        "k_requested": int(k),
        "k_used": int(neighbor_count),
        "feature_columns": feature_columns,
        "predicted_candidate_class": predicted_class,
        "prediction_confidence": round(float(confidence), 4),
        "nearest_distance": round(float(neighbor_distances[0]), 4),
        "class_weight_vote": {key: round(value, 4) for key, value in sorted(class_weights.items())},
        "warnings": warnings,
        "official_use_policy": "Similarity triage is a review aid; it suggests whether deeper simulation or lab review is justified.",
    }
    return SimilarityTriageResult(neighbor_records=neighbors, prediction_summary=summary)


def classify_candidates(frame: pd.DataFrame) -> CandidateClassifierResult:
    """Train a weakly supervised classifier and add ML triage predictions."""
    labelled = add_rule_triage_labels(frame)
    numeric_features, categorical_features = _available_features(labelled)
    if not numeric_features and not categorical_features:
        raise ValueError("No supported triage features are available.")

    training_frame = labelled[labelled["rule_candidate_class"].notna()].copy()
    labels = training_frame["rule_candidate_class"].astype(str)
    classifier = _build_classifier(numeric_features, categorical_features)
    X = training_frame[numeric_features + categorical_features]

    metrics: dict[str, object] = {
        "label_source": "weak_supervision_rule_derived",
        "record_count": int(len(training_frame)),
        "feature_columns": numeric_features + categorical_features,
        "excluded_training_columns": ["screening_score"],
        "class_counts": {key: int(value) for key, value in labels.value_counts().sort_index().items()},
        "model": "RandomForestClassifier",
        "split_policy": "60/20/20 stratified train/validation/test when class counts support it",
        "official_ranking_policy": "ML classes are review aids; measured ranking and comparability remain authoritative.",
    }

    if len(training_frame) >= 15 and _can_split(labels, 0.20):
        X_train_valid, X_test, y_train_valid, y_test = train_test_split(
            X,
            labels,
            test_size=0.20,
            random_state=42,
            stratify=labels,
        )
        if _can_split(y_train_valid, 0.25):
            X_train, X_valid, y_train, y_valid = train_test_split(
                X_train_valid,
                y_train_valid,
                test_size=0.25,
                random_state=42,
                stratify=y_train_valid,
            )
        else:
            X_train, X_valid, y_train, y_valid = X_train_valid, X_test, y_train_valid, y_test
            metrics["validation_note"] = "Validation split reused test holdout because class counts were too small."

        classifier.fit(X_train, y_train)
        valid_predicted = classifier.predict(X_valid)
        test_predicted = classifier.predict(X_test)
        metrics["train_count"] = int(len(X_train))
        metrics["validation_count"] = int(len(X_valid))
        metrics["test_count"] = int(len(X_test))
        metrics["validation_accuracy"] = float(accuracy_score(y_valid, valid_predicted))
        metrics["test_accuracy"] = float(accuracy_score(y_test, test_predicted))
        metrics["validation_report"] = classification_report(y_valid, valid_predicted, output_dict=True, zero_division=0)
        metrics["test_report"] = classification_report(y_test, test_predicted, output_dict=True, zero_division=0)
        metrics["holdout_accuracy"] = metrics["test_accuracy"]
        metrics["holdout_report"] = metrics["test_report"]
        classifier.fit(X, labels)
    else:
        classifier.fit(X, labels)
        metrics["train_count"] = int(len(X))
        metrics["validation_count"] = 0
        metrics["test_count"] = 0
        metrics["validation_accuracy"] = None
        metrics["test_accuracy"] = None
        metrics["validation_report"] = None
        metrics["test_report"] = None
        metrics["holdout_accuracy"] = None
        metrics["holdout_report"] = None
        metrics["holdout_note"] = "Not enough labelled examples per class for stratified train/validation/test evaluation."

    predicted_labels = classifier.predict(labelled[numeric_features + categorical_features])
    probabilities = classifier.predict_proba(labelled[numeric_features + categorical_features])
    confidences = np.max(probabilities, axis=1)

    result = labelled.copy()
    result["ml_candidate_class"] = predicted_labels
    result["candidate_class_confidence"] = confidences.round(4)
    result["candidate_class_features"] = _top_feature_summary(result)
    return CandidateClassifierResult(classified_records=result, training_summary=metrics)
