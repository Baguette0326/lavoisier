"""Export reviewable CarbonSense screening results."""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from carbonsense.crafted_adapter import CraftedSliceConfig


@dataclass(frozen=True)
class ScreeningExportMetadata:
    """Metadata needed to reproduce and review a screening export."""

    generated_at: str
    source_name: str
    source_version: str
    source_status: str
    source_file: str | None
    source_checksum_sha256: str | None
    slice_config: dict[str, Any]
    weights: dict[str, float]
    input_record_count: int
    controlled_slice_count: int
    excluded_by_slice_count: int
    rank_eligible_count: int
    blocked_count: int
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class TransformationLog:
    """Lineage receipt for a generated screening export."""

    generated_at: str
    source_file: str | None
    source_name: str
    source_version: str
    license_status: str
    source_checksum_sha256: str | None
    input_row_count: int
    controlled_slice_row_count: int
    excluded_row_count: int
    rank_eligible_row_count: int
    blocked_row_count: int
    filter_applied: dict[str, Any]
    ranking_weights: dict[str, float]
    generated_files: tuple[str, ...]
    transformation_steps: tuple[str, ...]
    limitations: tuple[str, ...]


def calculate_sha256(path: Path) -> str:
    """Return a SHA-256 checksum for a source file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_export_metadata(
    *,
    source_name: str,
    source_version: str,
    source_status: str,
    source_file: Path | None = None,
    source_checksum_sha256: str | None = None,
    slice_config: CraftedSliceConfig,
    weights: dict[str, float],
    input_record_count: int,
    controlled_slice_count: int,
    excluded_by_slice_count: int,
    rank_eligible_count: int,
    blocked_count: int,
    generated_at: datetime | None = None,
) -> ScreeningExportMetadata:
    """Build metadata for a screening export."""
    timestamp = generated_at or datetime.now(UTC)
    return ScreeningExportMetadata(
        generated_at=timestamp.isoformat(),
        source_name=source_name,
        source_version=source_version,
        source_status=source_status,
        source_file=str(source_file) if source_file else None,
        source_checksum_sha256=source_checksum_sha256,
        slice_config=asdict(slice_config),
        weights=weights,
        input_record_count=input_record_count,
        controlled_slice_count=controlled_slice_count,
        excluded_by_slice_count=excluded_by_slice_count,
        rank_eligible_count=rank_eligible_count,
        blocked_count=blocked_count,
        limitations=(
            "Synthetic fixtures are not research findings.",
            "CRAFTED records are computational screening evidence, not experimental validation.",
            "Ranking applies only within the controlled MOF/GCMC slice.",
            "Blocked records require human review before comparison.",
        ),
    )


def build_transformation_log(
    *,
    metadata: ScreeningExportMetadata,
    generated_files: tuple[Path, ...],
    output_dir: Path,
) -> TransformationLog:
    """Build a reviewable lineage log for generated files."""
    return TransformationLog(
        generated_at=metadata.generated_at,
        source_file=metadata.source_file,
        source_name=metadata.source_name,
        source_version=metadata.source_version,
        license_status=metadata.source_status,
        source_checksum_sha256=metadata.source_checksum_sha256,
        input_row_count=metadata.input_record_count,
        controlled_slice_row_count=metadata.controlled_slice_count,
        excluded_row_count=metadata.excluded_by_slice_count,
        rank_eligible_row_count=metadata.rank_eligible_count,
        blocked_row_count=metadata.blocked_count,
        filter_applied=metadata.slice_config,
        ranking_weights=metadata.weights,
        generated_files=tuple(str(path.relative_to(output_dir)) for path in generated_files),
        transformation_steps=(
            "Load source table without mutating the raw/source file.",
            "Validate required CarbonSense and CRAFTED-like columns.",
            "Select the controlled MOF/GCMC slice using the recorded filter_applied settings.",
            "Export out-of-slice records separately instead of silently dropping them.",
            "Apply comparability rules and tradeoff flags to in-slice records.",
            "Rank only records that remain rank-eligible.",
            "Write ranked, excluded, blocked, metadata, and transformation-log review files.",
        ),
        limitations=metadata.limitations,
    )


def export_screening_result(
    *,
    ranked: pd.DataFrame,
    reviewed: pd.DataFrame,
    excluded: pd.DataFrame,
    metadata: ScreeningExportMetadata,
    output_dir: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    """Write ranked, excluded, blocked, and metadata files for a reviewable result."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked_path = output_dir / "ranked_records.csv"
    excluded_path = output_dir / "excluded_records.csv"
    blocked_path = output_dir / "blocked_records.csv"
    metadata_path = output_dir / "screening_metadata.json"
    transformation_log_path = output_dir / "transformation_log.json"

    ranked.to_csv(ranked_path, index=False)
    excluded.to_csv(excluded_path, index=False)
    if "rank_eligible" in reviewed.columns:
        blocked = reviewed[reviewed["rank_eligible"] == False].copy()  # noqa: E712 - pandas boolean mask
    else:
        blocked = reviewed.iloc[0:0].copy()
    blocked.to_csv(blocked_path, index=False)
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
    transformation_log = build_transformation_log(
        metadata=metadata,
        generated_files=(ranked_path, excluded_path, blocked_path, metadata_path, transformation_log_path),
        output_dir=output_dir,
    )
    transformation_log_path.write_text(json.dumps(asdict(transformation_log), indent=2), encoding="utf-8")
    return ranked_path, excluded_path, blocked_path, metadata_path, transformation_log_path
