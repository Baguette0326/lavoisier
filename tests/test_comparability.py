import pandas as pd

from carbonsense.comparability import ComparabilityRules, add_comparability_columns
from carbonsense.ranking import rank_materials


def test_add_comparability_columns_marks_matching_records_rank_eligible() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["A", "B"],
            "material_class": ["MOF", "MOF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC"],
            "force_field": ["UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC"],
            "capture_context": ["post-combustion", "post-combustion"],
            "temperature_k": [298, 300],
            "pressure_bar": [1.0, 1.03],
            "humidity_condition": ["dry", "dry"],
        }
    )

    result = add_comparability_columns(frame, ComparabilityRules(require_humidity=True))

    assert result["rank_eligible"].tolist() == [True, True]
    assert result["comparability_status"].tolist() == ["comparable", "comparable"]


def test_add_comparability_columns_blocks_different_pressure() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["A", "B"],
            "material_class": ["MOF", "MOF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC"],
            "force_field": ["UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC"],
            "capture_context": ["post-combustion", "post-combustion"],
            "temperature_k": [298, 298],
            "pressure_bar": [1.0, 0.15],
            "humidity_condition": ["dry", "dry"],
        }
    )

    result = add_comparability_columns(frame, ComparabilityRules(require_humidity=True))

    assert result.loc[0, "rank_eligible"]
    assert not result.loc[1, "rank_eligible"]
    assert "pressure differs beyond tolerance" in result.loc[1, "comparability_reasons"]


def test_add_comparability_columns_requires_humidity_context() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["A"],
            "material_class": ["MOF"],
            "evidence_type": ["computational_gcmc"],
            "simulation_method": ["GCMC"],
            "force_field": ["UFF"],
            "charge_method": ["DDEC"],
            "capture_context": ["post-combustion"],
            "temperature_k": [298],
            "pressure_bar": [1.0],
            "humidity_condition": ["not reported"],
        }
    )

    result = add_comparability_columns(frame, ComparabilityRules(require_humidity=True))

    assert not result.loc[0, "rank_eligible"]
    assert result.loc[0, "comparability_status"] == "needs_review"
    assert "humidity condition is not reported" in result.loc[0, "comparability_reasons"]


def test_add_comparability_columns_blocks_non_mof_records() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["A", "B"],
            "material_class": ["MOF", "COF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC"],
            "force_field": ["UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC"],
            "capture_context": ["post-combustion", "post-combustion"],
            "temperature_k": [298, 298],
            "pressure_bar": [1.0, 1.0],
        }
    )

    result = add_comparability_columns(frame)

    assert not result.loc[1, "rank_eligible"]
    assert "outside the MOF MVP scope" in result.loc[1, "comparability_reasons"]


def test_add_comparability_columns_blocks_different_force_field() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["A", "B"],
            "material_class": ["MOF", "MOF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC"],
            "force_field": ["UFF", "DREIDING"],
            "charge_method": ["DDEC", "DDEC"],
            "capture_context": ["post-combustion", "post-combustion"],
            "temperature_k": [298, 298],
            "pressure_bar": [1.0, 1.0],
        }
    )

    result = add_comparability_columns(frame)

    assert not result.loc[1, "rank_eligible"]
    assert "force field differs from comparison scope" in result.loc[1, "comparability_reasons"]


def test_rank_materials_excludes_non_eligible_records_by_default() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["eligible", "blocked"],
            "evidence_type": ["experimental", "experimental"],
            "rank_eligible": [True, False],
            "co2_uptake_mmol_g": [1.0, 10.0],
        }
    )

    ranked = rank_materials(frame, weights={"co2_uptake_mmol_g": 1.0})

    assert ranked["material_id"].tolist() == ["eligible"]
