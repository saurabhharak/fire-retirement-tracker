"""Retirement Analysis page -- metrics, 3-bucket strategy, SWR comparison (spec 7.7)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import get_current_user_id
from config import BUCKET_PERCENTAGES, SWR_SCENARIOS, SWR_VERDICTS
from db import load_fire_inputs
from engine import (
    compute_derived_inputs,
    compute_growth_projection,
    compute_retirement_metrics,
    format_indian,
)

st.title("Retirement Analysis")

# ---------------------------------------------------------------------------
# Load inputs from session_state or DB
# ---------------------------------------------------------------------------
fire_inputs = st.session_state.get("fire_inputs")

if fire_inputs is None:
    try:
        user_id = get_current_user_id()
        fire_inputs = load_fire_inputs(user_id)
        if fire_inputs is not None:
            st.session_state["fire_inputs"] = fire_inputs
    except RuntimeError:
        fire_inputs = None

if fire_inputs is None:
    st.info("Configure your FIRE Settings first.")
    st.stop()

# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------
inputs = compute_derived_inputs(fire_inputs)
projection = compute_growth_projection(inputs)

# Corpus at retirement = portfolio value at year == years_to_retirement
years_to_retirement = inputs["years_to_retirement"]
retirement_row = projection[years_to_retirement] if years_to_retirement < len(projection) else projection[-1]
corpus = retirement_row["portfolio"]

metrics = compute_retirement_metrics(inputs, corpus)

# ---------------------------------------------------------------------------
# Key Metrics
# ---------------------------------------------------------------------------
st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Corpus at Retirement", f"\u20b9 {format_indian(metrics['corpus'])}")
with col2:
    st.metric("Annual Expense (at retirement)", f"\u20b9 {format_indian(metrics['annual_expense'])}")
with col3:
    st.metric("Monthly SWP Income", f"\u20b9 {format_indian(metrics['monthly_swp'])}")
with col4:
    st.metric("Monthly Expense (at retirement)", f"\u20b9 {format_indian(metrics['monthly_expense'])}")

col5, col6, col7 = st.columns(3)
with col5:
    surplus = metrics["surplus"]
    label = "Surplus" if surplus >= 0 else "Deficit"
    st.metric(f"Monthly {label}", f"\u20b9 {format_indian(surplus)}")
with col6:
    funded_ratio = metrics["funded_ratio"]
    st.metric("Funded Ratio", f"{funded_ratio:.1%}")
with col7:
    st.metric("Required Corpus", f"\u20b9 {format_indian(metrics['required_corpus'])}")

st.divider()

# ---------------------------------------------------------------------------
# 3-Bucket Strategy
# ---------------------------------------------------------------------------
st.subheader("3-Bucket Strategy")

buckets = metrics["buckets"]
bucket_names = [b["name"] for b in buckets]
bucket_amounts = [b["amount"] for b in buckets]
bucket_pcts = [b["pct"] for b in buckets]
bucket_coverage = [b["coverage_years"] for b in buckets]

# Horizontal bar chart
fig_buckets = go.Figure()

fig_buckets.add_trace(go.Bar(
    y=bucket_names,
    x=bucket_amounts,
    orientation="h",
    marker_color=["#636EFA", "#EF553B", "#00CC96"],
    text=[
        f"\u20b9 {format_indian(amt)} ({pct:.0%}) - {cov:.1f} yrs"
        for amt, pct, cov in zip(bucket_amounts, bucket_pcts, bucket_coverage)
    ],
    textposition="auto",
))

fig_buckets.update_layout(
    xaxis_title="Amount (\u20b9)",
    yaxis_title="",
    showlegend=False,
    height=250,
)

st.plotly_chart(fig_buckets, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# SWR Comparison Table
# ---------------------------------------------------------------------------
st.subheader("Safe Withdrawal Rate (SWR) Comparison")

swr_rows = []
for s in metrics["swr_scenarios"]:
    vs_expense = s["vs_expense"]
    vs_label = f"\u20b9 {format_indian(vs_expense)}" if vs_expense >= 0 else f"-\u20b9 {format_indian(abs(vs_expense))}"
    swr_rows.append({
        "SWR": f"{s['rate'] * 100:.1f}%",
        "Annual Withdrawal (\u20b9)": format_indian(s["annual"]),
        "Monthly Income (\u20b9)": format_indian(s["monthly"]),
        "vs Monthly Expense": vs_label,
        "Verdict": s["verdict"],
    })

df_swr = pd.DataFrame(swr_rows)

st.dataframe(
    df_swr,
    use_container_width=True,
    hide_index=True,
)
