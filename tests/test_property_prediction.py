import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from carbonsense.property_prediction import PREDICTION_TARGETS, predict_candidate_properties


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "predict_unfamiliar_candidate_properties.py"


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
    assert result.prediction_summary["target_summaries"]["co2_uptake_mmol_g"]["test_records"] > 0


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
    assert "# Candidate Property Prediction Report" in report
