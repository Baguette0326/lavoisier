import pandas as pd

from carbonsense.ml_triage import add_rule_triage_labels, classify_candidates


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
