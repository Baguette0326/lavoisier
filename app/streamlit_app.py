"""Lavoisier recruiter-demo Streamlit app."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RANKED_RECORDS = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "ranked_records.csv"
SCREENING_METADATA = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "screening_metadata.json"
TRANSFORMATION_LOG = PROJECT_ROOT / "reports" / "crafted_real_slice_export" / "transformation_log.json"
VIRTUAL_LAB_SUMMARY = PROJECT_ROOT / "reports" / "virtual_lab_demo" / "demo_summary.csv"
FEATURE_SET_EVALUATION = (
    PROJECT_ROOT / "reports" / "descriptor_feature_set_evaluation" / "descriptor_feature_set_evaluation.json"
)
FEATURE_SOURCE_POLICY = PROJECT_ROOT / "docs" / "feature_source_policy.md"

RANKED_COLUMNS = [
    "material_id",
    "screening_score",
    "co2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
    "surface_area_m2_g",
    "pore_volume_cm3_g",
    "density_g_cm3",
    "descriptor_match_status",
    "core_match_status",
    "review_flags",
]

PROVENANCE_COLUMNS = [
    "material_id",
    "core_match_status",
    "core_source_file",
    "core_formula_sum",
    "core_cell_volume",
    "core_file_checksum_sha256",
]


def apply_demo_styles() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stMetricValue"] {
            font-variant-numeric: tabular-nums;
        }
        .lavoisier-hero {
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, rgba(41, 98, 91, 0.14), rgba(58, 129, 191, 0.10));
            box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06);
        }
        .lavoisier-hero h1 {
            margin: 0 0 0.25rem 0;
            letter-spacing: 0;
        }
        .lavoisier-hero p {
            margin: 0;
            max-width: 920px;
        }
        .lavoisier-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            margin: 0 0.35rem 0.35rem 0;
            background: rgba(0, 0, 0, 0.06);
            font-size: 0.82rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_demo_header() -> None:
    st.markdown(
        """
        <div class="lavoisier-hero">
          <h1>Lavoisier</h1>
          <p>
            A local decision-support prototype for reviewing carbon-capture MOF screening records.
            It ranks one controlled CRAFTED CO2/N2 slice, attaches CoRE structural provenance,
            and uses target-specific ML estimates for candidate triage without claiming experimental validation.
          </p>
        </div>
        <span class="lavoisier-badge">CRAFTED GCMC slice</span>
        <span class="lavoisier-badge">CoRE MOF provenance</span>
        <span class="lavoisier-badge">Target-specific ML</span>
        <span class="lavoisier-badge">Reviewable exports</span>
        """,
        unsafe_allow_html=True,
    )


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def require_output(path: Path, command: str) -> bool:
    if path.exists():
        return True
    st.error(f"Missing local output: `{path.relative_to(PROJECT_ROOT)}`")
    st.code(command, language="bash")
    return False


def format_metric(value: object, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def display_dataframe(frame: pd.DataFrame, columns: list[str]) -> None:
    visible = [column for column in columns if column in frame.columns]
    st.dataframe(frame[visible], hide_index=True, width="stretch")


def render_ranked_screening(ranked: pd.DataFrame) -> None:
    st.header("Ranked MOF Screening")
    st.caption("Controlled CRAFTED MOF/GCMC slice with CoRE provenance enrichment.")

    if ranked.empty:
        st.info("No ranked records are available yet.")
        return

    top = ranked.iloc[0]
    core_matches = int(ranked["core_match_status"].eq("matched_core2014").sum()) if "core_match_status" in ranked else 0
    flagged = int(ranked["review_flags"].fillna("").astype(str).str.strip().ne("").sum()) if "review_flags" in ranked else 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Ranked records", f"{len(ranked):,}")
    metric_cols[1].metric("Top score", format_metric(float(top["screening_score"])))
    metric_cols[2].metric("CoRE matched", f"{core_matches:,}")
    metric_cols[3].metric("Review flags", f"{flagged:,}")

    controls = st.columns([1, 1, 2])
    top_n = controls[0].slider("Rows", 5, min(100, len(ranked)), 20, step=5)
    core_filter = controls[1].selectbox("CoRE status", ["all", "matched_core2014", "missing_core2014"])
    search = controls[2].text_input("Material search", placeholder="e.g. PARHAS")

    view = ranked.copy()
    if core_filter != "all" and "core_match_status" in view:
        view = view[view["core_match_status"].eq(core_filter)]
    if search:
        view = view[view["material_id"].astype(str).str.contains(search, case=False, na=False)]
    view = view.head(top_n)

    display_dataframe(view, RANKED_COLUMNS)

    if not view.empty:
        st.subheader("Top Candidate Snapshot")
        selected_id = st.selectbox("Inspect material", view["material_id"].astype(str).tolist())
        selected = ranked[ranked["material_id"].astype(str).eq(selected_id)].iloc[0]
        detail_cols = st.columns(3)
        detail_cols[0].metric("CO2 uptake (mmol/g)", format_metric(selected.get("co2_uptake_mmol_g")))
        detail_cols[1].metric("CO2/N2 selectivity", format_metric(selected.get("co2_n2_selectivity")))
        detail_cols[2].metric("Heat of adsorption (kJ/mol)", format_metric(selected.get("heat_of_adsorption_kj_mol")))
        st.write("Provenance")
        display_dataframe(pd.DataFrame([selected]), PROVENANCE_COLUMNS)

    csv_bytes = view.to_csv(index=False).encode("utf-8")
    st.download_button("Export visible ranked records", csv_bytes, "lavoisier_ranked_visible.csv", "text/csv")

    with st.expander("How to explain this tab in a demo"):
        st.markdown(
            """
            - The comparison is intentionally restricted to one controlled CRAFTED slice.
            - The ranking is deterministic and reviewable, not an autonomous material-discovery claim.
            - CoRE fields show whether each performance record has matched structural provenance.
            """
        )


def render_virtual_lab() -> None:
    st.header("Candidate Virtual Lab")
    st.caption("Synthetic unfamiliar-candidate examples; recommendations are triage, not validation.")

    if not require_output(VIRTUAL_LAB_SUMMARY, "python scripts/run_virtual_lab_demo.py"):
        return

    summary = read_csv(VIRTUAL_LAB_SUMMARY)
    if summary.empty:
        st.info("Virtual lab summary exists but has no rows.")
        return

    st.dataframe(summary, hide_index=True, width="stretch")
    selected_label = st.selectbox("Review candidate", summary["material_id"].astype(str).tolist())
    selected = summary[summary["material_id"].astype(str).eq(selected_label)].iloc[0]
    report_path = PROJECT_ROOT / str(selected["report_path"])
    report_text = read_text(report_path)

    decision_cols = st.columns(4)
    decision_cols[0].metric("Decision", str(selected["final_decision"]))
    decision_cols[1].metric("Viability", str(selected["viability_read"]))
    decision_cols[2].metric("Better than reference", str(selected["better_than_known_reference"]))
    decision_cols[3].metric("Confidence", str(selected["review_confidence"]))

    if report_text:
        with st.expander("Candidate Review Report", expanded=True):
            st.markdown(report_text)
    else:
        st.warning(f"Candidate report is missing: `{report_path.relative_to(PROJECT_ROOT)}`")

    if require_output(FEATURE_SET_EVALUATION, "python scripts/evaluate_descriptor_feature_sets.py"):
        evaluation = read_json(FEATURE_SET_EVALUATION)
        comparisons = evaluation.get("comparison_summary", {}).get("target_comparisons", {})
        if isinstance(comparisons, dict):
            st.subheader("ML Feature Policy Evidence")
            rows = []
            for target, detail in comparisons.items():
                if isinstance(detail, dict):
                    rows.append(
                        {
                            "target": target,
                            "status": detail.get("status"),
                            "baseline_mae": detail.get("baseline_test_mae"),
                            "core_plus_mae": detail.get("candidate_test_mae"),
                            "improved_splits": (
                                f"{detail.get('candidate_improved_split_count')}/"
                                f"{detail.get('comparable_split_count')}"
                            ),
                        }
                    )
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    with st.expander("How to explain this tab in a demo"):
        st.markdown(
            """
            - Candidate metrics are synthetic user-supplied claims for demo purposes.
            - The ML model estimates expected properties from descriptors, then flags assumption gaps.
            - Feature sets are target-specific because CoRE descriptors helped uptake and heat, but hurt selectivity.
            """
        )


def render_provenance(ranked: pd.DataFrame) -> None:
    st.header("Provenance And Limitations")
    st.caption("What this result came from, what was filtered, and what the software cannot claim.")

    metadata = read_json(SCREENING_METADATA)
    transformation_log = read_json(TRANSFORMATION_LOG)

    if metadata:
        st.subheader("Controlled Slice")
        slice_config = metadata.get("slice_config", {})
        if isinstance(slice_config, dict):
            st.json(slice_config)

        count_cols = st.columns(4)
        count_cols[0].metric("Input rows", format_metric(metadata.get("input_record_count"), 0))
        count_cols[1].metric("Controlled slice", format_metric(metadata.get("controlled_slice_count"), 0))
        count_cols[2].metric("Rank eligible", format_metric(metadata.get("rank_eligible_count"), 0))
        count_cols[3].metric("Blocked", format_metric(metadata.get("blocked_count"), 0))

    if transformation_log:
        st.subheader("Transformation Receipt")
        receipt_rows = {
            "source_name": transformation_log.get("source_name"),
            "source_version": transformation_log.get("source_version"),
            "license_status": transformation_log.get("license_status"),
            "source_checksum_sha256": transformation_log.get("source_checksum_sha256"),
            "generated_at": transformation_log.get("generated_at"),
        }
        st.dataframe(pd.DataFrame([receipt_rows]), hide_index=True, width="stretch")
        with st.expander("Transformation steps"):
            for step in transformation_log.get("transformation_steps", []):
                st.write(f"- {step}")
        with st.expander("Ranking weights"):
            st.json(transformation_log.get("ranking_weights", {}))

    st.subheader("Feature Source Policy")
    policy_text = read_text(FEATURE_SOURCE_POLICY)
    if policy_text:
        with st.expander("Open feature/database policy"):
            st.markdown(policy_text)

    st.subheader("Current Limits")
    limitations = metadata.get("limitations", []) if metadata else []
    if limitations:
        for limitation in limitations:
            st.warning(str(limitation))
    st.warning("Descriptor predictions are ML estimates, not GCMC simulations or lab measurements.")
    st.warning("The app compares one controlled slice; it does not predict performance at other temperatures or pressures yet.")

    if not ranked.empty:
        st.subheader("CoRE Coverage")
        if "core_match_status" in ranked:
            st.bar_chart(ranked["core_match_status"].value_counts())

    with st.expander("Demo close-out"):
        st.markdown(
            """
            Lavoisier is useful because carbon-capture material records are only meaningful with their
            conditions, evidence type, and source lineage attached. The app helps produce a shortlist
            that a human can inspect instead of treating high adsorption numbers as universally comparable.
            """
        )


def main() -> None:
    st.set_page_config(page_title="Lavoisier", page_icon="L", layout="wide")
    apply_demo_styles()
    render_demo_header()

    if not require_output(RANKED_RECORDS, "python scripts/run_crafted_real_slice.py"):
        return

    ranked = read_csv(RANKED_RECORDS)
    tabs = st.tabs(["Ranked MOF Screening", "Candidate Virtual Lab", "Provenance / Limitations"])
    with tabs[0]:
        render_ranked_screening(ranked)
    with tabs[1]:
        render_virtual_lab()
    with tabs[2]:
        render_provenance(ranked)


if __name__ == "__main__":
    main()
