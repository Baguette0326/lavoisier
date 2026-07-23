import pandas as pd

from carbonsense.flags import build_tradeoff_flags


def test_build_tradeoff_flags_marks_computational_evidence() -> None:
    frame = pd.DataFrame({"material_id": ["MOF-1"], "evidence_type": ["computational_gcmc"]})

    result = build_tradeoff_flags(frame)

    assert "computational evidence requires experimental validation" in result.loc[0, "review_flags"]


def test_build_tradeoff_flags_tolerates_non_numeric_upload_values() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["MOF-1"],
            "evidence_type": ["experimental"],
            "co2_uptake_mmol_g": ["not reported"],
            "co2_n2_selectivity": ["unknown"],
            "heat_of_adsorption_kj_mol": ["n/a"],
            "humidity_flag": [None],
        }
    )

    result = build_tradeoff_flags(frame)

    assert "humidity stability not reported" in result.loc[0, "review_flags"]
