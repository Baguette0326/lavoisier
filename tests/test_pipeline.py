import json
from pathlib import Path

import pandas as pd

from carbonsense.crafted_adapter import CraftedSliceConfig
from carbonsense.pipeline import export_result, run_crafted_screening_pipeline, run_fixture_pipeline


def test_run_crafted_screening_pipeline_filters_and_ranks_controlled_slice() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["keep_low", "keep_high", "wrong_force", "cof"],
            "material_class": ["MOF", "MOF", "MOF", "COF"],
            "evidence_type": ["computational_gcmc"] * 4,
            "simulation_method": ["GCMC"] * 4,
            "force_field": ["UFF", "UFF", "DREIDING", "UFF"],
            "charge_method": ["DDEC"] * 4,
            "source": ["fixture"] * 4,
            "capture_context": ["post-combustion"] * 4,
            "temperature_k": [298] * 4,
            "pressure_bar": [1.0] * 4,
            "co2_uptake_mmol_g": [1.0, 5.0, 9.0, 10.0],
            "n2_uptake_mmol_g": [0.2, 0.1, 0.1, 0.1],
            "co2_n2_selectivity": [5, 50, 90, 100],
        }
    )

    result = run_crafted_screening_pipeline(
        frame,
        slice_config=CraftedSliceConfig(force_field="UFF", charge_method="DDEC"),
        weights={"co2_uptake_mmol_g": 1.0},
    )

    assert result.controlled_slice["material_id"].tolist() == ["keep_low", "keep_high"]
    assert result.ranked_records["material_id"].tolist() == ["keep_high", "keep_low"]
    assert result.metadata.input_record_count == 4
    assert result.metadata.controlled_slice_count == 2
    assert result.metadata.excluded_by_slice_count == 2
    assert result.metadata.rank_eligible_count == 2


def test_run_fixture_pipeline_uses_bundled_fixture() -> None:
    result = run_fixture_pipeline(Path("data/crafted_like_fixture.csv"))

    assert len(result.input_records) == 7
    assert len(result.controlled_slice) == 4
    assert len(result.excluded_records) == 3
    assert set(result.ranked_records["rank_eligible"]) == {True}


def test_export_result_writes_review_files(tmp_path: Path) -> None:
    result = run_fixture_pipeline(Path("data/crafted_like_fixture.csv"))

    ranked_path, excluded_path, blocked_path, metadata_path, transformation_log_path = export_result(result, tmp_path)

    assert ranked_path.exists()
    assert excluded_path.exists()
    assert blocked_path.exists()
    assert metadata_path.exists()
    assert transformation_log_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["source_status"] == "synthetic_fixture_not_research_data"
    assert metadata["controlled_slice_count"] == 4
    assert metadata["excluded_by_slice_count"] == 3
    assert metadata["source_checksum_sha256"]
    assert len(metadata["source_checksum_sha256"]) == 64
    transformation_log = json.loads(transformation_log_path.read_text(encoding="utf-8"))
    assert transformation_log["source_checksum_sha256"] == metadata["source_checksum_sha256"]
    assert transformation_log["input_row_count"] == 7
    assert transformation_log["controlled_slice_row_count"] == 4
    assert transformation_log["excluded_row_count"] == 3
    assert transformation_log["filter_applied"]["material_class"] == "MOF"
    assert transformation_log["filter_applied"]["force_field"] == "UFF"
    assert transformation_log["filter_applied"]["charge_method"] == "DDEC"
    assert "ranked_records.csv" in transformation_log["generated_files"]
    assert "transformation_log.json" in transformation_log["generated_files"]
