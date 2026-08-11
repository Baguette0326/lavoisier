"""Run weakly supervised ML candidate triage on a local ranked slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.ml_triage import classify_candidates


DEFAULT_INPUT = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "crafted_ml_triage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify candidates using weakly supervised ML triage.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Ranked records CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.exists():
        raise SystemExit(f"Input ranked records file does not exist: {input_path}")

    frame = pd.read_csv(input_path)
    result = classify_candidates(frame)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    classified_path = args.output_dir / "classified_records.csv"
    summary_path = args.output_dir / "ml_triage_summary.json"
    result.classified_records.to_csv(classified_path, index=False)
    summary_path.write_text(json.dumps(result.training_summary, indent=2), encoding="utf-8")

    print(f"Input records: {len(frame)}")
    print(f"Classified records: {len(result.classified_records)}")
    print("Rule-derived class counts:")
    for label, count in result.training_summary["class_counts"].items():
        print(f"  {label}: {count}")
    print(f"Wrote {classified_path.resolve().relative_to(PROJECT_ROOT)}")
    print(f"Wrote {summary_path.resolve().relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
