import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "evaluate_unfamiliar_candidate.py"


def test_evaluate_unfamiliar_candidate_script_writes_review_packet(tmp_path: Path) -> None:
    reference_path = tmp_path / "ranked_records.csv"
    candidate_path = tmp_path / "candidate.json"
    output_dir = tmp_path / "candidate_triage"

    pd.DataFrame(
        {
            "material_id": ["strong-a", "strong-b", "strong-c", "strong-d", "weak"],
            "rank_eligible": [True, True, True, True, True],
            "co2_uptake_mmol_g": [5.0, 5.2, 4.9, 5.1, 0.5],
            "n2_uptake_mmol_g": [0.1, 0.1, 0.1, 0.1, 0.2],
            "co2_n2_selectivity": [50.0, 52.0, 49.0, 51.0, 5.0],
            "heat_of_adsorption_kj_mol": [40.0, 42.0, 39.0, 41.0, 35.0],
            "screening_score": [0.8, 0.82, 0.79, 0.81, 0.2],
            "temperature_k": [298, 298, 298, 298, 298],
            "co2_pressure_bar": [0.2, 0.2, 0.2, 0.2, 0.2],
            "n2_pressure_bar": [1.0, 1.0, 1.0, 1.0, 1.0],
            "force_field": ["UFF", "UFF", "UFF", "UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC", "DDEC", "DDEC", "DDEC"],
            "evidence_type": [
                "computational_gcmc",
                "computational_gcmc",
                "computational_gcmc",
                "computational_gcmc",
                "computational_gcmc",
            ],
            "simulation_method": ["GCMC", "GCMC", "GCMC", "GCMC", "GCMC"],
            "surface_area_m2_g": [1200.0, 1220.0, 1180.0, 1210.0, 600.0],
            "pore_volume_cm3_g": [0.55, 0.57, 0.54, 0.56, 0.2],
            "density_g_cm3": [0.9, 0.88, 0.91, 0.89, 1.4],
            "pore_limiting_diameter_a": [4.1, 4.2, 4.0, 4.15, 2.1],
            "largest_cavity_diameter_a": [6.2, 6.3, 6.1, 6.25, 3.0],
            "void_fraction": [0.2, 0.21, 0.19, 0.205, 0.08],
        }
    ).to_csv(reference_path, index=False)
    candidate_path.write_text(
        json.dumps(
            {
                "material_id": "new-candidate",
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
                "surface_area_m2_g": 1210.0,
                "pore_volume_cm3_g": 0.56,
                "density_g_cm3": 0.89,
                "pore_limiting_diameter_a": 4.15,
                "largest_cavity_diameter_a": 6.25,
                "void_fraction": 0.205,
            }
        ),
        encoding="utf-8",
    )

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
            "--k",
            "2",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Predicted review class: promising_candidate" in completed.stdout
    assert "candidate_review_report.md" in completed.stdout
    assert "R&D recommendation: prioritize_deeper_review" in completed.stdout
    assert "Virtual lab decision:" in completed.stdout
    assert "Viability read:" in completed.stdout
    assert "Benchmark verdict: above_reference_candidate" in completed.stdout
    assert "Neighbor advantage: candidate_advantage_over_neighbors" in completed.stdout
    assert "Descriptor-predicted properties:" in completed.stdout
    assert "Supplied vs descriptor-predicted status:" in completed.stdout
    assert "Descriptor coverage: 6/6 candidate descriptors, 5/5 reference rows with descriptors" in completed.stdout
    assert "Next experiment steps:" in completed.stdout
    assert "test_neighbor_sensitivity_under_same_conditions" in completed.stdout
    summary = json.loads((output_dir / "candidate_similarity_summary.json").read_text(encoding="utf-8"))
    predictions = json.loads((output_dir / "predicted_properties.json").read_text(encoding="utf-8"))
    property_summary = json.loads((output_dir / "property_prediction_summary.json").read_text(encoding="utf-8"))
    assessment = json.loads((output_dir / "candidate_assessment_summary.json").read_text(encoding="utf-8"))
    report = (output_dir / "candidate_review_report.md").read_text(encoding="utf-8")
    neighbors = pd.read_csv(output_dir / "nearest_neighbors.csv")
    assert "# Candidate Review Report" in report
    assert "## Verdict" in report
    assert "## Virtual Lab Assessment" in report
    assert "R&D recommendation: `prioritize_deeper_review`" in report
    assert "## Metric Benchmarks" in report
    assert "## Descriptor-Predicted Properties" in report
    assert "## Supplied Vs Descriptor-Predicted Metrics" in report
    assert "## Descriptor Coverage" in report
    assert "## Neighbor Comparison" in report
    assert "## Nearest Neighbors" in report
    assert "## Next Experiment Steps" in report
    assert "not proof of experimental viability" in report
    assert summary["predicted_candidate_class"] == "promising_candidate"
    assert summary["rd_recommendation"] == "prioritize_deeper_review"
    assert summary["benchmark_verdict"] == "above_reference_candidate"
    assert summary["neighbor_advantage_verdict"] == "candidate_advantage_over_neighbors"
    assert summary["descriptor_coverage"]["candidate_supplied_count"] == 6
    assert "neighbor_metric_comparison" in summary
    assert "metric_benchmarks" in summary
    assert summary["next_experiment_steps"][0]["action"] == "test_neighbor_sensitivity_under_same_conditions"
    assert summary["k_used"] == 2
    assert predictions["co2_uptake_mmol_g"] is not None
    assert property_summary["candidate_descriptor_count"] == 6
    assert "target adsorption metrics excluded" in property_summary["feature_policy"]
    assert property_summary["supplied_prediction_comparison"]["co2_uptake_mmol_g"]["status"] in {
        "consistent_with_descriptor_prediction",
        "moderate_supplied_prediction_gap",
        "large_supplied_prediction_gap",
    }
    assert assessment["method"] == "rule_based_virtual_lab_assessment"
    assert assessment["final_decision"] in {
        "prioritize_deeper_review",
        "investigate_assumption_gap",
        "review_with_caution",
    }
    assert assessment["official_use_policy"].startswith("This assessment is a triage synthesis")
    assert neighbors["material_id"].tolist() == ["strong-d", "strong-a"]
