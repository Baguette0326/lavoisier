import pandas as pd
from pathlib import Path

from carbonsense.crafted_adapter import (
    CraftedRealSliceConfig,
    CraftedSliceConfig,
    join_crafted_geometric_descriptors,
    load_crafted_mof_geometric_descriptors,
    parse_crafted_real_slice,
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


def test_parse_crafted_real_slice_builds_long_and_screening_tables(tmp_path: Path) -> None:
    root = tmp_path / "CRAFTED-2.0.1"
    isotherm_dir = root / "ISOTHERM_FILES"
    enthalpy_dir = root / "ENTHALPY_FILES"
    isotherm_dir.mkdir(parents=True)
    enthalpy_dir.mkdir()
    (isotherm_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "1.000000000000000000e+04,1.0,0.1\n"
        "2.000000000000000000e+04,2.0,0.2\n",
        encoding="utf-8",
    )
    (isotherm_dir / "DDEC_MOF-1_UFF_N2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "1.000000000000000000e+05,0.5,0.05\n",
        encoding="utf-8",
    )
    (enthalpy_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# Pressure_Pa,Enthalpy_kj/mol,Uncertainty_kj/mol\n"
        "2.000000000000000000e+04,-35.0,0.1\n",
        encoding="utf-8",
    )

    long_table, screening, blocked = parse_crafted_real_slice(root)

    assert long_table["gas"].tolist() == ["CO2", "N2"]
    assert long_table["uptake_mmol_g"].tolist() == [2.0, 0.5]
    assert screening["material_id"].tolist() == ["MOF-1"]
    assert screening.loc[0, "co2_uptake_mmol_g"] == 2.0
    assert screening.loc[0, "n2_uptake_mmol_g"] == 0.5
    assert screening.loc[0, "co2_n2_selectivity"] == 20.0
    assert screening.loc[0, "heat_of_adsorption_kj_mol"] == 35.0
    assert blocked.empty


def test_parse_crafted_real_slice_blocks_missing_pair(tmp_path: Path) -> None:
    root = tmp_path / "CRAFTED-2.0.1"
    isotherm_dir = root / "ISOTHERM_FILES"
    enthalpy_dir = root / "ENTHALPY_FILES"
    isotherm_dir.mkdir(parents=True)
    enthalpy_dir.mkdir()
    (isotherm_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "2.000000000000000000e+04,2.0,0.2\n",
        encoding="utf-8",
    )

    long_table, screening, blocked = parse_crafted_real_slice(root)

    assert long_table["gas"].tolist() == ["CO2"]
    assert screening.empty
    assert blocked.loc[0, "material_id"] == "MOF-1"
    assert blocked.loc[0, "block_type"] == "incomplete_pair"
    assert "missing matched N2 point" in blocked.loc[0, "block_reason"]


def test_parse_crafted_real_slice_blocks_zero_n2_selectivity_denominator(tmp_path: Path) -> None:
    root = tmp_path / "CRAFTED-2.0.1"
    isotherm_dir = root / "ISOTHERM_FILES"
    enthalpy_dir = root / "ENTHALPY_FILES"
    isotherm_dir.mkdir(parents=True)
    enthalpy_dir.mkdir()
    (isotherm_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "2.000000000000000000e+04,2.0,0.2\n",
        encoding="utf-8",
    )
    (isotherm_dir / "DDEC_MOF-1_UFF_N2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "1.000000000000000000e+05,0.0,0.0\n",
        encoding="utf-8",
    )

    _, screening, blocked = parse_crafted_real_slice(root)

    assert screening.empty
    assert blocked.loc[0, "block_type"] == "invalid_selectivity_denominator"
    assert "positive matched CO2 and N2 uptake" in blocked.loc[0, "block_reason"]


def test_load_and_join_crafted_geometric_descriptors(tmp_path: Path) -> None:
    descriptor_path = tmp_path / "CRAFTED_MOF_geometric.csv"
    descriptor_path.write_text(
        "FrameworkName,D_is,D_fs,D_isfs,ASA_m^2/cm^3,ASA_m^2/g,Density,AV_Volume_fraction,AV_cm^3/g,n_pockets\n"
        "MOF-1,6.0,4.0,5.5,1000,1200,0.9,0.25,0.7,2\n",
        encoding="utf-8",
    )
    screening = pd.DataFrame({"material_id": ["MOF-1", "MOF-2"], "co2_uptake_mmol_g": [2.0, 3.0]})

    descriptors = load_crafted_mof_geometric_descriptors(descriptor_path)
    joined = join_crafted_geometric_descriptors(screening, descriptors)

    assert descriptors.loc[0, "pore_limiting_diameter_a"] == 4.0
    assert descriptors.loc[0, "largest_cavity_diameter_a"] == 6.0
    assert descriptors.loc[0, "surface_area_m2_g"] == 1200
    assert joined.loc[0, "descriptor_match_status"] == "matched_crafted_mof_geometric"
    assert joined.loc[1, "descriptor_match_status"] == "missing_crafted_mof_geometric"
