"""Run Lavoisier's backend pipeline on the local CRAFTED 2.0.1 slice.

This script uses local raw CRAFTED files that are intentionally ignored by Git.
It writes derived outputs to ignored local folders until processed-data sharing
is reviewed separately.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.crafted_adapter import (
    CraftedRealSliceConfig,
    CraftedSliceConfig,
    join_crafted_geometric_descriptors,
    load_crafted_mof_geometric_descriptors,
    parse_crafted_real_slice,
)
from carbonsense.core2014_adapter import join_core2014_enrichment
from carbonsense.pipeline import export_result, run_crafted_screening_pipeline


DEFAULT_ROOT = PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1"
DEFAULT_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1.tar.xz"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "crafted_2_0_1"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "crafted_real_slice_export"
DEFAULT_DESCRIPTOR_FILE = DEFAULT_ROOT / "RAC_DBSCAN" / "CRAFTED_MOF_geometric.csv"
DEFAULT_CORE2014_ENRICHMENT = PROJECT_ROOT / "reports" / "core_mof_2014_enrichment" / "core2014_enrichment.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse and rank the first local CRAFTED 2.0.1 slice.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Extracted CRAFTED 2.0.1 folder.")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE, help="Downloaded CRAFTED archive path.")
    parser.add_argument("--descriptor-file", type=Path, default=DEFAULT_DESCRIPTOR_FILE)
    parser.add_argument("--core2014-enrichment", type=Path, default=DEFAULT_CORE2014_ENRICHMENT)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--limit", type=int, default=None, help="Optional material limit for smoke testing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    archive = args.archive.resolve()
    if not root.exists():
        raise SystemExit(f"Extracted CRAFTED root does not exist: {root}")
    if not archive.exists():
        raise SystemExit(f"CRAFTED archive does not exist: {archive}")

    real_config = CraftedRealSliceConfig()
    long_table, screening, parser_blocked = parse_crafted_real_slice(root, real_config, limit=args.limit)
    descriptor_file = args.descriptor_file.resolve()
    descriptor_match_count = 0
    if descriptor_file.exists() and not screening.empty:
        descriptors = load_crafted_mof_geometric_descriptors(descriptor_file)
        screening = join_crafted_geometric_descriptors(screening, descriptors)
        descriptor_match_count = int(screening["descriptor_match_status"].eq("matched_crafted_mof_geometric").sum())
    core_enrichment_file = args.core2014_enrichment.resolve()
    core_match_count = 0
    if core_enrichment_file.exists() and not screening.empty:
        core_enrichment = pd.read_csv(core_enrichment_file)
        screening = join_core2014_enrichment(screening, core_enrichment)
        core_match_count = int(screening["core_match_status"].eq("matched_core2014").sum())

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    long_path = args.processed_dir / "crafted_isotherm_long.csv"
    screening_path = args.processed_dir / "crafted_screening_slice.csv"
    parser_blocked_path = args.processed_dir / "crafted_parser_blocked_records.csv"
    long_table.to_csv(long_path, index=False)
    screening.to_csv(screening_path, index=False)
    parser_blocked.to_csv(parser_blocked_path, index=False)

    result = run_crafted_screening_pipeline(
        screening,
        slice_config=CraftedSliceConfig(
            force_field=real_config.force_field,
            charge_method=real_config.charge_method,
            temperature_k=real_config.temperature_k,
            co2_pressure_bar=real_config.co2_pressure_bar,
            n2_pressure_bar=real_config.n2_pressure_bar,
        ),
        source_name="CRAFTED 2.0.1 local approved slice",
        source_version=real_config.source_version,
        source_status="local_only_raw_data_not_committed",
        source_file=archive,
    )
    output_paths = export_result(result, args.report_dir)

    print(f"Long records: {len(long_table)}")
    print(f"Screening records: {len(screening)}")
    print(f"Descriptor-matched screening records: {descriptor_match_count}")
    print(f"CoRE-enriched screening records: {core_match_count}")
    print(f"Parser-blocked records: {len(parser_blocked)}")
    print(f"Ranked records: {len(result.ranked_records)}")
    print(f"Backend-blocked records: {result.metadata.blocked_count}")
    for path in (long_path, screening_path, parser_blocked_path, *output_paths):
        print(f"Wrote {path.resolve().relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
