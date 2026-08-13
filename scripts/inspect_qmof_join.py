"""Inspect exact identifier overlap between CRAFTED and QMOF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QMOF_CSV = PROJECT_ROOT / "data" / "raw" / "qmof" / "qmof_database" / "qmof.csv"
DEFAULT_QMOF_METADATA = PROJECT_ROOT / "data" / "raw" / "qmof_figshare_article.json"
DEFAULT_CRAFTED_GEOMETRIC = (
    PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1" / "RAC_DBSCAN" / "CRAFTED_MOF_geometric.csv"
)
DEFAULT_RANKED_RECORDS = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "qmof_join_inspection"

QMOF_USECOLS = [
    "qmof_id",
    "name",
    "info.mofid.mofid",
    "info.mofid.mofkey",
    "info.mofid.topology",
    "info.pld",
    "info.lcd",
    "info.density",
    "info.volume",
    "info.synthesized",
    "info.source",
    "info.doi",
    "outputs.pbe.bandgap",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect QMOF join coverage for local CRAFTED identifiers.")
    parser.add_argument("--qmof-csv", type=Path, default=DEFAULT_QMOF_CSV)
    parser.add_argument("--qmof-metadata", type=Path, default=DEFAULT_QMOF_METADATA)
    parser.add_argument("--crafted-geometric", type=Path, default=DEFAULT_CRAFTED_GEOMETRIC)
    parser.add_argument("--ranked-records", type=Path, default=DEFAULT_RANKED_RECORDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def normalize_qmof_name(name: object) -> str | None:
    if pd.isna(name):
        return None
    text = str(name).strip()
    if not text:
        return None
    if text.endswith("_FSR"):
        return text.removesuffix("_FSR")
    return text


def load_qmof_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"QMOF CSV not found: {path}")
    frame = pd.read_csv(path, usecols=QMOF_USECOLS)
    frame["normalized_name"] = frame["name"].map(normalize_qmof_name)
    frame["join_method"] = frame.apply(
        lambda row: "name_strip_FSR" if row["normalized_name"] != row["name"] else "name_exact",
        axis=1,
    )
    return frame


def load_geometric_ids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"CRAFTED geometric descriptor file not found: {path}")
    frame = pd.read_csv(path, usecols=["FrameworkName"])
    return set(frame["FrameworkName"].dropna().astype(str).str.strip())


def load_ranked_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    frame = pd.read_csv(path, usecols=["material_id"])
    return set(frame["material_id"].dropna().astype(str).str.strip())


def load_figshare_metadata(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_overlap(source_ids: set[str], target_ids: set[str]) -> dict[str, object]:
    matched = sorted(source_ids & target_ids)
    missing = sorted(source_ids - target_ids)
    return {
        "source_count": len(source_ids),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "match_fraction": round(len(matched) / len(source_ids), 4) if source_ids else 0.0,
        "matched_examples": matched[:10],
        "missing_examples": missing[:10],
    }


def build_matched_descriptor_slice(qmof: pd.DataFrame, target_ids: set[str]) -> pd.DataFrame:
    matched = qmof[qmof["normalized_name"].isin(target_ids)].copy()
    return matched[
        [
            "normalized_name",
            "qmof_id",
            "name",
            "join_method",
            "info.source",
            "info.synthesized",
            "info.mofid.mofid",
            "info.mofid.mofkey",
            "info.mofid.topology",
            "info.pld",
            "info.lcd",
            "info.density",
            "info.volume",
            "outputs.pbe.bandgap",
            "info.doi",
        ]
    ].sort_values(["normalized_name", "qmof_id"])


def build_report(summary: dict[str, object]) -> str:
    lines = [
        "# QMOF Join Inspection",
        "",
        "This report checks conservative identifier overlap only. It does not claim structural identity beyond a controlled name match.",
        "",
        "## Source",
        "",
        f"- Figshare DOI: `{summary['figshare_doi']}`",
        f"- Figshare version: `{summary['figshare_version']}`",
        f"- License: `{summary['figshare_license']}`",
        "",
        "## Counts",
        "",
        f"- QMOF rows: `{summary['qmof_row_count']}`",
        f"- QMOF unique names: `{summary['qmof_name_count']}`",
        f"- QMOF `_FSR` names: `{summary['qmof_fsr_name_count']}`",
        f"- CRAFTED geometric FrameworkName IDs: `{summary['crafted_geometric_id_count']}`",
        f"- Ranked material IDs: `{summary['ranked_id_count']}`",
        "",
        "## Exact Overlap",
        "",
    ]
    for key, title in (
        ("qmof_raw_name_to_crafted_geometric", "QMOF raw `name` -> CRAFTED geometric `FrameworkName`"),
        ("qmof_normalized_name_to_crafted_geometric", "QMOF normalized `name` -> CRAFTED geometric `FrameworkName`"),
        ("qmof_normalized_name_to_ranked", "QMOF normalized `name` -> current ranked material IDs"),
    ):
        detail = summary[key]
        lines.extend(
            [
                f"### {title}",
                "",
                f"- source count: `{detail['source_count']}`",
                f"- matched count: `{detail['matched_count']}`",
                f"- missing count: `{detail['missing_count']}`",
                f"- match fraction: `{detail['match_fraction']}`",
                f"- matched examples: `{', '.join(detail['matched_examples'])}`",
                f"- missing examples: `{', '.join(detail['missing_examples'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "QMOF is useful as a descriptor-enrichment source, but it is not as clean a first join target as CoRE MOF 2014.",
            "The only normalization currently allowed is stripping a QMOF terminal `_FSR` suffix from CSD-source names.",
            "Do not use QMOF `qmof_id` as a CRAFTED join key because it is QMOF-specific.",
            "",
            "## Join Policy",
            "",
            "```text",
            "join QMOF to CRAFTED only by CSD-style name after controlled _FSR stripping",
            "do not fuzzy-match QMOF names",
            "keep QMOF DFT/geometric descriptors separate from CRAFTED adsorption metrics",
            "mark missing QMOF descriptors explicitly",
            "prefer CoRE 2014 for the first descriptor integration; use QMOF as a later enrichment layer",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def inspect_join(
    qmof_csv: Path,
    qmof_metadata: Path,
    crafted_geometric: Path,
    ranked_records: Path,
) -> tuple[dict[str, object], pd.DataFrame]:
    qmof = load_qmof_frame(qmof_csv)
    geometric_ids = load_geometric_ids(crafted_geometric)
    ranked_ids = load_ranked_ids(ranked_records)
    metadata = load_figshare_metadata(qmof_metadata)
    license_info = metadata.get("license", {})
    raw_names = set(qmof["name"].dropna().astype(str).str.strip())
    normalized_names = set(qmof["normalized_name"].dropna().astype(str).str.strip())
    matched_descriptors = build_matched_descriptor_slice(qmof, geometric_ids)
    summary = {
        "qmof_csv": str(qmof_csv),
        "qmof_metadata": str(qmof_metadata) if qmof_metadata.exists() else None,
        "crafted_geometric": str(crafted_geometric),
        "ranked_records": str(ranked_records) if ranked_records.exists() else None,
        "figshare_doi": metadata.get("doi"),
        "figshare_version": metadata.get("version"),
        "figshare_modified_date": metadata.get("modified_date"),
        "figshare_license": license_info.get("name") if isinstance(license_info, dict) else None,
        "qmof_row_count": len(qmof),
        "qmof_name_count": len(raw_names),
        "qmof_normalized_name_count": len(normalized_names),
        "qmof_fsr_name_count": int(qmof["name"].dropna().astype(str).str.endswith("_FSR").sum()),
        "crafted_geometric_id_count": len(geometric_ids),
        "ranked_id_count": len(ranked_ids),
        "qmof_raw_name_to_crafted_geometric": summarize_overlap(raw_names, geometric_ids),
        "qmof_normalized_name_to_crafted_geometric": summarize_overlap(normalized_names, geometric_ids),
        "qmof_normalized_name_to_ranked": summarize_overlap(normalized_names, ranked_ids),
        "matched_descriptor_row_count": len(matched_descriptors),
        "matched_source_counts": matched_descriptors["info.source"].value_counts(dropna=False).to_dict(),
        "join_policy": "controlled_name_match_only; strip terminal _FSR only; do not fuzzy-match",
    }
    return summary, matched_descriptors


def main() -> None:
    args = parse_args()
    summary, matched_descriptors = inspect_join(
        args.qmof_csv.resolve(),
        args.qmof_metadata.resolve(),
        args.crafted_geometric.resolve(),
        args.ranked_records.resolve(),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "join_summary.json"
    report_path = args.output_dir / "join_summary.md"
    descriptors_path = args.output_dir / "matched_qmof_descriptors.csv"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(build_report(summary), encoding="utf-8")
    matched_descriptors.to_csv(descriptors_path, index=False)
    print("QMOF join inspection complete.")
    print(
        "QMOF normalized name -> CRAFTED geometric match fraction: "
        f"{summary['qmof_normalized_name_to_crafted_geometric']['match_fraction']}"
    )
    print(f"Matched descriptor rows: {summary['matched_descriptor_row_count']}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {descriptors_path}")


if __name__ == "__main__":
    sys.exit(main())
