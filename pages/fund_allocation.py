"""Fund Allocation page -- read-only breakdown of 10 funds (spec 7.5)."""

import pandas as pd
import streamlit as st

from auth import get_current_user_id
from db import load_fire_inputs
from engine import compute_derived_inputs, compute_fund_allocation, format_indian

st.title("Fund Allocation")

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
funds = compute_fund_allocation(inputs)

# ---------------------------------------------------------------------------
# Build DataFrame
# ---------------------------------------------------------------------------
rows = []
for f in funds:
    rows.append({
        "Fund Name": f["name"],
        "Category": f["category"].title(),
        "% of Portfolio": f"{f['pct'] * 100:.1f}%",
        "Monthly SIP (\u20b9)": format_indian(f["monthly_sip"]),
        "Account": f.get("account", ""),
    })

# Totals row
total_pct = sum(f["pct"] for f in funds)
total_sip = sum(f["monthly_sip"] for f in funds)
rows.append({
    "Fund Name": "TOTAL",
    "Category": "",
    "% of Portfolio": f"{total_pct * 100:.1f}%",
    "Monthly SIP (\u20b9)": format_indian(total_sip),
    "Account": "",
})

df = pd.DataFrame(rows)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)
