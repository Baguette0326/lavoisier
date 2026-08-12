import pandas as pd

from carbonsense.ml_triage import add_rule_triage_labels, classify_candidates, triage_unfamiliar_candidate


def test_add_rule_triage_labels_marks_promising_candidate() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["strong"],
            "rank_eligible": [True],
            "co2_uptake_mmol_g": [5.0],
            "n2_uptake_mmol_g": [0.1],
            "co2_n2_selectivity": [50.0],
            "heat_of_adsorption_kj_mol": [40.0],
            "screening_score": [0.8],
        }
    )

    result = add_rule_triage_labels(frame)

    assert result.loc[0, "rule_candidate_class"] == "promising_candidate"
    assert "high uptake" in result.loc[0, "rule_candidate_reason"]


def test_add_rule_triage_labels_marks_regeneration_risk_before_promising() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["sticky"],
            "rank_eligible": [True],
            "co2_uptake_mmol_g": [8.0],
            "n2_uptake_mmol_g": [0.1],
            "co2_n2_selectivity": [80.0],
            "heat_of_adsorption_kj_mol": [75.0],
            "screening_score": [0.9],
        }
    )

    result = add_rule_triage_labels(frame)

    assert result.loc[0, "rule_candidate_class"] == "high_regeneration_risk"


def test_add_rule_triage_labels_does_not_treat_nan_block_type_as_blocked() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["strong"],
            "rank_eligible": [True],
            "block_type": [float("nan")],
            "co2_uptake_mmol_g": [5.0],
            "n2_uptake_mmol_g": [0.1],
            "co2_n2_selectivity": [50.0],
            "heat_of_adsorption_kj_mol": [40.0],
            "screening_score": [0.8],
        }
    )

    result = add_rule_triage_labels(frame)

    assert result.loc[0, "rule_candidate_class"] == "promising_candidate"


def test_classify_candidates_adds_ml_review_columns() -> None:
    frame = pd.DataFrame(
        {
            "material_id": [f"MOF-{index}" for index in range(12)],
            "rank_eligible": [True] * 12,
            "co2_uptake_mmol_g": [5, 5.2, 4.8, 0.5, 0.7, 0.8, 2.5, 2.2, 2.8, 3.0, 1.5, 1.8],
            "n2_uptake_mmol_g": [0.1] * 12,
            "co2_n2_selectivity": [50, 55, 52, 20, 22, 25, 30, 28, 32, 8, 7, 9],
            "heat_of_adsorption_kj_mol": [40, 41, 39, 35, 36, 34, 45, 46, 44, 40, 42, 41],
            "screening_score": [0.8, 0.82, 0.78, 0.2, 0.22, 0.21, 0.5, 0.52, 0.51, 0.35, 0.3, 0.32],
            "temperature_k": [298] * 12,
            "co2_pressure_bar": [0.2] * 12,
            "n2_pressure_bar": [1.0] * 12,
            "force_field": ["UFF"] * 12,
            "charge_method": ["DDEC"] * 12,
            "evidence_type": ["computational_gcmc"] * 12,
            "simulation_method": ["GCMC"] * 12,
        }
    )

    result = classify_candidates(frame)

    assert "ml_candidate_class" in result.classified_records.columns
    assert "candidate_class_confidence" in result.classified_records.columns
    assert "candidate_class_features" in result.classified_records.columns
    assert result.training_summary["label_source"] == "weak_supervision_rule_derived"
    assert result.training_summary["record_count"] == 12
    assert "screening_score" not in result.training_summary["feature_columns"]
    assert result.training_summary["excluded_training_columns"] == ["screening_score"]
    assert result.training_summary["train_count"] == 12
    assert result.training_summary["validation_count"] == 0
    assert result.training_summary["test_count"] == 0


def test_classify_candidates_reports_train_validation_test_split() -> None:
    rows = []
    patterns = [
        ("promising", 5.0, 0.1, 50.0, 40.0, 0.8),
        ("balanced", 2.5, 0.1, 30.0, 45.0, 0.5),
        ("low", 0.6, 0.1, 20.0, 35.0, 0.2),
        ("poor", 3.0, 0.1, 8.0, 40.0, 0.3),
    ]
    for label, uptake, n2_uptake, selectivity, heat, score in patterns:
        for index in range(10):
            rows.append(
                {
                    "material_id": f"{label}-{index}",
                    "rank_eligible": True,
                    "co2_uptake_mmol_g": uptake + index * 0.01,
                    "n2_uptake_mmol_g": n2_uptake,
                    "co2_n2_selectivity": selectivity,
                    "heat_of_adsorption_kj_mol": heat,
                    "screening_score": score,
                    "temperature_k": 298,
                    "co2_pressure_bar": 0.2,
                    "n2_pressure_bar": 1.0,
                    "force_field": "UFF",
                    "charge_method": "DDEC",
                    "evidence_type": "computational_gcmc",
                    "simulation_method": "GCMC",
                }
            )
    frame = pd.DataFrame(rows)

    result = classify_candidates(frame)

    assert result.training_summary["train_count"] == 24
    assert result.training_summary["validation_count"] == 8
    assert result.training_summary["test_count"] == 8
    assert result.training_summary["validation_accuracy"] is not None
    assert result.training_summary["test_accuracy"] is not None


def _similarity_reference_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "material_id": ["strong-a", "strong-b", "balanced", "low-capacity", "poor-selectivity"],
            "rank_eligible": [True] * 5,
            "co2_uptake_mmol_g": [5.0, 5.3, 2.6, 0.4, 3.0],
            "n2_uptake_mmol_g": [0.1, 0.1, 0.1, 0.1, 0.4],
            "co2_n2_selectivity": [50.0, 52.0, 30.0, 20.0, 7.5],
            "heat_of_adsorption_kj_mol": [40.0, 42.0, 45.0, 35.0, 40.0],
            "screening_score": [0.8, 0.82, 0.5, 0.2, 0.3],
            "temperature_k": [298] * 5,
            "co2_pressure_bar": [0.2] * 5,
            "n2_pressure_bar": [1.0] * 5,
            "force_field": ["UFF"] * 5,
            "charge_method": ["DDEC"] * 5,
            "evidence_type": ["computational_gcmc"] * 5,
            "simulation_method": ["GCMC"] * 5,
        }
    )


def test_triage_unfamiliar_candidate_finds_similar_known_mofs() -> None:
    candidate = {
        "material_id": "new-isomer",
        "co2_uptake_mmol_g": 5.1,
        "n2_uptake_mmol_g": 0.1,
        "co2_n2_selectivity": 51.0,
        "heat_of_adsorption_kj_mol": 41.0,
        "temperature_k": 298,
        "co2_pressure_bar": 0.2,
        "n2_pressure_bar": 1.0,
        "force_field": "UFF",
        "charge_method": "DDEC",
        "evidence_type": "computational_gcmc",
        "simulation_method": "GCMC",
    }

    result = triage_unfamiliar_candidate(_similarity_reference_frame(), candidate, k=3)

    assert result.prediction_summary["method"] == "KNearestNeighbors similarity triage"
    assert result.prediction_summary["predicted_candidate_class"] == "promising_candidate"
    assert result.prediction_summary["rd_recommendation"] == "prioritize_deeper_review"
    assert result.prediction_summary["k_used"] == 3
    assert list(result.neighbor_records["material_id"][:2]) == ["strong-a", "strong-b"]
    assert "similarity_distance" in result.neighbor_records.columns


def test_triage_unfamiliar_candidate_warns_about_missing_descriptors() -> None:
    candidate = {
        "material_id": "sparse-new-mof",
        "co2_uptake_mmol_g": 5.1,
        "co2_n2_selectivity": 51.0,
    }

    result = triage_unfamiliar_candidate(_similarity_reference_frame(), candidate, k=2)

    assert result.prediction_summary["k_used"] == 2
    assert result.prediction_summary["rd_recommendation"] == "review_with_caution"
    assert result.prediction_summary["warnings"]
    assert "n2_uptake_mmol_g" in result.prediction_summary["warnings"][0]
