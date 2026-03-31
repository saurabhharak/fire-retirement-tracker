"""Dashboard (Home) page for the FIRE Retirement Tracker.

Shows FIRE countdown, income/expense metric cards, FIRE metric cards,
and a portfolio growth area chart.
"""

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from auth import get_current_user_id
from config import BUCKET_PERCENTAGES, SWR_SCENARIOS
from db import load_fire_inputs, load_fixed_expenses, load_income_entries
from engine import (
    compute_derived_inputs,
    compute_growth_projection,
    compute_retirement_metrics,
    format_indian,
)


def _compute_monthly_expense_total(expenses: list[dict]) -> float:
    """Sum all active fixed expenses normalized to a monthly amount."""
    total = 0.0
    for exp in expenses:
        amount = float(exp.get("amount", 0))
        freq = exp.get("frequency", "monthly")
        if freq == "monthly":
            total += amount
        elif freq == "quarterly":
            total += amount / 3.0
        elif freq == "yearly":
            total += amount / 12.0
    return total


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

user_id = get_current_user_id()

# Load FIRE inputs from session_state or DB
fire_inputs = st.session_state.get("fire_inputs")
if fire_inputs is None:
    fire_inputs = load_fire_inputs(user_id)
    if fire_inputs is not None:
        st.session_state["fire_inputs"] = fire_inputs

if fire_inputs is None:
    st.title("Dashboard")
    st.info("Set up your FIRE plan in Settings first.")
    st.stop()

# Compute derived values and projections
inputs = compute_derived_inputs(fire_inputs)
projection = compute_growth_projection(inputs)

years_to_ret = max(inputs["years_to_retirement"], 0)
retirement_row = None
for row in projection:
    if row["year"] == years_to_ret:
        retirement_row = row
        break
if retirement_row is None:
    retirement_row = projection[-1]

corpus_at_retirement = retirement_row["portfolio"]
metrics = compute_retirement_metrics(inputs, corpus_at_retirement)

# ---------------------------------------------------------------------------
# FIRE Countdown
# ---------------------------------------------------------------------------

st.title("Dashboard")

years_part = years_to_ret
# Approximate months from fractional age difference
dob = inputs["dob"] if isinstance(inputs["dob"], date) else date.fromisoformat(inputs["dob"])
today = date.today()
total_months_lived = (today.year - dob.year) * 12 + (today.month - dob.month)
retirement_month_total = inputs["retirement_age"] * 12
months_remaining = max(retirement_month_total - total_months_lived, 0)
years_display = months_remaining // 12
months_display = months_remaining % 12

if months_remaining > 0:
    st.subheader(f"{years_display} years {months_display} months to FIRE")
    # Total working months from current age to retirement
    total_working_months = inputs["retirement_age"] * 12 - (inputs["current_age"] * 12)
    elapsed_months = total_working_months - months_remaining
    progress = min(max(elapsed_months / total_working_months, 0.0), 1.0) if total_working_months > 0 else 1.0
    st.progress(progress)
else:
    st.subheader("You have reached FIRE!")
    st.progress(1.0)

# ---------------------------------------------------------------------------
# Income Row -- 4 metric cards
# ---------------------------------------------------------------------------

st.markdown("### Income Overview")

# Load income and expense data
income_entries = load_income_entries(user_id, limit=1)
fixed_expenses = load_fixed_expenses(user_id)

current_month = today.month
current_year = today.year

this_month_income = 0.0
if income_entries:
    latest = income_entries[0]
    if latest.get("month") == current_month and latest.get("year") == current_year:
        this_month_income = float(latest.get("your_income", 0)) + float(
            latest.get("wife_income", 0)
        )

fixed_expense_total = _compute_monthly_expense_total(fixed_expenses)
monthly_savings = this_month_income - fixed_expense_total
savings_rate = (monthly_savings / this_month_income * 100) if this_month_income > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("This Month's Income", f"Rs {format_indian(this_month_income)}")
with col2:
    st.metric("Fixed Expenses", f"Rs {format_indian(fixed_expense_total)}")
with col3:
    st.metric("Monthly Savings", f"Rs {format_indian(monthly_savings)}")
with col4:
    st.metric("Savings Rate", f"{savings_rate:.1f}%")

# ---------------------------------------------------------------------------
# FIRE Row -- 4 metric cards
# ---------------------------------------------------------------------------

st.markdown("### FIRE Metrics")

funded_ratio = metrics["funded_ratio"]
# Color-code funded ratio
if funded_ratio >= 1.0:
    fr_color = "#00895E"  # Prosperity green
    fr_label = "On Track"
elif funded_ratio >= 0.75:
    fr_color = "#E5A100"  # Amber gold (warning without negativity)
    fr_label = "Close"
else:
    fr_color = "#C45B5B"  # Muted coral (avoids aggressive red - Vastu/Feng Shui)
    fr_label = "Behind"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "Projected Corpus",
        f"Rs {format_indian(corpus_at_retirement)}",
    )
with col2:
    st.metric(
        "Required Corpus",
        f"Rs {format_indian(metrics['required_corpus'])}",
    )
with col3:
    # SECURITY: Only hardcoded values used below. Never inject user-controlled data.
    st.markdown(
        f"**Funded Ratio**  \n"
        f"<span style='color:{fr_color}; font-size:1.8rem; font-weight:600;'>"
        f"{funded_ratio:.1%}</span>  \n"
        f"<span style='color:{fr_color};'>{fr_label}</span>",
        unsafe_allow_html=True,
    )
with col4:
    monthly_swp = metrics["monthly_swp"]
    monthly_expense_ret = metrics["monthly_expense"]
    delta = monthly_swp - monthly_expense_ret
    st.metric(
        "Monthly SWP vs Expense",
        f"Rs {format_indian(monthly_swp)}",
        delta=f"Rs {format_indian(delta)} {'surplus' if delta >= 0 else 'deficit'}",
        delta_color="normal" if delta >= 0 else "inverse",
    )

# ---------------------------------------------------------------------------
# Growth Chart -- Plotly stacked area
# ---------------------------------------------------------------------------

st.markdown("### Portfolio Growth Projection")

years = [r["year"] for r in projection]
equity_values = [r["equity_value"] for r in projection]
other_values = [r["debt_gold_cash"] for r in projection]
ages = [r["age"] for r in projection]

# Build x-axis labels with age
x_labels = [f"Yr {y} (Age {a})" for y, a in zip(years, ages)]

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=x_labels,
        y=other_values,
        name="Debt + Gold + Cash",
        fill="tozeroy",
        mode="lines",
        line=dict(width=0.5, color="rgb(55, 126, 184)"),
        fillcolor="rgba(55, 126, 184, 0.5)",
    )
)

fig.add_trace(
    go.Scatter(
        x=x_labels,
        y=[e + o for e, o in zip(equity_values, other_values)],
        name="Equity",
        fill="tonexty",
        mode="lines",
        line=dict(width=0.5, color="rgb(228, 26, 28)"),
        fillcolor="rgba(228, 26, 28, 0.4)",
    )
)

fig.update_layout(
    title="Portfolio Growth (Stacked Area)",
    xaxis_title="Year",
    yaxis_title="Portfolio Value (Rs)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=500,
)

# Format y-axis with Indian notation via custom tick text
fig.update_yaxes(tickformat=",")

st.plotly_chart(fig, use_container_width=True)
