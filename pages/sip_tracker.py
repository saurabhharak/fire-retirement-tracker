"""SIP Tracker page -- log and compare planned vs actual SIPs (spec 7.8)."""

import datetime

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from auth import get_current_user_id
from config import DEBT_SUB_SPLITS, EQUITY_SUB_SPLITS
from db import load_fire_inputs, load_sip_logs, log_audit, save_sip_log
from engine import compute_derived_inputs, compute_monthly_sips, format_indian
from models import SipLogEntry

st.title("SIP Tracker")

# ---------------------------------------------------------------------------
# Auth & inputs
# ---------------------------------------------------------------------------
try:
    user_id = get_current_user_id()
except RuntimeError:
    st.error("Please log in to access this page.")
    st.stop()

fire_inputs = st.session_state.get("fire_inputs")
if fire_inputs is None:
    fire_inputs = load_fire_inputs(user_id)
    if fire_inputs is not None:
        st.session_state["fire_inputs"] = fire_inputs

if fire_inputs is None:
    st.info("Configure your FIRE Settings first to use the SIP Tracker.")
    st.stop()

inputs = compute_derived_inputs(fire_inputs)

# ===================================================================
# SECTION 1: Monthly SIP Log Form
# ===================================================================
st.header("Log Monthly SIP")

now = datetime.datetime.now()

# Build fund name list for the optional per-fund breakdown
fund_names = (
    list(EQUITY_SUB_SPLITS.keys())
    + list(DEBT_SUB_SPLITS.keys())
    + ["Gold", "Cash"]
)

with st.form("sip_log_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        sip_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=now.month - 1,
            format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"),
        )
    with col2:
        sip_year = st.number_input(
            "Year", min_value=2020, max_value=2100, value=now.year
        )

    actual_invested = st.number_input(
        "Actual Amount Invested",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        format="%.2f",
    )

    sip_notes = st.text_input("Notes", max_chars=500)

    # Optional per-fund breakdown
    with st.expander("Per-Fund Breakdown (optional)"):
        fund_amounts = {}
        cols = st.columns(2)
        for idx, fund_name in enumerate(fund_names):
            with cols[idx % 2]:
                fund_amounts[fund_name] = st.number_input(
                    fund_name,
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    format="%.2f",
                    key=f"fund_{fund_name}",
                )

    submitted_sip = st.form_submit_button(
        "Save SIP Log Entry", use_container_width=True
    )

if submitted_sip:
    # Compute the planned SIP for the selected month
    monthly_sips = compute_monthly_sips(inputs)

    # Determine which month index this corresponds to.
    # Month 1 of the schedule is the current calendar month at the time
    # FIRE settings were created. We use a simple approach: compute the
    # offset in months from the start date (today's year/month as month 1).
    # For simplicity, look up the first month's value (step-up applied yearly).
    start_year = now.year
    start_month = now.month
    month_offset = (sip_year - start_year) * 12 + (sip_month - start_month)

    # Clamp to valid range
    if month_offset < 0:
        planned_sip = monthly_sips[0]
    elif month_offset >= len(monthly_sips):
        planned_sip = monthly_sips[-1]
    else:
        planned_sip = monthly_sips[month_offset]

    try:
        entry = SipLogEntry(
            month=sip_month,
            year=sip_year,
            planned_sip=planned_sip,
            actual_invested=actual_invested,
            notes=sip_notes,
        )

        # Build funds list from per-fund breakdown
        funds = []
        for fund_name, amount in fund_amounts.items():
            if amount > 0:
                funds.append({"fund_name": fund_name, "amount": amount})

        save_data = entry.model_dump()
        if funds:
            save_data["funds"] = funds

        result = save_sip_log(user_id, save_data)
        if result is not None:
            log_audit(
                user_id,
                "save_sip_log",
                {"month": entry.month, "year": entry.year},
            )
            st.success(
                f"SIP log saved for "
                f"{datetime.date(2000, entry.month, 1).strftime('%B')} {entry.year}."
            )
        else:
            st.error("Failed to save SIP log entry.")
    except ValidationError as exc:
        for err in exc.errors():
            st.error(f"{err['loc'][0]}: {err['msg']}")

# ===================================================================
# SECTION 2: Past SIP Entries Table
# ===================================================================
st.header("SIP History")

sip_logs = load_sip_logs(user_id)

if sip_logs:
    rows = []
    total_planned = 0.0
    total_actual = 0.0

    for log in sip_logs:
        planned = log.get("planned_sip", 0.0) or 0.0
        actual = log.get("actual_invested", 0.0) or 0.0
        diff = actual - planned
        month_name = datetime.date(2000, log["month"], 1).strftime("%B")

        total_planned += planned
        total_actual += actual

        rows.append(
            {
                "Month": month_name,
                "Year": log["year"],
                "Planned SIP": format_indian(planned),
                "Actual Invested": format_indian(actual),
                "Difference": diff,
                "Notes": log.get("notes", ""),
            }
        )

    # Add running totals row
    rows.append(
        {
            "Month": "TOTAL",
            "Year": "",
            "Planned SIP": format_indian(total_planned),
            "Actual Invested": format_indian(total_actual),
            "Difference": total_actual - total_planned,
            "Notes": "",
        }
    )

    df = pd.DataFrame(rows)

    # Keep raw numeric differences for styling, then format for display
    raw_diffs = df["Difference"].tolist()

    # Format the Difference column as Indian notation for display
    df["Difference"] = [
        format_indian(v) if isinstance(v, (int, float)) else v
        for v in raw_diffs
    ]

    def color_difference(val):
        """Return CSS color based on whether the formatted string starts with '-'."""
        s = str(val)
        if s.startswith("-"):
            return "color: red; font-weight: bold"
        return "color: green; font-weight: bold"

    # Apply styling to the Difference column
    styled_df = df.style.map(
        color_difference, subset=["Difference"]
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No SIP log entries yet. Use the form above to log your first SIP.")
