import pandas as pd

from carbonsense.crafted_adapter import (
    CraftedSliceConfig,
    select_controlled_crafted_slice,
    validate_crafted_like_table,
)


def test_validate_crafted_like_table_reports_missing_columns() -> None:
    warnings = validate_crafted_like_table(pd.DataFrame({"material_id": ["MOF-1"]}))

    assert any("Missing CRAFTED MVP column" in warning for warning in warnings)


def test_validate_crafted_like_table_flags_non_mof_records() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["MOF-1", "COF-1"],
            "material_class": ["MOF", "COF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "simulation_method": ["GCMC", "GCMC"],
            "force_field": ["UFF", "UFF"],
            "charge_method": ["DDEC", "DDEC"],
            "temperature_k": [298, 298],
            "pressure_bar": [1.0, 1.0],
            "co2_uptake_mmol_g": [4.0, 5.0],
            "n2_uptake_mmol_g": [0.2, 0.3],
        }
    )

    warnings = validate_crafted_like_table(frame)

    assert "1 non-MOF record(s) must be excluded from the MVP slice." in warnings


def test_select_controlled_crafted_slice_filters_scope() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["keep", "wrong_temp", "wrong_force", "cof"],
            "material_class": ["MOF", "MOF", "MOF", "COF"],
            "evidence_type": ["computational_gcmc"] * 4,
            "simulation_method": ["GCMC"] * 4,
            "force_field": ["UFF", "UFF", "DREIDING", "UFF"],
            "charge_method": ["DDEC"] * 4,
            "temperature_k": [298, 323, 298, 298],
        }
    )

    result = select_controlled_crafted_slice(frame, CraftedSliceConfig(force_field="UFF", charge_method="DDEC"))

    assert result["material_id"].tolist() == ["keep"]
