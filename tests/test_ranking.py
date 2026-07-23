import pandas as pd

from carbonsense.ranking import rank_materials


def test_rank_materials_orders_by_weighted_score() -> None:
    frame = pd.DataFrame(
        {
            "material_id": ["weak", "strong"],
            "material_class": ["MOF", "MOF"],
            "evidence_type": ["computational_gcmc", "computational_gcmc"],
            "co2_uptake_mmol_g": [1.0, 5.0],
            "co2_n2_selectivity": [5.0, 50.0],
        }
    )

    ranked = rank_materials(
        frame,
        weights={"co2_uptake_mmol_g": 0.5, "co2_n2_selectivity": 0.5},
        require_rank_eligible=False,
    )

    assert ranked.iloc[0]["material_id"] == "strong"
    assert "screening_score" in ranked.columns
