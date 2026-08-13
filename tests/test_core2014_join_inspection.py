import tarfile
from pathlib import Path

import pandas as pd

from scripts.inspect_core2014_join import inspect_join, normalize_core_id


def test_normalize_core_id_removes_clean_suffix_and_metadata_files() -> None:
    assert normalize_core_id("./re-labeled/ABUWOJ_clean.cif") == "ABUWOJ"
    assert normalize_core_id("./re-labeled/ACOLIP.cif") == "ACOLIP"
    assert normalize_core_id("./re-labeled/._ACOLIP.cif") is None
    assert normalize_core_id("./re-labeled/readme.txt") is None


def test_inspect_join_reports_exact_overlap(tmp_path: Path) -> None:
    archive_path = tmp_path / "core.tar"
    crafted_cif_dir = tmp_path / "crafted_cifs"
    geometric_path = tmp_path / "CRAFTED_MOF_geometric.csv"
    ranked_path = tmp_path / "ranked_records.csv"
    crafted_cif_dir.mkdir()

    for name in ("ABUWOJ.cif", "ACOLIP.cif", "05000N2.cif"):
        (crafted_cif_dir / name).write_text("data_test\n", encoding="utf-8")
    pd.DataFrame({"FrameworkName": ["ABUWOJ", "ACOLIP", "05000N2"]}).to_csv(geometric_path, index=False)
    pd.DataFrame({"material_id": ["ABUWOJ", "05000N2"]}).to_csv(ranked_path, index=False)

    core_file = tmp_path / "ABUWOJ_clean.cif"
    core_file.write_text("data_ABUWOJ\n", encoding="utf-8")
    core_file_2 = tmp_path / "ACOLIP.cif"
    core_file_2.write_text("data_ACOLIP\n", encoding="utf-8")
    with tarfile.open(archive_path, "w") as archive:
        archive.add(core_file, arcname="./re-labeled/ABUWOJ_clean.cif")
        archive.add(core_file_2, arcname="./re-labeled/ACOLIP.cif")

    summary = inspect_join(archive_path, crafted_cif_dir, geometric_path, ranked_path)

    assert summary["core_id_count"] == 2
    assert summary["crafted_cif_to_core"]["matched_count"] == 2
    assert summary["crafted_cif_to_core"]["missing_count"] == 1
    assert summary["crafted_geometric_to_core"]["match_fraction"] == 0.6667
    assert summary["ranked_to_core"]["matched_examples"] == ["ABUWOJ"]
