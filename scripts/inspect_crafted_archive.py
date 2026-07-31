"""Inspect a local approved CRAFTED archive before parser work.

This script does not download, approve, ingest, or rank CRAFTED data.
Run it only after completing the CRAFTED approval checklist.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.crafted_inspection import write_inspection_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a local CRAFTED folder or .zip archive.")
    parser.add_argument("source_path", type=Path, help="Approved local CRAFTED folder or .zip archive.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "reports" / "crafted_archive_inspection",
        help="Directory for inspection artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = args.source_path.expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Source path does not exist: {source_path}")
    output_paths = write_inspection_outputs(source_path, args.output_dir)
    print(f"Inspected {source_path}")
    for path in output_paths:
        print(f"Wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
