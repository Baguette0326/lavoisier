"""CarbonSense Streamlit app."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from carbonsense.flags import build_tradeoff_flags
from carbonsense.ranking import DEFAULT_WEIGHTS, rank_materials
from carbonsense.schema import validate_material_table


SAMPLE_DATA = PROJECT_ROOT / "data" / "sample_materials.csv"
DISPLAY_COLUMNS = [
    "rank",
    "material_id",
    "screening_score",
    "evidence_type",
    "source",
    "capture_context",
    "co2_uptake_mmol_g",
    "co2_n2_selectivity",
    "heat_of_adsorption_kj_mol",
    "review_flags",
]


def load_frame(source_choice: str, uploaded: object | None) -> pd.DataFrame | None:
    """Load the selected local demo or uploaded CSV."""
    if source_choice == "Use demo data":
        return pd.read_csv(SAMPLE_DATA)
    if uploaded is not None:
        return pd.read_csv(uploaded)
    return None


def explain_top_candidate(ranked: pd.DataFrame, weights: dict[str, float]) -> str:
    """Summarize the strongest weighted score components for the top record."""
    if ranked.empty:
        return "No candidate is available to explain."
    active_total = sum(weight for feature, weight in weights.items() if feature in ranked.columns)
    if active_total <= 0:
        return "No scoring criteria have a positive weight."
    top = ranked.iloc[0]
    contributions: list[tuple[str, float]] = []
    for feature, weight in weights.items():
        score_column = f"{feature}_score"
        if score_column in ranked.columns:
            contributions.append((feature, float(top[score_column]) * weight / active_total))
    strongest = sorted(contributions, key=lambda item: item[1], reverse=True)[:2]
    drivers = ", ".join(feature.replace("_", " ") for feature, _ in strongest)
    return f"{top['material_id']} ranks first. Its strongest weighted drivers are {drivers}."


st.set_page_config(page_title="CarbonSense", page_icon="CS", layout="wide")
st.title("CarbonSense")
st.caption(
    "AI-assisted, human-reviewed screening for carbon-capture materials. "
    "Scores support comparison; they are not experimental validation."
)

st.subheader("1. Choose review data")
source_choice = st.radio(
    "Data source",
    ["Use demo data", "Upload CSV"],
    horizontal=True,
    label_visibility="collapsed",
)
uploaded = None
if source_choice == "Upload CSV":
    uploaded = st.file_uploader("Upload an approved or review-ready CSV dataset", type=["csv"])
else:
    st.info("Using six synthetic records for demonstration only. They are not research findings.")

try:
    frame = load_frame(source_choice, uploaded)
except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"The CSV could not be read: {error}")
    st.stop()

if frame is None:
    st.info("Choose a CSV to begin the review.")
    st.stop()

validation = validate_material_table(frame)
if not validation.is_valid:
    st.error(f"Missing required columns: {', '.join(validation.missing_required)}")
    st.caption("Required: `material_id` and `evidence_type`.")
    st.stop()

st.subheader("2. Validate and scope")
metric_columns = st.columns(4)
metric_columns[0].metric("Records", len(frame))
metric_columns[1].metric("Fields", len(frame.columns))
metric_columns[2].metric("Screening fields", len(validation.available_recommended))
metric_columns[3].metric("Validation warnings", len(validation.warnings))

if validation.warnings:
    with st.expander(f"Review {len(validation.warnings)} validation warning(s)", expanded=True):
        for warning in validation.warnings:
            st.warning(warning)
else:
    st.success("Minimum schema checks passed with no warnings.")

filter_columns = st.columns(2)
filtered = frame.copy()
if "capture_context" in frame.columns:
    contexts = sorted(frame["capture_context"].dropna().astype(str).unique())
    selected_contexts = filter_columns[0].multiselect("Capture context", contexts, default=contexts)
    filtered = filtered[filtered["capture_context"].astype(str).isin(selected_contexts)]
if "evidence_type" in frame.columns:
    evidence_types = sorted(frame["evidence_type"].dropna().astype(str).unique())
    selected_evidence = filter_columns[1].multiselect("Evidence type", evidence_types, default=evidence_types)
    filtered = filtered[filtered["evidence_type"].astype(str).isin(selected_evidence)]

if filtered.empty:
    st.warning("No records match the selected review scope.")
    st.stop()

st.subheader("3. Rank candidates")
with st.expander("Adjust transparent ranking weights"):
    st.caption("Weights are normalized automatically. Heat of adsorption scores best in the 25-60 kJ/mol target range.")
    weights: dict[str, float] = {}
    weight_columns = st.columns(3)
    for index, (feature, default_weight) in enumerate(DEFAULT_WEIGHTS.items()):
        if feature in filtered.columns:
            with weight_columns[index % 3]:
                weights[feature] = st.slider(
                    feature.replace("_", " ").title(),
                    0.0,
                    1.0,
                    float(default_weight),
                    0.05,
                )

ranked = build_tradeoff_flags(rank_materials(filtered, weights=weights))
ranked.insert(0, "rank", range(1, len(ranked) + 1))
ranked["has_review_flag"] = ranked["review_flags"].astype(str).str.strip().ne("")

summary_columns = st.columns(3)
summary_columns[0].metric("Candidates ranked", len(ranked))
summary_columns[1].metric("Top score", f"{ranked['screening_score'].max():.3f}")
summary_columns[2].metric("Candidates flagged", int(ranked["has_review_flag"].sum()))
st.info(explain_top_candidate(ranked, weights))

show_flagged_only = st.checkbox("Show only candidates requiring review")
view = ranked[ranked["has_review_flag"]] if show_flagged_only else ranked
shortlist_size = st.slider("Shortlist size", 1, len(view), min(5, len(view))) if not view.empty else 0
shortlist = view.head(shortlist_size).copy()

if shortlist.empty:
    st.info("No candidates have review flags in the current scope.")
else:
    visible_columns = [column for column in DISPLAY_COLUMNS if column in shortlist.columns]
    st.dataframe(
        shortlist[visible_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "screening_score": st.column_config.ProgressColumn(
                "Screening score", min_value=0.0, max_value=1.0, format="%.3f"
            ),
            "review_flags": st.column_config.TextColumn("Review flags", width="large"),
        },
    )

    chart_data = shortlist.set_index("material_id")[["screening_score"]]
    st.bar_chart(chart_data, horizontal=True)

    export_columns = [column for column in shortlist.columns if column != "has_review_flag"]
    csv_bytes = shortlist[export_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Export current shortlist",
        csv_bytes,
        "carbonsense_shortlist.csv",
        "text/csv",
        type="primary",
    )

with st.expander("Method and review limits"):
    st.markdown(
        "Scores use min-max normalization within the currently filtered dataset. "
        "Missing numeric values score zero. Density is minimized; heat of adsorption uses a target range; "
        "other active criteria are maximized. Review provenance, units, humidity stability, and evidence type "
        "before approving any shortlist."
    )
