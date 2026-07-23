"""End-to-end backend screening pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from carbonsense.comparability import ComparabilityRules, add_comparability_columns
from carbonsense.crafted_adapter import (
    CraftedSliceConfig,
    select_controlled_crafted_slice,
    validate_crafted_like_table,
)
from carbonsense.export import (
    ScreeningExportMetadata,
    build_export_metadata,
    calculate_sha256,
    export_screening_result,
)
from carbonsense.flags import build_tradeoff_flags
from carbonsense.ranking import DEFAULT_WEIGHTS, rank_materials
from carbonsense.schema import ValidationResult, validate_material_table


@dataclass(frozen=True)
class ScreeningResult:
    """Result of running the backend screening pipeline."""

    input_records: pd.DataFrame
    controlled_slice: pd.DataFrame
    excluded_records: pd.DataFrame
    reviewed_records: pd.DataFrame
    ranked_records: pd.DataFrame
    validation: ValidationResult
    crafted_warnings: tuple[str, ...]
    metadata: ScreeningExportMetadata


def run_crafted_screening_pipeline(
    frame: pd.DataFrame,
    *,
    slice_config: CraftedSliceConfig,
    comparability_rules: ComparabilityRules | None = None,
    weights: dict[str, float] | None = None,
    source_name: str = "Synthetic CRAFTED-like fixture",
    source_version: str = "fixture",
    source_status: str = "synthetic_fixture_not_research_data",
    source_file: Path | None = None,
) -> ScreeningResult:
    """Run validation, slice selection, comparability, flags, and ranking."""
    active_weights = weights or DEFAULT_WEIGHTS
    validation = validate_material_table(frame)
    crafted_warnings = tuple(validate_crafted_like_table(frame))
    controlled_slice = select_controlled_crafted_slice(frame, slice_config)
    excluded = frame.loc[~frame.index.isin(controlled_slice.index)].copy()
    reviewed = add_comparability_columns(controlled_slice, comparability_rules or ComparabilityRules())
    reviewed = build_tradeoff_flags(reviewed)
    ranked = rank_materials(reviewed, weights=active_weights)
    metadata = build_export_metadata(
        source_name=source_name,
        source_version=source_version,
        source_status=source_status,
        source_file=source_file,
        source_checksum_sha256=calculate_sha256(source_file) if source_file else None,
        slice_config=slice_config,
        weights=active_weights,
        input_record_count=len(frame),
        controlled_slice_count=len(controlled_slice),
        excluded_by_slice_count=len(excluded),
        rank_eligible_count=len(ranked),
        blocked_count=int((reviewed["rank_eligible"] == False).sum()) if "rank_eligible" in reviewed.columns else 0,
    )
    return ScreeningResult(
        input_records=frame.copy(),
        controlled_slice=controlled_slice,
        excluded_records=excluded,
        reviewed_records=reviewed,
        ranked_records=ranked,
        validation=validation,
        crafted_warnings=crafted_warnings,
        metadata=metadata,
    )


def run_fixture_pipeline(fixture_path: Path) -> ScreeningResult:
    """Run the pipeline on the bundled synthetic CRAFTED-like fixture."""
    frame = pd.read_csv(fixture_path)
    return run_crafted_screening_pipeline(
        frame,
        slice_config=CraftedSliceConfig(force_field="UFF", charge_method="DDEC"),
        source_file=fixture_path,
    )


def export_result(result: ScreeningResult, output_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Export a pipeline result with ranked, blocked, and metadata files."""
    return export_screening_result(
        ranked=result.ranked_records,
        reviewed=result.reviewed_records,
        excluded=result.excluded_records,
        metadata=result.metadata,
        output_dir=output_dir,
    )
