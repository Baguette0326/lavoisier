import pandas as pd

from carbonsense.schema import validate_material_table


def test_validate_material_table_accepts_required_columns() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["MOF-1"],
            "material_class": ["MOF"],
            "evidence_type": ["computational_gcmc"],
            "co2_uptake_mmol_g": [4.0],
        }
    )

    result = validate_material_table(frame)

    assert result.is_valid
    assert result.missing_required == []


def test_validate_material_table_reports_missing_required_columns() -> None:
    frame = pd.DataFrame({"material": ["MOF-1"]})

    result = validate_material_table(frame)

    assert not result.is_valid
    assert result.missing_required == ["evidence_type", "material_class", "material_id"]


def test_validate_material_table_warns_about_messy_screening_data() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["MOF-1", "MOF-1"],
            "evidence_type": ["computational", "experimental"],
            "co2_uptake_mmol_g": ["unknown", 4.0],
        }
    )

    result = validate_material_table(frame)

    assert any("duplicate material" in warning for warning in result.warnings)
    assert any("non-numeric" in warning for warning in result.warnings)
