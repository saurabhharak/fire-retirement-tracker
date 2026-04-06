"""FIRE Settings page for the FIRE Retirement Tracker.

All FIRE planning inputs are collected inside a single st.form() to
prevent widget-triggered reruns.  A preview section outside the form
shows computed blended return, real return, and years to retirement.
"""

from datetime import date

import streamlit as st
from pydantic import ValidationError

from auth import get_current_user_id
from db import load_fire_inputs, save_fire_inputs
from engine import blended_return, compute_derived_inputs, format_indian, real_return
from models import FireInputs


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("FIRE Settings")

user_id = get_current_user_id()

# Load existing values from session_state or DB on first load
if "fire_inputs" not in st.session_state or st.session_state["fire_inputs"] is None:
    existing = load_fire_inputs(user_id)
    if existing is not None:
        st.session_state["fire_inputs"] = existing

defaults = st.session_state.get("fire_inputs") or {}

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

with st.form("fire_settings"):
    # -- Personal ----------------------------------------------------------
    st.subheader("Personal")
    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        dob_default = defaults.get("dob")
        if isinstance(dob_default, str):
            dob_default = date.fromisoformat(dob_default)
        elif not isinstance(dob_default, date):
            dob_default = date(1990, 1, 1)
        dob = st.date_input("Date of Birth", value=dob_default)

    with col_p2:
        retirement_age = st.number_input(
            "Retirement Age",
            min_value=30,
            max_value=70,
            value=int(defaults.get("retirement_age", 45)),
            step=1,
        )

    with col_p3:
        life_expectancy = st.number_input(
            "Life Expectancy",
            min_value=60,
            max_value=100,
            value=int(defaults.get("life_expectancy", 85)),
            step=1,
        )

    # -- Investment --------------------------------------------------------
    st.subheader("Investment")
    col_i1, col_i2, col_i3, col_i4 = st.columns(4)

    with col_i1:
        your_sip = st.number_input(
            "Your Monthly SIP (Rs)",
            min_value=0.0,
            value=float(defaults.get("your_sip", 0)),
            step=1000.0,
            format="%.0f",
        )

    with col_i2:
        wife_sip = st.number_input(
            "Wife's Monthly SIP (Rs)",
            min_value=0.0,
            value=float(defaults.get("wife_sip", 0)),
            step=1000.0,
            format="%.0f",
        )

    with col_i3:
        step_up_pct = st.number_input(
            "Annual Step-up %",
            min_value=0.0,
            max_value=50.0,
            value=float(defaults.get("step_up_pct", 0.10)) * 100,
            step=0.5,
            format="%.1f",
            help="Entered as percentage; stored as decimal (e.g. 10 = 10%)",
        )

    with col_i4:
        existing_corpus = st.number_input(
            "Existing Corpus (Rs)",
            min_value=0.0,
            value=float(defaults.get("existing_corpus", 0)),
            step=10000.0,
            format="%.0f",
        )

    # -- Monthly Expense ---------------------------------------------------
    st.subheader("Monthly Expense")

    # Auto-calculate from fixed expenses if available
    auto_expense = 0.0
    try:
        from db import load_fixed_expenses
        expenses = load_fixed_expenses(user_id, active_only=True)
        if expenses:
            for exp in expenses:
                amt = float(exp.get("amount", 0))
                freq = exp.get("frequency", "monthly")
                if freq == "monthly":
                    auto_expense += amt
                elif freq == "quarterly":
                    auto_expense += amt / 3.0
                elif freq == "yearly":
                    auto_expense += amt / 12.0
    except Exception:
        pass

    # Use auto-calculated value if no saved value, or show both
    saved_expense = float(defaults.get("monthly_expense", 0))
    default_expense = auto_expense if saved_expense == 0 and auto_expense > 0 else saved_expense

    if auto_expense > 0:
        st.caption(f"Auto-calculated from fixed expenses: Rs {auto_expense:,.0f}/month")

    monthly_expense = st.number_input(
        "Current Monthly Expense (Rs)",
        min_value=0.0,
        value=default_expense,
        step=1000.0,
        format="%.0f",
        help="Total monthly household expenses. Auto-fills from your fixed expenses if set.",
    )

    # -- SWR ---------------------------------------------------------------
    swr = st.number_input(
        "Safe Withdrawal Rate %",
        min_value=0.1,
        max_value=10.0,
        value=float(defaults.get("swr", 0.03)) * 100,
        step=0.5,
        format="%.1f",
        help="Entered as percentage; stored as decimal (e.g. 3.0 = 3%)",
    )

    # -- Returns -----------------------------------------------------------
    st.subheader("Expected Returns")
    col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)

    with col_r1:
        equity_return = st.number_input(
            "Equity Return %",
            min_value=0.1,
            max_value=30.0,
            value=float(defaults.get("equity_return", 0.12)) * 100,
            step=0.5,
            format="%.1f",
        )

    with col_r2:
        debt_return = st.number_input(
            "Debt Return %",
            min_value=0.1,
            max_value=30.0,
            value=float(defaults.get("debt_return", 0.07)) * 100,
            step=0.5,
            format="%.1f",
        )

    with col_r3:
        precious_metals_return = st.number_input(
            "Precious Metals Return %",
            min_value=0.0,
            max_value=30.0,
            value=float(defaults.get("precious_metals_return", 0.08)) * 100,
            step=0.5,
            format="%.1f",
        )

    with col_r4:
        cash_return = st.number_input(
            "Cash Return %",
            min_value=0.0,
            max_value=30.0,
            value=float(defaults.get("cash_return", 0.04)) * 100,
            step=0.5,
            format="%.1f",
        )

    with col_r5:
        inflation = st.number_input(
            "Inflation %",
            min_value=0.1,
            max_value=20.0,
            value=float(defaults.get("inflation", 0.06)) * 100,
            step=0.5,
            format="%.1f",
        )

    # -- Allocation --------------------------------------------------------
    st.subheader("Asset Allocation")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)

    with col_a1:
        equity_pct = st.number_input(
            "Equity %",
            min_value=0.0,
            max_value=100.0,
            value=float(defaults.get("equity_pct", 0.60)) * 100,
            step=1.0,
            format="%.0f",
        )

    with col_a2:
        precious_metals_pct = st.number_input(
            "Precious Metals %",
            min_value=0.0,
            max_value=100.0,
            value=float(defaults.get("precious_metals_pct", 0.10)) * 100,
            step=1.0,
            format="%.0f",
        )

    with col_a3:
        cash_pct = st.number_input(
            "Cash %",
            min_value=0.0,
            max_value=100.0,
            value=float(defaults.get("cash_pct", 0.05)) * 100,
            step=1.0,
            format="%.0f",
        )

    # Computed debt % and total
    alloc_total = equity_pct + precious_metals_pct + cash_pct
    debt_pct_display = 100.0 - alloc_total

    with col_a4:
        st.markdown(f"**Debt %**: {debt_pct_display:.0f}%")
        st.markdown(f"**Total**: {alloc_total + max(debt_pct_display, 0):.0f}%")

    if alloc_total > 100.0:
        st.error(
            f"Equity + Precious Metals + Cash = {alloc_total:.0f}% exceeds 100%. "
            "Please reduce allocations."
        )

    # -- Submit ------------------------------------------------------------
    submitted = st.form_submit_button("Save Settings", use_container_width=True)

if submitted:
    # Convert percentages back to decimals
    data = {
        "dob": dob.isoformat(),
        "retirement_age": int(retirement_age),
        "life_expectancy": int(life_expectancy),
        "your_sip": your_sip,
        "wife_sip": wife_sip,
        "step_up_pct": step_up_pct / 100.0,
        "existing_corpus": existing_corpus,
        "monthly_expense": monthly_expense,
        "swr": swr / 100.0,
        "equity_return": equity_return / 100.0,
        "debt_return": debt_return / 100.0,
        "precious_metals_return": precious_metals_return / 100.0,
        "cash_return": cash_return / 100.0,
        "inflation": inflation / 100.0,
        "equity_pct": equity_pct / 100.0,
        "precious_metals_pct": precious_metals_pct / 100.0,
        "cash_pct": cash_pct / 100.0,
    }

    # Validate with Pydantic
    try:
        validated = FireInputs(**{**data, "dob": dob})
    except ValidationError as e:
        for err in e.errors():
            field = err.get("loc", [""])[0]
            msg = err.get("msg", "")
            st.error(f"Validation error on '{field}': {msg}")
        st.stop()

    # Upsert to DB
    result = save_fire_inputs(user_id, data)
    if result is not None:
        st.session_state["fire_inputs"] = result
        st.success("FIRE settings saved successfully!")
    else:
        st.error("Could not save settings. Please try again.")

# ---------------------------------------------------------------------------
# Preview section (outside form) -- uses currently saved values
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Preview (based on saved settings)")

saved = st.session_state.get("fire_inputs")
if saved:
    derived = compute_derived_inputs(saved)

    col_pv1, col_pv2, col_pv3 = st.columns(3)

    with col_pv1:
        br = derived["blended_return"]
        st.metric("Blended Nominal Return", f"{br * 100:.2f}%")

    with col_pv2:
        rr = derived["real_return"]
        st.metric("Real Return (Fisher)", f"{rr * 100:.2f}%")

    with col_pv3:
        ytr = derived["years_to_retirement"]
        if ytr > 0:
            st.metric("Years to Retirement", f"{ytr} years")
        else:
            st.metric("Years to Retirement", "Already retired!")
else:
    st.info("Save your settings above to see the preview.")
