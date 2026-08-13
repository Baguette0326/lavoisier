"""Evaluate whether CoRE-enriched descriptors improve property prediction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.property_prediction import evaluate_property_prediction_feature_sets  # noqa: E402


DEFAULT_REFERENCE = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "descriptor_feature_set_evaluation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline vs CoRE-enriched descriptor prediction quality.")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def build_markdown_report(result: dict[str, object]) -> str:
    comparison = result["comparison_summary"]
    target_comparisons = comparison["target_comparisons"]
    lines = [
        "# Descriptor Feature Set Evaluation",
        "",
        f"Method: `{comparison['method']}`",
        "",
        "| Target | Status | Baseline MAE | CoRE+Baseline MAE | MAE delta | Baseline R2 | CoRE+Baseline R2 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for target, detail in target_comparisons.items():
        lines.append(
            "| {target} | {status} | {baseline_mae} | {candidate_mae} | {delta} | {baseline_r2} | {candidate_r2} |".format(
                target=target,
                status=detail["status"],
                baseline_mae=detail["baseline_test_mae"],
                candidate_mae=detail["candidate_test_mae"],
                delta=detail["mae_delta_candidate_minus_baseline"],
                baseline_r2=detail.get("baseline_test_r2"),
                candidate_r2=detail.get("candidate_test_r2"),
            )
        )

    lines.extend(
        [
            "",
            "## Feature Sets",
            "",
            f"- Baseline: `{comparison['baseline_feature_set']}`",
            f"- Candidate: `{comparison['candidate_feature_set']}`",
            "",
            "## Use Policy",
            "",
            f"- {comparison['use_policy']}",
            "- This evaluates prediction quality within the current controlled CRAFTED slice only.",
            "- Improvement here does not prove experimental validity or transfer to other conditions.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    reference_path = args.reference.resolve()
    if not reference_path.exists():
        raise SystemExit(f"Reference records CSV does not exist: {reference_path}")

    reference_frame = pd.read_csv(reference_path)
    result = evaluate_property_prediction_feature_sets(reference_frame)
    payload = {
        "target_results": result.target_results,
        "comparison_summary": result.comparison_summary,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "descriptor_feature_set_evaluation.json"
    report_path = args.output_dir / "descriptor_feature_set_evaluation.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_path.write_text(build_markdown_report(payload), encoding="utf-8")

    print("Descriptor feature-set evaluation complete.")
    for target, detail in result.comparison_summary["target_comparisons"].items():
        print(
            f"{target}: {detail['status']} "
            f"(baseline MAE={detail['baseline_test_mae']}, CoRE+baseline MAE={detail['candidate_test_mae']})"
        )
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
