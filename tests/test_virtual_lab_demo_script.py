import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run_virtual_lab_demo.py"


def test_run_virtual_lab_demo_writes_demo_packet(tmp_path: Path) -> None:
    reference_path = tmp_path / "ranked_records.csv"
    candidate_dir = tmp_path / "candidates"
    output_dir = tmp_path / "demo"
    candidate_dir.mkdir()

    pd.DataFrame(
        {
            "material_id": ["strong-a", "strong-b", "balanced-a", "weak-a", "weak-b"],
            "rank_eligible": [True, True, True, True, True],
            "co2_uptake_mmol_g": [5.0, 5.2, 2.5, 0.5, 0.6],
            "n2_uptake_mmol_g": [0.1, 0.1, 0.12, 0.2, 0.22],
            "co2_n2_selectivity": [50.0, 52.0, 25.0, 5.0, 6.0],
            "heat_of_adsorption_kj_mol": [40.0, 42.0, 32.0, 35.0, 36.0],
            "screening_score": [0.8, 0.82, 0.55, 0.2, 0.22],
            "temperature_k": [298, 298, 298, 298, 298],
            "co2_pressure_bar": [0.2, 0.2, 0.2, 0.2, 0.2],
            "n2_pressure_bar": [1.0, 1.0, 1.0, 1.0, 1.0],
            "force_field": ["UFF", "UFF", "UFF", "UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC", "DDEC", "DDEC", "DDEC"],
            "evidence_type": ["computational_gcmc"] * 5,
            "simulation_method": ["GCMC"] * 5,
            "surface_area_m2_g": [1200.0, 1220.0, 900.0, 600.0, 620.0],
            "pore_volume_cm3_g": [0.55, 0.57, 0.4, 0.2, 0.22],
            "density_g_cm3": [0.9, 0.88, 1.0, 1.4, 1.38],
            "pore_limiting_diameter_a": [4.1, 4.2, 3.2, 2.1, 2.2],
            "largest_cavity_diameter_a": [6.2, 6.3, 4.5, 3.0, 3.1],
            "void_fraction": [0.2, 0.21, 0.15, 0.08, 0.09],
        }
    ).to_csv(reference_path, index=False)
    (candidate_dir / "demo.json").write_text(
        json.dumps(
            {
                "material_id": "demo-candidate",
                "co2_uptake_mmol_g": 5.1,
                "n2_uptake_mmol_g": 0.1,
                "co2_n2_selectivity": 51.0,
                "heat_of_adsorption_kj_mol": 41.0,
                "surface_area_m2_g": 1210.0,
                "pore_volume_cm3_g": 0.56,
                "density_g_cm3": 0.89,
                "pore_limiting_diameter_a": 4.15,
                "largest_cavity_diameter_a": 6.25,
                "void_fraction": 0.205,
                "temperature_k": 298,
                "co2_pressure_bar": 0.2,
                "n2_pressure_bar": 1.0,
                "force_field": "UFF",
                "charge_method": "DDEC",
                "evidence_type": "user_supplied_candidate_claim",
                "simulation_method": "unknown_candidate_source",
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
            "--candidate-dir",
            str(candidate_dir),
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

    assert "Virtual lab demo complete." in completed.stdout
    summary = pd.read_csv(output_dir / "demo_summary.csv")
    index = (output_dir / "demo_index.md").read_text(encoding="utf-8")
    report = (output_dir / "demo" / "candidate_review_report.md").read_text(encoding="utf-8")
    assert summary["material_id"].tolist() == ["demo-candidate"]
    assert "final_decision" in summary.columns
    assert "Evidence labels:" in index
    assert "Virtual Lab Assessment" in report
    assert (output_dir / "demo" / "candidate_assessment_summary.json").exists()
