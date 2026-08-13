import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from carbonsense.property_prediction import (
    PREDICTION_TARGETS,
    evaluate_property_prediction_feature_sets,
    predict_candidate_properties,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "predict_unfamiliar_candidate_properties.py"
FEATURE_SET_SCRIPT = PROJECT_ROOT / "scripts" / "evaluate_descriptor_feature_sets.py"


def _reference_frame(record_count: int = 30) -> pd.DataFrame:
    rows = []
    for index in range(record_count):
        surface_area = 900 + index * 35
        pore_volume = 0.25 + index * 0.015
        density = 1.2 - index * 0.01
        pore_limit = 3.0 + index * 0.05
        cavity = 4.5 + index * 0.08
        void_fraction = 0.1 + index * 0.005
        rows.append(
            {
                "material_id": f"mof-{index}",
                "surface_area_m2_g": surface_area,
                "pore_volume_cm3_g": pore_volume,
                "density_g_cm3": density,
                "pore_limiting_diameter_a": pore_limit,
                "largest_cavity_diameter_a": cavity,
                "void_fraction": void_fraction,
                "core_cell_length_a": 10 + index * 0.1,
                "core_cell_length_b": 11 + index * 0.1,
                "core_cell_length_c": 12 + index * 0.1,
                "core_cell_angle_alpha": 90,
                "core_cell_angle_beta": 90,
                "core_cell_angle_gamma": 90,
                "core_cell_volume": 1000 + index * 25,
                "core_cell_formula_units_z": 2,
                "core_int_tables_number": 1,
                "temperature_k": 298,
                "co2_pressure_bar": 0.2,
                "n2_pressure_bar": 1.0,
                "co2_uptake_mmol_g": 0.5 + surface_area / 1000 + pore_volume,
                "co2_n2_selectivity": 8 + pore_limit * 4 + void_fraction * 20,
                "heat_of_adsorption_kj_mol": 25 + density * 8 + cavity * 0.7,
            }
        )
    return pd.DataFrame(rows)


def _candidate() -> dict[str, object]:
    return {
        "material_id": "new-mof",
        "surface_area_m2_g": 1500,
        "pore_volume_cm3_g": 0.55,
        "density_g_cm3": 0.95,
        "pore_limiting_diameter_a": 4.0,
        "largest_cavity_diameter_a": 5.8,
        "void_fraction": 0.18,
        "temperature_k": 298,
        "co2_pressure_bar": 0.2,
        "n2_pressure_bar": 1.0,
    }


def test_predict_candidate_properties_uses_descriptors_not_target_metrics() -> None:
    result = predict_candidate_properties(_reference_frame(), _candidate())

    assert set(result.predicted_properties) == set(PREDICTION_TARGETS)
    assert all(value is not None for value in result.predicted_properties.values())
    feature_columns = result.prediction_summary["feature_columns"]
    assert "surface_area_m2_g" in feature_columns
    assert "co2_pressure_bar" in feature_columns
    assert "co2_uptake_mmol_g" not in feature_columns
    assert "co2_n2_selectivity" not in feature_columns
    assert "heat_of_adsorption_kj_mol" not in feature_columns
    assert result.prediction_summary["candidate_descriptor_count"] == 6
    uptake_summary = result.prediction_summary["target_summaries"]["co2_uptake_mmol_g"]
    assert uptake_summary["test_records"] > 0
    assert uptake_summary["prediction_interval_method"] == "random_forest_tree_prediction_p10_p90"
    assert uptake_summary["approx_p10"] <= result.predicted_properties["co2_uptake_mmol_g"] <= uptake_summary["approx_p90"]
    assert uptake_summary["tree_std"] >= 0
    comparison = result.prediction_summary["supplied_prediction_comparison"]
    assert comparison["co2_uptake_mmol_g"]["status"] == "not_supplied"


def test_predict_candidate_properties_flags_large_supplied_prediction_gap() -> None:
    candidate = _candidate()
    candidate["co2_uptake_mmol_g"] = 20.0

    result = predict_candidate_properties(_reference_frame(), candidate)

    comparison = result.prediction_summary["supplied_prediction_comparison"]
    assert comparison["co2_uptake_mmol_g"]["status"] == "large_supplied_prediction_gap"
    assert any("co2_uptake_mmol_g supplied value differs strongly" in warning for warning in result.prediction_summary["warnings"])


def test_predict_candidate_properties_skips_candidate_without_descriptors() -> None:
    result = predict_candidate_properties(
        _reference_frame(),
        {"material_id": "descriptor-free", "temperature_k": 298, "co2_pressure_bar": 0.2, "n2_pressure_bar": 1.0},
    )

    assert all(value is None for value in result.predicted_properties.values())
    assert "candidate has no supported structural descriptors" in result.prediction_summary["warnings"][0]


def test_property_prediction_script_writes_prediction_packet(tmp_path: Path) -> None:
    reference_path = tmp_path / "ranked_records.csv"
    candidate_path = tmp_path / "candidate.json"
    output_dir = tmp_path / "property_prediction"
    _reference_frame().to_csv(reference_path, index=False)
    candidate_path.write_text(json.dumps(_candidate()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--reference",
            str(reference_path),
            "--candidate",
            str(candidate_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Predicted properties:" in completed.stdout
    assert "Descriptor coverage: 6/6 candidate descriptors" in completed.stdout
    predictions = json.loads((output_dir / "predicted_properties.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "property_prediction_summary.json").read_text(encoding="utf-8"))
    report = (output_dir / "property_prediction_report.md").read_text(encoding="utf-8")
    assert set(predictions) == set(PREDICTION_TARGETS)
    assert summary["method"] == "RandomForestRegressor descriptor baseline"
    assert "target adsorption metrics excluded" in summary["feature_policy"]
    assert "supplied_prediction_comparison" in summary
    assert summary["target_summaries"]["co2_uptake_mmol_g"]["approx_p10"] is not None
    assert "# Candidate Property Prediction Report" in report
    assert "Approx P10" in report
    assert "## Supplied Vs Descriptor-Predicted Metrics" in report


def test_evaluate_property_prediction_feature_sets_compares_core_enrichment() -> None:
    result = evaluate_property_prediction_feature_sets(_reference_frame(40))

    assert set(result.target_results) == set(PREDICTION_TARGETS)
    uptake = result.target_results["co2_uptake_mmol_g"]
    assert uptake["crafted_geometric"]["status"] == "evaluated"
    assert uptake["crafted_geometric_plus_core2014"]["status"] == "evaluated"
    assert "core_cell_volume" in uptake["crafted_geometric_plus_core2014"]["feature_columns"]
    assert "core_cell_volume" not in uptake["crafted_geometric"]["feature_columns"]
    comparison = result.comparison_summary["target_comparisons"]["co2_uptake_mmol_g"]
    assert comparison["baseline_test_mae"] is not None
    assert comparison["candidate_test_mae"] is not None


def test_evaluate_descriptor_feature_sets_script_writes_reports(tmp_path: Path) -> None:
    reference_path = tmp_path / "ranked_records.csv"
    output_dir = tmp_path / "feature_set_evaluation"
    _reference_frame(40).to_csv(reference_path, index=False)

    completed = subprocess.run(
        [
            sys.executable,
            str(FEATURE_SET_SCRIPT),
            "--reference",
            str(reference_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Descriptor feature-set evaluation complete." in completed.stdout
    payload = json.loads((output_dir / "descriptor_feature_set_evaluation.json").read_text(encoding="utf-8"))
    report = (output_dir / "descriptor_feature_set_evaluation.md").read_text(encoding="utf-8")
    assert "comparison_summary" in payload
    assert "crafted_geometric_plus_core2014" == payload["comparison_summary"]["candidate_feature_set"]
    assert "# Descriptor Feature Set Evaluation" in report
