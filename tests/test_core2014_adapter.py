from pathlib import Path
import tarfile

import pandas as pd

from carbonsense.core2014_adapter import (
    build_core2014_enrichment,
    join_core2014_enrichment,
    load_core2014_records,
    normalize_core2014_member_name,
)


def test_normalize_core2014_member_name_strips_clean_suffix() -> None:
    assert normalize_core2014_member_name("./re-labeled/ABUWOJ_clean.cif") == "ABUWOJ"
    assert normalize_core2014_member_name("./re-labeled/ACOLIP.cif") == "ACOLIP"
    assert normalize_core2014_member_name("./re-labeled/._ACOLIP.cif") is None
    assert normalize_core2014_member_name("./re-labeled/readme.txt") is None


def test_load_core2014_records_extracts_safe_cif_metadata(tmp_path: Path) -> None:
    cif_path = tmp_path / "ABUWOJ_clean.cif"
    cif_path.write_text(
        "\n".join(
            [
                "data_Zn2H7C12O7",
                "_symmetry_space_group_name_H-M   'P 1'",
                "_cell_length_a   14.49880000",
                "_cell_length_b   17.16590000",
                "_cell_length_c   18.15360000",
                "_cell_angle_alpha   90.00000000",
                "_cell_angle_beta   90.00000000",
                "_cell_angle_gamma   90.00000000",
                "_symmetry_Int_Tables_number   1",
                "_chemical_formula_structural   Zn2H7C12O7",
                "_chemical_formula_sum   'Zn16 H56 C96 O56'",
                "_cell_volume   4518.15784502",
                "_cell_formula_units_Z   8",
            ]
        ),
        encoding="utf-8",
    )
    archive_path = tmp_path / "core.tar"
    with tarfile.open(archive_path, "w") as archive:
        archive.add(cif_path, arcname="./re-labeled/ABUWOJ_clean.cif")

    records = load_core2014_records(archive_path)

    assert len(records) == 1
    row = records.iloc[0]
    assert row["material_id"] == "ABUWOJ"
    assert row["core_had_clean_suffix"] == True  # noqa: E712 - pandas stores bools as numpy scalars
    assert row["core_formula_structural"] == "Zn2H7C12O7"
    assert row["core_formula_sum"] == "Zn16 H56 C96 O56"
    assert row["core_cell_length_a"] == 14.4988
    assert row["core_cell_volume"] == 4518.15784502
    assert row["core_space_group_hm"] == "P 1"
    assert isinstance(row["core_file_checksum_sha256"], str)
    assert len(row["core_file_checksum_sha256"]) == 64


def test_build_core2014_enrichment_preserves_missing_targets() -> None:
    core_records = pd.DataFrame(
        [
            {
                "material_id": "ABUWOJ",
                "core_match_status": "matched_core2014",
                "core_source_file": "./re-labeled/ABUWOJ_clean.cif",
                "core_source_version": "CoRE MOF 2014 DDEC",
                "core_source_doi": "10.5281/zenodo.3986573",
                "core_license": "CC BY 4.0",
            }
        ]
    )

    enrichment = build_core2014_enrichment(core_records, {"ABUWOJ", "MISSING"})

    assert enrichment["material_id"].tolist() == ["ABUWOJ", "MISSING"]
    assert enrichment["core_match_status"].tolist() == ["matched_core2014", "missing_core2014"]
    assert enrichment.loc[1, "core_source_version"] == "CoRE MOF 2014 DDEC"


def test_join_core2014_enrichment_preserves_screening_rows() -> None:
    screening = pd.DataFrame(
        {
            "material_id": ["ABUWOJ", "UNMATCHED"],
            "co2_uptake_mmol_g": [4.2, 1.1],
        }
    )
    enrichment = pd.DataFrame(
        [
            {
                "material_id": "ABUWOJ",
                "core_match_status": "matched_core2014",
                "core_source_file": "./re-labeled/ABUWOJ_clean.cif",
                "core_formula_sum": "Zn16 H56 C96 O56",
                "core_source_version": "CoRE MOF 2014 DDEC",
                "core_source_doi": "10.5281/zenodo.3986573",
                "core_license": "CC BY 4.0",
            }
        ]
    )

    joined = join_core2014_enrichment(screening, enrichment)

    assert joined["material_id"].tolist() == ["ABUWOJ", "UNMATCHED"]
    assert joined["core_match_status"].tolist() == ["matched_core2014", "missing_core2014"]
    assert joined.loc[0, "core_formula_sum"] == "Zn16 H56 C96 O56"
    assert joined.loc[1, "core_source_version"] == "CoRE MOF 2014 DDEC"
