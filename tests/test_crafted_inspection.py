import json
from pathlib import Path

import pandas as pd

from carbonsense.crafted_inspection import inspect_path, write_inspection_outputs


def test_inspect_path_builds_manifest_for_tabular_files(tmp_path: Path) -> None:
    table_path = tmp_path / "isotherms.csv"
    table_path.write_text(
        "material_id,gas,pressure_bar,temperature_k,uptake_mmol_g,force_field,charge_method\n"
        "MOF-1,CO2,0.15,298,1.2,UFF,DDEC\n",
        encoding="utf-8",
    )

    inspections = inspect_path(tmp_path)

    assert len(inspections) == 1
    assert inspections[0].path == "isotherms.csv"
    assert inspections[0].is_tabular
    assert inspections[0].row_count == 1
    assert "pressure_bar" in inspections[0].columns


def test_write_inspection_outputs_reports_pressure_availability(tmp_path: Path) -> None:
    source_dir = tmp_path / "crafted"
    source_dir.mkdir()
    (source_dir / "isotherms.csv").write_text(
        "material_id,gas,pressure_bar,temperature_k,uptake_mmol_g,force_field,charge_method\n"
        "MOF-1,CO2,0.15,298,1.2,UFF,DDEC\n"
        "MOF-2,CO2,0.15,298,1.4,UFF,DDEC\n"
        "MOF-1,N2,0.85,298,0.1,UFF,DDEC\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "inspection"

    manifest_path, pressure_path, column_map_path, summary_path = write_inspection_outputs(source_dir, output_dir)

    assert manifest_path.exists()
    assert pressure_path.exists()
    assert column_map_path.exists()
    assert summary_path.exists()
    pressure = pd.read_csv(pressure_path)
    assert set(pressure["gas"]) == {"CO2", "N2"}
    co2_row = pressure[(pressure["gas"] == "CO2") & (pressure["pressure_bar"] == 0.15)].iloc[0]
    assert co2_row["record_count"] == 2
    assert co2_row["material_count"] == 2
    column_map = json.loads(column_map_path.read_text(encoding="utf-8"))
    assert {"file": "isotherms.csv", "column": "pressure_bar"} in column_map["pressure"]
    summary = summary_path.read_text(encoding="utf-8")
    assert "Files inspected: 1" in summary


def test_write_inspection_outputs_uses_fast_crafted_folder_path(tmp_path: Path) -> None:
    source_dir = tmp_path / "CRAFTED-2.0.1"
    isotherm_dir = source_dir / "ISOTHERM_FILES"
    enthalpy_dir = source_dir / "ENTHALPY_FILES"
    isotherm_dir.mkdir(parents=True)
    enthalpy_dir.mkdir()
    (isotherm_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# pressure[Pa],mean_volume[mol/kg],mean_error[mol/kg]\n"
        "1.000000000000000000e+04,1.2,0.1\n"
        "2.000000000000000000e+04,1.4,0.1\n",
        encoding="utf-8",
    )
    (enthalpy_dir / "DDEC_MOF-1_UFF_CO2_298.csv").write_text(
        "# pressure[Pa],enthalpy[kJ/mol]\n"
        "1.000000000000000000e+04,30\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "inspection"

    manifest_path, pressure_path, column_map_path, summary_path = write_inspection_outputs(source_dir, output_dir)

    manifest = pd.read_csv(manifest_path)
    pressure = pd.read_csv(pressure_path)
    assert set(manifest["data_kind"]) == {"enthalpy", "isotherm"}
    assert pressure["pressure_bar"].tolist() == [0.1, 0.2]
    column_map = json.loads(column_map_path.read_text(encoding="utf-8"))
    assert column_map["pressure"][0]["converted_to"] == "pressure_bar"
    summary = summary_path.read_text(encoding="utf-8")
    assert "Parsed isotherm files: 1" in summary
