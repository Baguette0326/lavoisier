"""Export a CoRE MOF 2014 descriptor/provenance enrichment table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.core2014_adapter import (  # noqa: E402
    CORE2014_LICENSE,
    CORE2014_SOURCE_DOI,
    CORE2014_SOURCE_VERSION,
    build_core2014_enrichment,
    load_core2014_records,
    load_crafted_geometric_target_ids,
)


DEFAULT_CORE_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "core_mof_2014" / "core-mof-1.0-ddec.tar"
DEFAULT_CRAFTED_GEOMETRIC = (
    PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1" / "RAC_DBSCAN" / "CRAFTED_MOF_geometric.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "core_mof_2014_enrichment"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CoRE MOF 2014 enrichment for CRAFTED MOF IDs.")
    parser.add_argument("--core-archive", type=Path, default=DEFAULT_CORE_ARCHIVE)
    parser.add_argument("--crafted-geometric", type=Path, default=DEFAULT_CRAFTED_GEOMETRIC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def build_summary(enrichment) -> dict[str, object]:
    matched_count = int(enrichment["core_match_status"].eq("matched_core2014").sum())
    missing_count = int(enrichment["core_match_status"].eq("missing_core2014").sum())
    return {
        "source_version": CORE2014_SOURCE_VERSION,
        "source_doi": CORE2014_SOURCE_DOI,
        "license": CORE2014_LICENSE,
        "target_count": int(len(enrichment)),
        "matched_count": matched_count,
        "missing_count": missing_count,
        "match_fraction": round(matched_count / len(enrichment), 4) if len(enrichment) else 0.0,
        "matched_examples": enrichment.loc[
            enrichment["core_match_status"].eq("matched_core2014"), "material_id"
        ].head(10).tolist(),
        "missing_examples": enrichment.loc[
            enrichment["core_match_status"].eq("missing_core2014"), "material_id"
        ].head(10).tolist(),
        "join_policy": "exact CRAFTED FrameworkName to normalized CoRE CIF filename; strip CoRE terminal _clean only",
        "limitations": [
            "This table provides descriptors/provenance only, not adsorption measurements.",
            "Exact identifier match does not replace structural identity review for publication-grade analysis.",
            "Missing CoRE rows are preserved rather than silently dropped.",
        ],
    }


def main() -> None:
    args = parse_args()
    core_records = load_core2014_records(args.core_archive.resolve())
    target_ids = load_crafted_geometric_target_ids(args.crafted_geometric.resolve())
    enrichment = build_core2014_enrichment(core_records, target_ids)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    enrichment_path = args.output_dir / "core2014_enrichment.csv"
    summary_path = args.output_dir / "core2014_enrichment_summary.json"
    enrichment.to_csv(enrichment_path, index=False)
    summary_path.write_text(json.dumps(build_summary(enrichment), indent=2), encoding="utf-8")

    print("CoRE MOF 2014 enrichment export complete.")
    print(f"Target records: {len(enrichment)}")
    print(f"Matched records: {int(enrichment['core_match_status'].eq('matched_core2014').sum())}")
    print(f"Missing records: {int(enrichment['core_match_status'].eq('missing_core2014').sum())}")
    print(f"Wrote {enrichment_path.resolve().relative_to(PROJECT_ROOT)}")
    print(f"Wrote {summary_path.resolve().relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
