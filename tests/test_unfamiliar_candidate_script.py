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
            "material_id": ["strong-a", "strong-b", "weak"],
            "rank_eligible": [True, True, True],
            "co2_uptake_mmol_g": [5.0, 5.2, 0.5],
            "n2_uptake_mmol_g": [0.1, 0.1, 0.2],
            "co2_n2_selectivity": [50.0, 52.0, 5.0],
            "heat_of_adsorption_kj_mol": [40.0, 42.0, 35.0],
            "screening_score": [0.8, 0.82, 0.2],
            "temperature_k": [298, 298, 298],
            "co2_pressure_bar": [0.2, 0.2, 0.2],
            "n2_pressure_bar": [1.0, 1.0, 1.0],
            "force_field": ["UFF", "UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC", "DDEC"],
            "evidence_type": ["computational_gcmc", "computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC", "GCMC"],
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
    assert "R&D recommendation: prioritize_deeper_review" in completed.stdout
    assert "Benchmark verdict: competitive_with_reference" in completed.stdout
    summary = json.loads((output_dir / "candidate_similarity_summary.json").read_text(encoding="utf-8"))
    neighbors = pd.read_csv(output_dir / "nearest_neighbors.csv")
    assert summary["predicted_candidate_class"] == "promising_candidate"
    assert summary["rd_recommendation"] == "prioritize_deeper_review"
    assert summary["benchmark_verdict"] == "competitive_with_reference"
    assert "metric_benchmarks" in summary
    assert summary["k_used"] == 2
    assert neighbors["material_id"].tolist() == ["strong-a", "strong-b"]
