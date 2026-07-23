"""Run CarbonSense's backend pipeline on the synthetic CRAFTED-like fixture."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.pipeline import export_result, run_fixture_pipeline


def main() -> None:
    fixture_path = PROJECT_ROOT / "data" / "crafted_like_fixture.csv"
    result = run_fixture_pipeline(fixture_path)
    output_paths = export_result(result, PROJECT_ROOT / "reports" / "backend_fixture_export")
    print(f"Input records: {len(result.input_records)}")
    print(f"Controlled slice records: {len(result.controlled_slice)}")
    print(f"Excluded by slice: {len(result.excluded_records)}")
    print(f"Ranked records: {len(result.ranked_records)}")
    print(f"Blocked records: {result.metadata.blocked_count}")
    for path in output_paths:
        print(f"Wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
