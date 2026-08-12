"""Evaluate an unfamiliar MOF candidate against known screening records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.ml_triage import triage_unfamiliar_candidate
from carbonsense.property_prediction import predict_candidate_properties


DEFAULT_REFERENCE = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_CANDIDATE = PROJECT_ROOT / "data" / "sample_unfamiliar_candidate.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "unfamiliar_candidate_triage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare one unfamiliar MOF candidate with known ranked records using similarity triage."
    )
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE, help="Known ranked records CSV.")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE, help="Candidate descriptor JSON file.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder.")
    parser.add_argument("--k", type=int, default=5, help="Number of nearest known records to inspect.")
    return parser.parse_args()


def load_candidate(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Candidate JSON file does not exist: {path}")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict):
        raise SystemExit("Candidate JSON must contain one object with descriptor fields.")
    return candidate


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _format_metric_table(metrics: dict[str, object]) -> list[str]:
    lines = [
        "| Metric | Candidate | Reference median | Percentile / status |",
        "| --- | ---: | ---: | --- |",
    ]
    if not metrics:
        return lines + ["| No benchmarkable metrics |  |  |  |"]
    for metric, raw_detail in metrics.items():
        detail = raw_detail if isinstance(raw_detail, dict) else {}
        status = detail.get("target_status", detail.get("percentile_rank", ""))
        lines.append(
            "| {metric} | {candidate} | {median} | {status} |".format(
                metric=metric,
                candidate=detail.get("candidate_value", ""),
                median=detail.get("reference_median", ""),
                status=status,
            )
        )
    return lines


def _format_neighbor_comparison_table(comparisons: dict[str, object]) -> list[str]:
    lines = [
        "| Metric | Candidate | Neighbor median | Delta | Interpretation |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    if not comparisons:
        return lines + ["| No neighbor comparison available |  |  |  |  |"]
    for metric, raw_detail in comparisons.items():
        detail = raw_detail if isinstance(raw_detail, dict) else {}
        lines.append(
            "| {metric} | {candidate} | {median} | {delta} | {interpretation} |".format(
                metric=metric,
                candidate=detail.get("candidate_value", ""),
                median=detail.get("neighbor_median", ""),
                delta=detail.get("delta_vs_neighbor_median", ""),
                interpretation=detail.get("interpretation", ""),
            )
        )
    return lines


def _format_property_prediction_table(
    predicted_properties: dict[str, float | None],
    prediction_summary: dict[str, object],
) -> list[str]:
    lines = [
        "| Target | Descriptor-predicted value | Training records | Test MAE | Test R2 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    if not predicted_properties:
        return lines + ["| No property predictions available |  |  |  |  |"]
    target_summaries = prediction_summary.get("target_summaries", {})
    for target, value in predicted_properties.items():
        detail = target_summaries.get(target, {}) if isinstance(target_summaries, dict) else {}
        lines.append(
            "| {target} | {value} | {training_records} | {test_mae} | {test_r2} |".format(
                target=target,
                value="not predicted" if value is None else value,
                training_records=detail.get("training_records", 0),
                test_mae=detail.get("test_mae", ""),
                test_r2=detail.get("test_r2", ""),
            )
        )
    return lines


def _format_dataframe_table(frame: pd.DataFrame, columns: list[str], limit: int = 10) -> list[str]:
    if frame.empty or not columns:
        return ["No nearest-neighbor records were available."]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame[columns].head(limit).iterrows():
        values = [str(row.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def build_markdown_report(
    candidate: dict[str, object],
    summary: dict[str, object],
    neighbors: pd.DataFrame,
    predicted_properties: dict[str, float | None] | None = None,
    property_prediction_summary: dict[str, object] | None = None,
) -> str:
    candidate_id = candidate.get("material_id", "unidentified candidate")
    lines = [
        "# Candidate Review Report",
        "",
        f"Candidate: `{candidate_id}`",
        "",
        "## Verdict",
        "",
        f"- Predicted review class: `{summary['predicted_candidate_class']}`",
        f"- R&D recommendation: `{summary['rd_recommendation']}`",
        f"- Recommendation reason: {summary['rd_recommendation_reason']}",
        f"- Benchmark verdict: `{summary['benchmark_verdict']}`",
        f"- Neighbor advantage: `{summary['neighbor_advantage_verdict']}`",
        f"- Confidence: `{summary['prediction_confidence']}`",
        f"- Nearest distance: `{summary['nearest_distance']}`",
        "",
        "## Metric Benchmarks",
        "",
    ]
    lines.extend(_format_metric_table(summary.get("metric_benchmarks", {})))
    if predicted_properties is not None and property_prediction_summary is not None:
        lines.extend(["", "## Descriptor-Predicted Properties", ""])
        lines.extend(_format_property_prediction_table(predicted_properties, property_prediction_summary))
        lines.extend(
            [
                "",
                f"- Prediction method: `{property_prediction_summary['method']}`",
                f"- Feature policy: {property_prediction_summary['feature_policy']}",
                f"- Candidate supplied descriptors: `{property_prediction_summary['candidate_descriptor_count']}` / `{property_prediction_summary['candidate_descriptor_required_count']}`",
            ]
        )
    coverage = summary.get("descriptor_coverage", {})
    lines.extend(
        [
            "",
            "## Descriptor Coverage",
            "",
            f"- Candidate supplied descriptors: `{coverage.get('candidate_supplied_count', 0)}` / `{coverage.get('candidate_required_count', 0)}`",
            f"- Reference rows with any descriptor: `{coverage.get('reference_rows_with_any_descriptor', 0)}` / `{coverage.get('reference_record_count', 0)}`",
            f"- Reference rows with all descriptors: `{coverage.get('reference_rows_with_all_descriptors', 0)}` / `{coverage.get('reference_record_count', 0)}`",
        ]
    )
    missing = coverage.get("candidate_missing_descriptors", [])
    if missing:
        lines.append("- Missing candidate descriptors: `" + "`, `".join(missing) + "`")
    lines.extend(["", "## Neighbor Comparison", ""])
    lines.extend(_format_neighbor_comparison_table(summary.get("neighbor_metric_comparison", {})))
    lines.extend(["", "## Nearest Neighbors", ""])

    neighbor_columns = [
        column
        for column in (
            "material_id",
            "rule_candidate_class",
            "similarity_distance",
            "similarity_weight",
            "co2_uptake_mmol_g",
            "co2_n2_selectivity",
            "heat_of_adsorption_kj_mol",
        )
        if column in neighbors.columns
    ]
    if neighbor_columns:
        lines.extend(_format_dataframe_table(neighbors, neighbor_columns))
    else:
        lines.append("No nearest-neighbor records were available.")

    lines.extend(["", "## Next Experiment Steps", ""])
    for step in summary.get("next_experiment_steps", []):
        lines.append(f"- `{step['priority']}` `{step['action']}`: {step['reason']}")
    if not summary.get("next_experiment_steps"):
        lines.append("- No next steps generated.")

    lines.extend(["", "## Warnings And Limitations", ""])
    warnings = summary.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- No candidate-specific warnings were generated.")
    if property_prediction_summary is not None:
        for warning in property_prediction_summary.get("warnings", []):
            lines.append(f"- Property prediction: {warning}")
        lines.append(f"- {property_prediction_summary['official_use_policy']}")
    lines.append(f"- {summary['official_use_policy']}")
    lines.append("- This report is a computational review aid, not proof of experimental viability.")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    reference_path = args.reference.resolve()
    candidate_path = args.candidate.resolve()
    if not reference_path.exists():
        raise SystemExit(f"Reference records CSV does not exist: {reference_path}")

    reference_frame = pd.read_csv(reference_path)
    candidate = load_candidate(candidate_path)
    result = triage_unfamiliar_candidate(reference_frame, candidate, k=args.k)
    property_result = predict_candidate_properties(reference_frame, candidate)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    neighbors_path = args.output_dir / "nearest_neighbors.csv"
    summary_path = args.output_dir / "candidate_similarity_summary.json"
    predicted_properties_path = args.output_dir / "predicted_properties.json"
    property_summary_path = args.output_dir / "property_prediction_summary.json"
    report_path = args.output_dir / "candidate_review_report.md"
    result.neighbor_records.to_csv(neighbors_path, index=False)
    summary_path.write_text(json.dumps(result.prediction_summary, indent=2), encoding="utf-8")
    predicted_properties_path.write_text(json.dumps(property_result.predicted_properties, indent=2), encoding="utf-8")
    property_summary_path.write_text(json.dumps(property_result.prediction_summary, indent=2), encoding="utf-8")
    report_path.write_text(
        build_markdown_report(
            candidate,
            result.prediction_summary,
            result.neighbor_records,
            property_result.predicted_properties,
            property_result.prediction_summary,
        ),
        encoding="utf-8",
    )

    candidate_id = candidate.get("material_id", "unidentified candidate")
    print(f"Candidate: {candidate_id}")
    print(f"Predicted review class: {result.prediction_summary['predicted_candidate_class']}")
    print(f"R&D recommendation: {result.prediction_summary['rd_recommendation']}")
    print(f"Recommendation reason: {result.prediction_summary['rd_recommendation_reason']}")
    print(f"Benchmark verdict: {result.prediction_summary['benchmark_verdict']}")
    print(f"Neighbor advantage: {result.prediction_summary['neighbor_advantage_verdict']}")
    print("Descriptor-predicted properties:")
    for target, value in property_result.predicted_properties.items():
        print(f"  {target}: {'not predicted' if value is None else value}")
    coverage = result.prediction_summary["descriptor_coverage"]
    print(
        "Descriptor coverage: "
        f"{coverage['candidate_supplied_count']}/{coverage['candidate_required_count']} candidate descriptors, "
        f"{coverage['reference_rows_with_any_descriptor']}/{coverage['reference_record_count']} reference rows with descriptors"
    )
    print(f"Confidence: {result.prediction_summary['prediction_confidence']}")
    print(f"Nearest distance: {result.prediction_summary['nearest_distance']}")
    print("Next experiment steps:")
    for step in result.prediction_summary["next_experiment_steps"][:2]:
        print(f"  - [{step['priority']}] {step['action']}: {step['reason']}")
    for warning in result.prediction_summary["warnings"]:
        print(f"Warning: {warning}")
    for warning in property_result.prediction_summary.get("warnings", []):
        print(f"Property prediction warning: {warning}")
    print(f"Wrote {display_path(neighbors_path)}")
    print(f"Wrote {display_path(summary_path)}")
    print(f"Wrote {display_path(predicted_properties_path)}")
    print(f"Wrote {display_path(property_summary_path)}")
    print(f"Wrote {display_path(report_path)}")


if __name__ == "__main__":
    main()
