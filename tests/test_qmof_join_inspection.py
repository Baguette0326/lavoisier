from pathlib import Path

import pandas as pd

from scripts.inspect_qmof_join import QMOF_USECOLS, inspect_join, normalize_qmof_name


def qmof_row(**overrides: object) -> dict[str, object]:
    row = {column: None for column in QMOF_USECOLS}
    row.update(
        {
            "qmof_id": "qmof-test",
            "name": "ABUWOJ_FSR",
            "info.source": "CSD",
            "info.synthesized": True,
            "info.pld": 3.1,
            "info.lcd": 5.2,
            "info.density": 1.2,
            "info.volume": 1000.0,
            "outputs.pbe.bandgap": 1.5,
        }
    )
    row.update(overrides)
    return row


def test_normalize_qmof_name_only_strips_terminal_fsr() -> None:
    assert normalize_qmof_name("ABUWOJ_FSR") == "ABUWOJ"
    assert normalize_qmof_name("ABUWOJ") == "ABUWOJ"
    assert normalize_qmof_name("ABUWOJ_1") == "ABUWOJ_1"
    assert normalize_qmof_name("ABUWOJ_FSR_extra") == "ABUWOJ_FSR_extra"
    assert normalize_qmof_name("") is None


def test_inspect_join_reports_controlled_fsr_overlap(tmp_path: Path) -> None:
    qmof_path = tmp_path / "qmof.csv"
    metadata_path = tmp_path / "qmof_figshare_article.json"
    geometric_path = tmp_path / "CRAFTED_MOF_geometric.csv"
    ranked_path = tmp_path / "ranked_records.csv"

    pd.DataFrame(
        [
            qmof_row(qmof_id="qmof-1", name="ABUWOJ_FSR"),
            qmof_row(qmof_id="qmof-2", name="ACOLIP"),
            qmof_row(qmof_id="qmof-3", name="05000N2_FSR"),
        ]
    ).to_csv(qmof_path, index=False)
    metadata_path.write_text(
        '{"doi":"10.6084/m9.figshare.13147324.v18","version":18,"license":{"name":"CC BY 4.0"}}',
        encoding="utf-8",
    )
    pd.DataFrame({"FrameworkName": ["ABUWOJ", "ACOLIP", "05000N2"]}).to_csv(geometric_path, index=False)
    pd.DataFrame({"material_id": ["ABUWOJ", "05000N2"]}).to_csv(ranked_path, index=False)

    summary, matched = inspect_join(qmof_path, metadata_path, geometric_path, ranked_path)

    assert summary["figshare_version"] == 18
    assert summary["qmof_raw_name_to_crafted_geometric"]["matched_count"] == 1
    assert summary["qmof_normalized_name_to_crafted_geometric"]["matched_count"] == 3
    assert summary["qmof_normalized_name_to_ranked"]["matched_count"] == 2
    assert summary["matched_descriptor_row_count"] == 3
    assert set(matched["join_method"]) == {"name_exact", "name_strip_FSR"}
