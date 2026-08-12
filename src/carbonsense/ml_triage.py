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
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
    "pore_limiting_diameter_a",
    "largest_cavity_diameter_a",
    "void_fraction",
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

BENCHMARK_METRICS = (
    "co2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
)

STRUCTURAL_DESCRIPTOR_FEATURES = (
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
    "pore_limiting_diameter_a",
    "largest_cavity_diameter_a",
    "void_fraction",
)

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


def _rd_recommendation(
    predicted_class: str,
    confidence: float,
    nearest_distance: float,
    warnings: list[str],
) -> tuple[str, str]:
    if warnings:
        if any("missing supported descriptor" in warning.casefold() for warning in warnings):
            return (
                "review_with_caution",
                "candidate has missing descriptors, so similarity and benchmark evidence are incomplete",
            )
        return (
            "review_with_caution",
            "candidate is outside the familiar reference space, so neighbor evidence is weak",
        )
    if nearest_distance > 3:
        return (
            "review_with_caution",
            "nearest known MOF is far away, so neighbor evidence is weak",
        )
    if predicted_class == "promising_candidate" and confidence >= 0.6:
        return (
            "prioritize_deeper_review",
            "candidate resembles known promising records with enough neighbor agreement",
        )
    if predicted_class in {"balanced_candidate", "rank_ready", "promising_candidate"}:
        return (
            "consider_for_deeper_review",
            "candidate resembles usable known records, but evidence is not strong enough to prioritize",
        )
    if predicted_class in {"poor_selectivity", "low_capacity", "high_regeneration_risk"}:
        return (
            "deprioritize_until_new_evidence",
            "candidate resembles known records with a first-pass screening limitation",
        )
    return (
        "manual_review_required",
        "candidate resembles records that require missing-data or comparability review",
    )


def _percentile_rank(reference_values: pd.Series, candidate_value: float) -> float:
    numeric = pd.to_numeric(reference_values, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    return float((numeric <= candidate_value).mean())


def _metric_benchmarks(reference: pd.DataFrame, candidate_frame: pd.DataFrame) -> tuple[dict[str, object], str]:
    candidate_row = candidate_frame.iloc[0]
    benchmarks: dict[str, object] = {}
    available_percentiles: dict[str, float] = {}
    for metric in BENCHMARK_METRICS:
        if metric not in reference.columns or metric not in candidate_frame.columns:
            continue
        candidate_value = _numeric(candidate_row.get(metric))
        reference_values = pd.to_numeric(reference[metric], errors="coerce").dropna()
        if candidate_value is None or reference_values.empty:
            continue

        percentile = _percentile_rank(reference_values, candidate_value)
        detail: dict[str, object] = {
            "candidate_value": round(candidate_value, 4),
            "reference_count": int(len(reference_values)),
            "reference_median": round(float(reference_values.median()), 4),
            "percentile_rank": round(percentile, 4),
        }
        if metric == "heat_of_adsorption_kj_mol":
            if 25 <= candidate_value <= 60:
                detail["target_status"] = "inside_first_pass_target_range"
            elif candidate_value > 60:
                detail["target_status"] = "above_first_pass_target_range"
            else:
                detail["target_status"] = "below_first_pass_target_range"
        benchmarks[metric] = detail
        available_percentiles[metric] = percentile

    uptake = available_percentiles.get("co2_uptake_mmol_g")
    selectivity = available_percentiles.get("co2_n2_selectivity")
    heat_detail = benchmarks.get("heat_of_adsorption_kj_mol", {})
    heat_target_status = heat_detail.get("target_status") if isinstance(heat_detail, dict) else None

    if uptake is None or selectivity is None or heat_target_status is None:
        verdict = "insufficient_metric_benchmark"
    elif uptake >= 0.75 and selectivity >= 0.75 and heat_target_status == "inside_first_pass_target_range":
        verdict = "above_reference_candidate"
    elif heat_target_status == "above_first_pass_target_range" or uptake < 0.25 or selectivity < 0.25:
        verdict = "below_reference_or_risky"
    elif uptake >= 0.5 and selectivity >= 0.5 and heat_target_status == "inside_first_pass_target_range":
        verdict = "competitive_with_reference"
    else:
        verdict = "mixed_against_reference"
    return benchmarks, verdict


def _descriptor_coverage(reference: pd.DataFrame, candidate_frame: pd.DataFrame) -> dict[str, object]:
    available_descriptors = [column for column in STRUCTURAL_DESCRIPTOR_FEATURES if column in reference.columns]
    candidate_supplied = [
        column
        for column in STRUCTURAL_DESCRIPTOR_FEATURES
        if column in candidate_frame.columns and _numeric(candidate_frame.iloc[0].get(column)) is not None
    ]
    reference_rows_with_any_descriptor = 0
    reference_rows_with_all_descriptors = 0
    if available_descriptors:
        descriptor_values = reference[available_descriptors].apply(pd.to_numeric, errors="coerce")
        reference_rows_with_any_descriptor = int(descriptor_values.notna().any(axis=1).sum())
        reference_rows_with_all_descriptors = int(descriptor_values.notna().all(axis=1).sum())
    missing_candidate_descriptors = [
        column for column in STRUCTURAL_DESCRIPTOR_FEATURES if column not in candidate_supplied
    ]
    return {
        "descriptor_features": list(STRUCTURAL_DESCRIPTOR_FEATURES),
        "candidate_supplied_count": len(candidate_supplied),
        "candidate_required_count": len(STRUCTURAL_DESCRIPTOR_FEATURES),
        "candidate_supplied_descriptors": candidate_supplied,
        "candidate_missing_descriptors": missing_candidate_descriptors,
        "reference_record_count": int(len(reference)),
        "reference_rows_with_any_descriptor": reference_rows_with_any_descriptor,
        "reference_rows_with_all_descriptors": reference_rows_with_all_descriptors,
    }


def _next_experiment_steps(
    predicted_class: str,
    benchmark_verdict: str,
    metric_benchmarks: dict[str, object],
    warnings: list[str],
) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    if warnings:
        if any("missing supported descriptor" in warning.casefold() for warning in warnings):
            steps.append(
                {
                    "priority": "high",
                    "action": "complete_candidate_descriptor_set",
                    "reason": "similarity and benchmark verdicts are less reliable while required descriptors are missing",
                }
            )
            return steps
        steps.append(
            {
                "priority": "high",
                "action": "review_out_of_domain_similarity",
                "reason": "nearest known MOFs are far away in feature space, so compare assumptions and descriptor scaling before trusting the verdict",
            }
        )
        return steps

    heat_detail = metric_benchmarks.get("heat_of_adsorption_kj_mol", {})
    heat_status = heat_detail.get("target_status") if isinstance(heat_detail, dict) else None
    if heat_status == "above_first_pass_target_range" or predicted_class == "high_regeneration_risk":
        steps.append(
            {
                "priority": "high",
                "action": "check_regeneration_energy_or_heat_of_adsorption",
                "reason": "candidate may bind CO2 too strongly for economical regeneration",
            }
        )

    if predicted_class == "poor_selectivity" or benchmark_verdict == "below_reference_or_risky":
        steps.append(
            {
                "priority": "high",
                "action": "rerun_or_validate_co2_n2_selectivity",
                "reason": "candidate may not separate CO2 from N2 well enough under the selected slice",
            }
        )
    elif benchmark_verdict in {"above_reference_candidate", "competitive_with_reference"}:
        steps.append(
            {
                "priority": "medium",
                "action": "test_neighbor_sensitivity_under_same_conditions",
                "reason": "candidate looks competitive, so compare it against nearest known MOFs under identical assumptions",
            }
        )

    if predicted_class in {"promising_candidate", "balanced_candidate"} and benchmark_verdict != "below_reference_or_risky":
        steps.append(
            {
                "priority": "medium",
                "action": "add_humidity_or_cycling_stability_evidence",
                "reason": "dry CO2/N2 screening is not enough to justify lab prioritization by itself",
            }
        )

    if not steps:
        steps.append(
            {
                "priority": "medium",
                "action": "manual_domain_review",
                "reason": "candidate result is mixed or ordinary, so expert review should decide whether more data is worth collecting",
            }
        )
    return steps


def _neighbor_advantage(candidate_frame: pd.DataFrame, neighbors: pd.DataFrame) -> tuple[dict[str, object], str]:
    candidate_row = candidate_frame.iloc[0]
    comparisons: dict[str, object] = {}
    favorable_count = 0
    comparable_count = 0
    for metric in BENCHMARK_METRICS:
        if metric not in candidate_frame.columns or metric not in neighbors.columns:
            continue
        candidate_value = _numeric(candidate_row.get(metric))
        neighbor_values = pd.to_numeric(neighbors[metric], errors="coerce").dropna()
        if candidate_value is None or neighbor_values.empty:
            continue

        neighbor_median = float(neighbor_values.median())
        delta = candidate_value - neighbor_median
        detail: dict[str, object] = {
            "candidate_value": round(candidate_value, 4),
            "neighbor_median": round(neighbor_median, 4),
            "delta_vs_neighbor_median": round(delta, 4),
        }
        if metric == "heat_of_adsorption_kj_mol":
            favorable = 25 <= candidate_value <= 60
            detail["interpretation"] = "within_target_range" if favorable else "outside_target_range"
        else:
            favorable = delta > 0
            detail["interpretation"] = "above_neighbor_median" if favorable else "not_above_neighbor_median"
        comparable_count += 1
        favorable_count += int(favorable)
        comparisons[metric] = detail

    if comparable_count < len(BENCHMARK_METRICS):
        verdict = "insufficient_neighbor_comparison"
    elif favorable_count == comparable_count:
        verdict = "candidate_advantage_over_neighbors"
    elif favorable_count >= 2:
        verdict = "candidate_mixed_advantage_over_neighbors"
    else:
        verdict = "candidate_no_clear_neighbor_advantage"
    return comparisons, verdict


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
    metric_benchmarks, benchmark_verdict = _metric_benchmarks(reference, candidate_frame)
    descriptor_coverage = _descriptor_coverage(reference, candidate_frame)
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
    neighbor_comparison, neighbor_advantage_verdict = _neighbor_advantage(candidate_frame, neighbors)

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
    recommendation, recommendation_reason = _rd_recommendation(
        predicted_class,
        confidence,
        float(neighbor_distances[0]),
        warnings,
    )
    next_steps = _next_experiment_steps(predicted_class, benchmark_verdict, metric_benchmarks, warnings)

    summary = {
        "method": "KNearestNeighbors similarity triage",
        "label_source": "weak_supervision_rule_derived",
        "k_requested": int(k),
        "k_used": int(neighbor_count),
        "feature_columns": feature_columns,
        "predicted_candidate_class": predicted_class,
        "prediction_confidence": round(float(confidence), 4),
        "nearest_distance": round(float(neighbor_distances[0]), 4),
        "benchmark_verdict": benchmark_verdict,
        "metric_benchmarks": metric_benchmarks,
        "descriptor_coverage": descriptor_coverage,
        "neighbor_advantage_verdict": neighbor_advantage_verdict,
        "neighbor_metric_comparison": neighbor_comparison,
        "rd_recommendation": recommendation,
        "rd_recommendation_reason": recommendation_reason,
        "next_experiment_steps": next_steps,
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
