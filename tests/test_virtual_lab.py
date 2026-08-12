from carbonsense.virtual_lab import synthesize_candidate_assessment


def _similarity_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "method": "KNearestNeighbors similarity triage",
        "predicted_candidate_class": "promising_candidate",
        "prediction_confidence": 0.85,
        "nearest_distance": 0.5,
        "rd_recommendation": "prioritize_deeper_review",
        "benchmark_verdict": "above_reference_candidate",
        "neighbor_advantage_verdict": "candidate_advantage_over_neighbors",
        "warnings": [],
    }
    summary.update(overrides)
    return summary


def _property_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "method": "RandomForestRegressor descriptor baseline",
        "target_summaries": {
            "co2_uptake_mmol_g": {"status": "predicted"},
            "co2_n2_selectivity": {"status": "predicted"},
            "heat_of_adsorption_kj_mol": {"status": "predicted"},
        },
        "supplied_prediction_comparison": {
            "co2_uptake_mmol_g": {"status": "consistent_with_descriptor_prediction"},
            "co2_n2_selectivity": {"status": "consistent_with_descriptor_prediction"},
            "heat_of_adsorption_kj_mol": {"status": "consistent_with_descriptor_prediction"},
        },
        "warnings": [],
    }
    summary.update(overrides)
    return summary


def test_synthesize_candidate_assessment_prioritizes_strong_consistent_candidate() -> None:
    result = synthesize_candidate_assessment(_similarity_summary(), _property_summary())

    assert result.assessment_summary["final_decision"] == "prioritize_deeper_review"
    assert result.assessment_summary["viability_read"] == "viable_candidate_for_deeper_review"
    assert result.assessment_summary["better_than_known_reference"] == "possibly_better_than_nearest_known_records"
    assert result.assessment_summary["review_confidence"] == "medium"


def test_synthesize_candidate_assessment_flags_large_metric_gap() -> None:
    result = synthesize_candidate_assessment(
        _similarity_summary(),
        _property_summary(
            supplied_prediction_comparison={
                "co2_uptake_mmol_g": {"status": "large_supplied_prediction_gap"},
            },
            warnings=["co2_uptake_mmol_g supplied value differs strongly from descriptor-based prediction"],
        ),
    )

    assert result.assessment_summary["final_decision"] == "investigate_assumption_gap"
    assert result.assessment_summary["viability_read"] == "potential_but_unresolved"
    assert "large_supplied_prediction_gap" in result.assessment_summary["evidence_flags"]
    assert result.assessment_summary["review_confidence"] == "low"


def test_synthesize_candidate_assessment_requires_missing_predictions() -> None:
    result = synthesize_candidate_assessment(
        _similarity_summary(),
        _property_summary(target_summaries={"co2_uptake_mmol_g": {"status": "skipped_insufficient_training_records"}}),
    )

    assert result.assessment_summary["final_decision"] == "complete_required_inputs"
    assert result.assessment_summary["better_than_known_reference"] == "insufficient_evidence"
