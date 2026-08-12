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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    neighbors_path = args.output_dir / "nearest_neighbors.csv"
    summary_path = args.output_dir / "candidate_similarity_summary.json"
    report_path = args.output_dir / "candidate_review_report.md"
    result.neighbor_records.to_csv(neighbors_path, index=False)
    summary_path.write_text(json.dumps(result.prediction_summary, indent=2), encoding="utf-8")
    report_path.write_text(
        build_markdown_report(candidate, result.prediction_summary, result.neighbor_records),
        encoding="utf-8",
    )

    candidate_id = candidate.get("material_id", "unidentified candidate")
    print(f"Candidate: {candidate_id}")
    print(f"Predicted review class: {result.prediction_summary['predicted_candidate_class']}")
    print(f"R&D recommendation: {result.prediction_summary['rd_recommendation']}")
    print(f"Recommendation reason: {result.prediction_summary['rd_recommendation_reason']}")
    print(f"Benchmark verdict: {result.prediction_summary['benchmark_verdict']}")
    print(f"Neighbor advantage: {result.prediction_summary['neighbor_advantage_verdict']}")
    print(f"Confidence: {result.prediction_summary['prediction_confidence']}")
    print(f"Nearest distance: {result.prediction_summary['nearest_distance']}")
    print("Next experiment steps:")
    for step in result.prediction_summary["next_experiment_steps"][:2]:
        print(f"  - [{step['priority']}] {step['action']}: {step['reason']}")
    for warning in result.prediction_summary["warnings"]:
        print(f"Warning: {warning}")
    print(f"Wrote {display_path(neighbors_path)}")
    print(f"Wrote {display_path(summary_path)}")
    print(f"Wrote {display_path(report_path)}")


if __name__ == "__main__":
    main()
