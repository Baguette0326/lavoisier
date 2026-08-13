"""Inspect exact identifier overlap between CRAFTED and CoRE MOF 2014 DDEC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tarfile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORE_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "core_mof_2014" / "core-mof-1.0-ddec.tar"
DEFAULT_CRAFTED_CIF_DIR = PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1" / "CIF_FILES" / "DDEC"
DEFAULT_CRAFTED_GEOMETRIC = (
    PROJECT_ROOT / "data" / "raw" / "crafted_2_0_1" / "CRAFTED-2.0.1" / "RAC_DBSCAN" / "CRAFTED_MOF_geometric.csv"
)
DEFAULT_RANKED_RECORDS = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "core_mof_2014_join_inspection"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect CoRE MOF 2014 join coverage for local CRAFTED identifiers.")
    parser.add_argument("--core-archive", type=Path, default=DEFAULT_CORE_ARCHIVE)
    parser.add_argument("--crafted-cif-dir", type=Path, default=DEFAULT_CRAFTED_CIF_DIR)
    parser.add_argument("--crafted-geometric", type=Path, default=DEFAULT_CRAFTED_GEOMETRIC)
    parser.add_argument("--ranked-records", type=Path, default=DEFAULT_RANKED_RECORDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def normalize_core_id(path: str) -> str | None:
    name = Path(path).name
    if not name.endswith(".cif") or name.startswith("._"):
        return None
    stem = Path(name).stem
    if stem.endswith("_clean"):
        stem = stem.removesuffix("_clean")
    return stem.strip()


def load_core_ids(archive_path: Path) -> set[str]:
    if not archive_path.exists():
        raise FileNotFoundError(f"CoRE MOF 2014 archive not found: {archive_path}")
    ids: set[str] = set()
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            identifier = normalize_core_id(member.name)
            if identifier:
                ids.add(identifier)
    return ids


def load_crafted_cif_ids(cif_dir: Path) -> set[str]:
    if not cif_dir.exists():
        raise FileNotFoundError(f"CRAFTED CIF folder not found: {cif_dir}")
    return {
        path.stem
        for path in cif_dir.glob("*.cif")
        if path.is_file() and not path.name.startswith("._")
    }


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


def numeric_like_count(ids: set[str]) -> int:
    pattern = re.compile(r"^\d")
    return sum(1 for identifier in ids if pattern.match(identifier))


def build_report(summary: dict[str, object]) -> str:
    lines = [
        "# CoRE MOF 2014 Join Inspection",
        "",
        "This report checks exact identifier overlap only. It does not prove structural identity beyond matching names/refcodes.",
        "",
        "## Counts",
        "",
        f"- CoRE MOF 2014 DDEC IDs: `{summary['core_id_count']}`",
        f"- CRAFTED DDEC CIF IDs: `{summary['crafted_cif_id_count']}`",
        f"- CRAFTED geometric FrameworkName IDs: `{summary['crafted_geometric_id_count']}`",
        f"- Ranked material IDs: `{summary['ranked_id_count']}`",
        "",
        "## Exact Overlap",
        "",
    ]
    for key, title in (
        ("crafted_cif_to_core", "CRAFTED DDEC CIF IDs -> CoRE 2014"),
        ("crafted_geometric_to_core", "CRAFTED geometric FrameworkName -> CoRE 2014"),
        ("ranked_to_core", "Current ranked material IDs -> CoRE 2014"),
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
            "A high exact-match fraction for CRAFTED MOF-style IDs means CoRE MOF 2014 is a realistic descriptor enrichment target.",
            "Numeric-leading CRAFTED IDs are likely outside the CoRE MOF refcode subset and should not be joined by fuzzy matching.",
        ]
    )
    return "\n".join(lines) + "\n"


def inspect_join(
    core_archive: Path,
    crafted_cif_dir: Path,
    crafted_geometric: Path,
    ranked_records: Path,
) -> dict[str, object]:
    core_ids = load_core_ids(core_archive)
    crafted_cif_ids = load_crafted_cif_ids(crafted_cif_dir)
    geometric_ids = load_geometric_ids(crafted_geometric)
    ranked_ids = load_ranked_ids(ranked_records)
    return {
        "core_archive": str(core_archive),
        "crafted_cif_dir": str(crafted_cif_dir),
        "crafted_geometric": str(crafted_geometric),
        "ranked_records": str(ranked_records) if ranked_records.exists() else None,
        "core_id_count": len(core_ids),
        "crafted_cif_id_count": len(crafted_cif_ids),
        "crafted_cif_numeric_like_count": numeric_like_count(crafted_cif_ids),
        "crafted_geometric_id_count": len(geometric_ids),
        "crafted_geometric_numeric_like_count": numeric_like_count(geometric_ids),
        "ranked_id_count": len(ranked_ids),
        "ranked_numeric_like_count": numeric_like_count(ranked_ids),
        "crafted_cif_to_core": summarize_overlap(crafted_cif_ids, core_ids),
        "crafted_geometric_to_core": summarize_overlap(geometric_ids, core_ids),
        "ranked_to_core": summarize_overlap(ranked_ids, core_ids),
        "join_policy": "exact_identifier_match_only; remove CoRE _clean suffix before matching; do not fuzzy-match numeric COF-like IDs",
    }


def main() -> None:
    args = parse_args()
    summary = inspect_join(
        args.core_archive.resolve(),
        args.crafted_cif_dir.resolve(),
        args.crafted_geometric.resolve(),
        args.ranked_records.resolve(),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "join_summary.json"
    report_path = args.output_dir / "join_summary.md"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(build_report(summary), encoding="utf-8")
    print("CoRE MOF 2014 join inspection complete.")
    print(f"CRAFTED geometric -> CoRE match fraction: {summary['crafted_geometric_to_core']['match_fraction']}")
    print(f"Ranked IDs -> CoRE match fraction: {summary['ranked_to_core']['match_fraction']}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
