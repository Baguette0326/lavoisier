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
    result.neighbor_records.to_csv(neighbors_path, index=False)
    summary_path.write_text(json.dumps(result.prediction_summary, indent=2), encoding="utf-8")

    candidate_id = candidate.get("material_id", "unidentified candidate")
    print(f"Candidate: {candidate_id}")
    print(f"Predicted review class: {result.prediction_summary['predicted_candidate_class']}")
    print(f"Confidence: {result.prediction_summary['prediction_confidence']}")
    print(f"Nearest distance: {result.prediction_summary['nearest_distance']}")
    for warning in result.prediction_summary["warnings"]:
        print(f"Warning: {warning}")
    print(f"Wrote {display_path(neighbors_path)}")
    print(f"Wrote {display_path(summary_path)}")


if __name__ == "__main__":
    main()
