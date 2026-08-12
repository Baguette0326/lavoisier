"""Predict adsorption properties for one unfamiliar MOF candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.property_prediction import predict_candidate_properties


DEFAULT_REFERENCE = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_CANDIDATE = PROJECT_ROOT / "data" / "sample_unfamiliar_candidate.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "unfamiliar_candidate_property_prediction"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict adsorption properties for one unfamiliar MOF from structural descriptors."
    )
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE, help="Known ranked records CSV.")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE, help="Candidate descriptor JSON file.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder.")
    return parser.parse_args()


def load_candidate(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Candidate JSON file does not exist: {path}")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict):
        raise SystemExit("Candidate JSON must contain one object with descriptor fields.")
    return candidate


def _format_value(value: object) -> str:
    if value is None:
        return "not predicted"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def build_markdown_report(
    candidate: dict[str, object],
    predicted_properties: dict[str, float | None],
    summary: dict[str, object],
) -> str:
    candidate_id = candidate.get("material_id", "unidentified candidate")
    lines = [
        "# Candidate Property Prediction Report",
        "",
        f"Candidate: `{candidate_id}`",
        "",
        "## Predicted Properties",
        "",
        "| Target | Predicted value | Training records | Test MAE | Test R2 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    target_summaries = summary.get("target_summaries", {})
    for target, value in predicted_properties.items():
        detail = target_summaries.get(target, {}) if isinstance(target_summaries, dict) else {}
        lines.append(
            "| {target} | {value} | {training_records} | {test_mae} | {test_r2} |".format(
                target=target,
                value=_format_value(value),
                training_records=detail.get("training_records", 0),
                test_mae=_format_value(detail.get("test_mae")),
                test_r2=_format_value(detail.get("test_r2")),
            )
        )

    lines.extend(
        [
            "",
            "## Model",
            "",
            f"- Method: `{summary['method']}`",
            f"- Feature policy: {summary['feature_policy']}",
            "- Feature columns: `" + "`, `".join(summary.get("feature_columns", [])) + "`",
            f"- Candidate supplied descriptors: `{summary['candidate_descriptor_count']}` / `{summary['candidate_descriptor_required_count']}`",
            "",
            "## Warnings And Limitations",
            "",
        ]
    )
    warnings = summary.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- No candidate-specific warnings were generated.")
    lines.append(f"- {summary['official_use_policy']}")
    lines.append("- Use this as an R&D triage estimate, not as proof of material viability.")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    reference_path = args.reference.resolve()
    candidate_path = args.candidate.resolve()
    if not reference_path.exists():
        raise SystemExit(f"Reference records CSV does not exist: {reference_path}")

    reference_frame = pd.read_csv(reference_path)
    candidate = load_candidate(candidate_path)
    result = predict_candidate_properties(reference_frame, candidate)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "predicted_properties.json"
    summary_path = args.output_dir / "property_prediction_summary.json"
    report_path = args.output_dir / "property_prediction_report.md"
    predictions_path.write_text(json.dumps(result.predicted_properties, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(result.prediction_summary, indent=2), encoding="utf-8")
    report_path.write_text(
        build_markdown_report(candidate, result.predicted_properties, result.prediction_summary),
        encoding="utf-8",
    )

    candidate_id = candidate.get("material_id", "unidentified candidate")
    print(f"Candidate: {candidate_id}")
    print("Predicted properties:")
    for target, value in result.predicted_properties.items():
        print(f"  {target}: {_format_value(value)}")
    print(
        "Descriptor coverage: "
        f"{result.prediction_summary['candidate_descriptor_count']}/"
        f"{result.prediction_summary['candidate_descriptor_required_count']} candidate descriptors"
    )
    warnings = result.prediction_summary.get("warnings", [])
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    print(f"Wrote: {predictions_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()
