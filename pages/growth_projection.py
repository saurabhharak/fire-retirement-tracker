"""Growth Projection page -- year-by-year table and stacked area chart (spec 7.6)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import get_current_user_id
from db import load_fire_inputs
from engine import compute_derived_inputs, compute_growth_projection, format_indian

st.title("Growth Projection")

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

retirement_age = inputs["retirement_age"]

# ---------------------------------------------------------------------------
# Year-by-year table
# ---------------------------------------------------------------------------
st.subheader("Year-by-Year Projection")

table_rows = []
for row in projection:
    table_rows.append({
        "Year": row["year"],
        "Age": row["age"],
        "Monthly SIP (\u20b9)": format_indian(row["monthly_sip"]),
        "Annual Investment (\u20b9)": format_indian(row["annual_inv"]),
        "Cumulative Invested (\u20b9)": format_indian(row["cumulative"]),
        "Portfolio Value (\u20b9)": format_indian(row["portfolio"]),
        "Total Gains (\u20b9)": format_indian(row["gains"]),
        "Equity Value (\u20b9)": format_indian(row["equity_value"]),
        "Debt+Gold+Cash (\u20b9)": format_indian(row["debt_gold_cash"]),
    })

df = pd.DataFrame(table_rows)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Plotly stacked area chart
# ---------------------------------------------------------------------------
st.subheader("Portfolio Growth Over Time")

ages = [row["age"] for row in projection]
equity_values = [row["equity_value"] for row in projection]
debt_gold_cash_values = [row["debt_gold_cash"] for row in projection]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=ages,
    y=debt_gold_cash_values,
    name="Debt + Gold + Cash",
    mode="lines",
    stackgroup="one",
    line=dict(color="#636EFA"),
    fillcolor="rgba(99, 110, 250, 0.4)",
))

fig.add_trace(go.Scatter(
    x=ages,
    y=equity_values,
    name="Equity",
    mode="lines",
    stackgroup="one",
    line=dict(color="#00CC96"),
    fillcolor="rgba(0, 204, 150, 0.4)",
))

# Vertical dashed line at retirement age
fig.add_vline(
    x=retirement_age,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Retirement ({retirement_age})",
    annotation_position="top left",
)

fig.update_layout(
    xaxis_title="Age",
    yaxis_title="Portfolio Value (\u20b9)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig, use_container_width=True)
