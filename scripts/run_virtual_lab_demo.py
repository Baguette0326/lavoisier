"""Run the local virtual-lab demo over synthetic candidate examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.ml_triage import triage_unfamiliar_candidate
from carbonsense.property_prediction import predict_candidate_properties
from carbonsense.virtual_lab import synthesize_candidate_assessment

from evaluate_unfamiliar_candidate import build_markdown_report


DEFAULT_REFERENCE = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_CANDIDATE_DIR = PROJECT_ROOT / "data" / "demo_candidates"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "virtual_lab_demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lavoisier virtual-lab backend demo.")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE, help="Known ranked records CSV.")
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR, help="Folder of candidate JSON files.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Demo output folder.")
    parser.add_argument("--k", type=int, default=5, help="Nearest-neighbor count.")
    return parser.parse_args()


def load_candidate(path: Path) -> dict[str, object]:
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict):
        raise ValueError(f"Candidate file must contain one JSON object: {path}")
    return candidate


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _candidate_output_dir(output_dir: Path, candidate_path: Path) -> Path:
    return output_dir / candidate_path.stem


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _write_demo_index(output_dir: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Lavoisier Virtual Lab Demo",
        "",
        "Synthetic demo candidates only. These are not research findings.",
        "",
        "| Candidate | Final decision | Viability read | Better-than-known read | Report |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        report_path = Path(str(row["report_path"]))
        lines.append(
            "| {candidate} | `{decision}` | `{viability}` | `{better}` | [{report}]({report}) |".format(
                candidate=row["material_id"],
                decision=row["final_decision"],
                viability=row["viability_read"],
                better=row["better_than_known_reference"],
                report=report_path.as_posix(),
            )
        )
    lines.extend(
        [
            "",
            "Evidence labels:",
            "",
            "- Reference adsorption records are CRAFTED-derived GCMC simulation outputs.",
            "- Demo candidate metrics are user-supplied synthetic claims.",
            "- Descriptor-predicted properties are ML estimates from structural descriptors.",
            "- Virtual-lab decisions are triage recommendations, not proof of experimental viability.",
        ]
    )
    (output_dir / "demo_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_demo(reference_path: Path, candidate_dir: Path, output_dir: Path, k: int) -> list[dict[str, object]]:
    if not reference_path.exists():
        raise SystemExit(
            f"Reference records CSV does not exist: {reference_path}\n"
            "Run scripts/run_crafted_real_slice.py first, or pass --reference to an existing ranked_records.csv."
        )
    if not candidate_dir.exists():
        raise SystemExit(f"Candidate folder does not exist: {candidate_dir}")

    reference_frame = pd.read_csv(reference_path)
    candidate_paths = sorted(candidate_dir.glob("*.json"))
    if not candidate_paths:
        raise SystemExit(f"No candidate JSON files found in: {candidate_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for candidate_path in candidate_paths:
        candidate = load_candidate(candidate_path)
        candidate_id = str(candidate.get("material_id", candidate_path.stem))
        candidate_output = _candidate_output_dir(output_dir, candidate_path)
        candidate_output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate_path, candidate_output / "candidate_input.json")

        similarity_result = triage_unfamiliar_candidate(reference_frame, candidate, k=k)
        property_result = predict_candidate_properties(reference_frame, candidate)
        assessment_result = synthesize_candidate_assessment(
            similarity_result.prediction_summary,
            property_result.prediction_summary,
        )

        neighbors_path = candidate_output / "nearest_neighbors.csv"
        similarity_path = candidate_output / "candidate_similarity_summary.json"
        predictions_path = candidate_output / "predicted_properties.json"
        property_path = candidate_output / "property_prediction_summary.json"
        assessment_path = candidate_output / "candidate_assessment_summary.json"
        report_path = candidate_output / "candidate_review_report.md"

        similarity_result.neighbor_records.to_csv(neighbors_path, index=False)
        _write_json(similarity_path, similarity_result.prediction_summary)
        _write_json(predictions_path, property_result.predicted_properties)
        _write_json(property_path, property_result.prediction_summary)
        _write_json(assessment_path, assessment_result.assessment_summary)
        report_path.write_text(
            build_markdown_report(
                candidate,
                similarity_result.prediction_summary,
                similarity_result.neighbor_records,
                property_result.predicted_properties,
                property_result.prediction_summary,
                assessment_result.assessment_summary,
            ),
            encoding="utf-8",
        )

        row = {
            "candidate_file": candidate_path.name,
            "material_id": candidate_id,
            "final_decision": assessment_result.assessment_summary["final_decision"],
            "viability_read": assessment_result.assessment_summary["viability_read"],
            "better_than_known_reference": assessment_result.assessment_summary["better_than_known_reference"],
            "review_confidence": assessment_result.assessment_summary["review_confidence"],
            "report_path": _display_path(report_path),
        }
        rows.append(row)

    pd.DataFrame(rows).to_csv(output_dir / "demo_summary.csv", index=False)
    _write_demo_index(output_dir, rows)
    return rows


def main() -> None:
    args = parse_args()
    rows = run_demo(args.reference.resolve(), args.candidate_dir.resolve(), args.output_dir.resolve(), args.k)
    print("Virtual lab demo complete.")
    for row in rows:
        print(
            "{candidate}: {decision} ({viability})".format(
                candidate=row["material_id"],
                decision=row["final_decision"],
                viability=row["viability_read"],
            )
        )
    print(f"Wrote {_display_path(args.output_dir.resolve() / 'demo_summary.csv')}")
    print(f"Wrote {_display_path(args.output_dir.resolve() / 'demo_index.md')}")


if __name__ == "__main__":
    main()
