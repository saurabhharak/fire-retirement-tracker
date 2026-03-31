"""Income & Expenses page -- log income, manage fixed expenses (spec 7.3)."""

import datetime

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from auth import get_current_user_id
from db import (
    deactivate_fixed_expense,
    load_fire_inputs,
    load_fixed_expenses,
    load_income_entries,
    log_audit,
    save_fixed_expense,
    save_income_entry,
)
from engine import compute_derived_inputs, format_indian
from models import FixedExpense, IncomeEntry

st.title("Income & Expenses")

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

# ===================================================================
# SECTION 1: Monthly Income
# ===================================================================
st.header("Monthly Income")

now = datetime.datetime.now()

with st.form("income_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        income_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=now.month - 1,
            format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"),
        )
    with col2:
        income_year = st.number_input(
            "Year", min_value=2020, max_value=2100, value=now.year
        )

    col3, col4 = st.columns(2)
    with col3:
        your_income = st.number_input(
            "Your Income", min_value=0.0, value=0.0, step=1000.0, format="%.2f"
        )
    with col4:
        wife_income = st.number_input(
            "Wife's Income", min_value=0.0, value=0.0, step=1000.0, format="%.2f"
        )

    income_notes = st.text_input("Notes", max_chars=500)

    submitted_income = st.form_submit_button(
        "Save Income Entry", use_container_width=True
    )

if submitted_income:
    try:
        entry = IncomeEntry(
            month=income_month,
            year=income_year,
            your_income=your_income,
            wife_income=wife_income,
            notes=income_notes,
        )
        result = save_income_entry(user_id, entry.model_dump())
        if result is not None:
            log_audit(
                user_id,
                "save_income_entry",
                {"month": entry.month, "year": entry.year},
            )
            st.success(
                f"Income entry saved for {datetime.date(2000, entry.month, 1).strftime('%B')} {entry.year}."
            )
        else:
            st.error("Failed to save income entry.")
    except ValidationError as exc:
        for err in exc.errors():
            st.error(f"{err['loc'][0]}: {err['msg']}")

# Table of last 12 months
st.subheader("Recent Income Entries")
income_entries = load_income_entries(user_id, limit=12)

if income_entries:
    income_rows = []
    for e in income_entries:
        month_name = datetime.date(2000, e["month"], 1).strftime("%B")
        income_rows.append(
            {
                "Month": month_name,
                "Year": e["year"],
                "Your Income": format_indian(e["your_income"]),
                "Wife's Income": format_indian(e["wife_income"]),
                "Total": format_indian(e["your_income"] + e["wife_income"]),
                "Notes": e.get("notes", ""),
            }
        )
    st.dataframe(
        pd.DataFrame(income_rows), use_container_width=True, hide_index=True
    )
else:
    st.info("No income entries yet. Use the form above to add your first entry.")

# ===================================================================
# SECTION 2: Fixed Expenses
# ===================================================================
st.header("Fixed Expenses")

expenses = load_fixed_expenses(user_id, active_only=True)

# Display active expenses table with deactivate buttons
if expenses:
    st.subheader("Active Expenses")

    for idx, exp in enumerate(expenses):
        col_name, col_owner, col_amount, col_freq, col_action = st.columns([3, 1.5, 2, 1.5, 1])
        with col_name:
            st.text(exp["name"])
        with col_owner:
            owner_label = {"you": "You", "wife": "Wife", "household": "Household"}.get(exp.get("owner", "household"), "Household")
            st.text(owner_label)
        with col_amount:
            st.text(format_indian(exp["amount"]))
        with col_freq:
            st.text(exp["frequency"].title())
        with col_action:
            if st.button("Deactivate", key=f"deactivate_{exp['id']}"):
                result = deactivate_fixed_expense(exp["id"], user_id)
                if result is not None:
                    log_audit(
                        user_id,
                        "deactivate_fixed_expense",
                        {"expense_id": exp["id"], "name": exp["name"]},
                    )
                    st.rerun()
                else:
                    st.error("Failed to deactivate expense.")

    # Total monthly fixed outflow (excludes one-time expenses)
    total_monthly = 0.0
    total_onetime = 0.0
    for exp in expenses:
        amount = exp["amount"]
        freq = exp["frequency"]
        if freq == "monthly":
            total_monthly += amount
        elif freq == "quarterly":
            total_monthly += amount / 3.0
        elif freq == "yearly":
            total_monthly += amount / 12.0
        elif freq == "one-time":
            total_onetime += amount

    st.markdown("---")
    col_totals1, col_totals2 = st.columns(2)
    with col_totals1:
        st.metric("Monthly Recurring Outflow", f"Rs {format_indian(total_monthly)}")
    with col_totals2:
        if total_onetime > 0:
            st.metric("One-time Expenses", f"Rs {format_indian(total_onetime)}")
else:
    st.info("No active fixed expenses.")
    total_monthly = 0.0

# Add new expense form
st.subheader("Add New Expense")
with st.form("add_expense_form", clear_on_submit=True):
    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns([3, 1.5, 2, 1.5])
    with exp_col1:
        expense_name = st.text_input("Expense Name", max_chars=100)
    with exp_col2:
        expense_owner = st.selectbox(
            "Owner", options=["you", "wife", "household"],
            format_func=lambda x: {"you": "You", "wife": "Wife", "household": "Household"}[x]
        )
    with exp_col3:
        expense_amount = st.number_input(
            "Amount", min_value=0.01, value=1000.0, step=100.0, format="%.2f"
        )
    with exp_col4:
        expense_frequency = st.selectbox(
            "Frequency", options=["monthly", "quarterly", "yearly", "one-time"],
            format_func=lambda x: {"monthly": "Monthly", "quarterly": "Quarterly", "yearly": "Yearly", "one-time": "One-time"}[x]
        )

    submitted_expense = st.form_submit_button(
        "Add Expense", use_container_width=True
    )

if submitted_expense:
    if not expense_name.strip():
        st.error("Expense name cannot be empty.")
    else:
        try:
            validated = FixedExpense(
                name=expense_name.strip(),
                amount=expense_amount,
                frequency=expense_frequency,
            )
            expense_data = validated.model_dump()
            expense_data["owner"] = expense_owner  # owner is not in Pydantic model
            result = save_fixed_expense(user_id, expense_data)
            if result is not None:
                log_audit(
                    user_id,
                    "save_fixed_expense",
                    {"name": validated.name, "amount": validated.amount},
                )
                st.success(f"Expense '{validated.name}' added.")
                st.rerun()
            else:
                st.error("Failed to save expense.")
        except ValidationError as exc:
            for err in exc.errors():
                st.error(f"{err['loc'][0]}: {err['msg']}")

# ===================================================================
# SECTION 3: Summary Card
# ===================================================================
st.header("Monthly Summary")

# Check if we have income data for the current month
current_month_income = None
for e in income_entries:
    if e["month"] == now.month and e["year"] == now.year:
        current_month_income = e
        break

if current_month_income is not None and fire_inputs is not None:
    total_income = (
        current_month_income["your_income"] + current_month_income["wife_income"]
    )

    # Compute total SIP from FIRE settings
    inputs = compute_derived_inputs(fire_inputs)
    total_sip = inputs.get("total_sip", 0.0)

    discretionary = total_income - total_monthly - total_sip

    col_inc, col_exp, col_sip, col_disc = st.columns(4)
    with col_inc:
        st.metric("Total Income", f"Rs {format_indian(total_income)}")
    with col_exp:
        st.metric("Fixed Expenses", f"Rs {format_indian(total_monthly)}")
    with col_sip:
        st.metric("Total SIP", f"Rs {format_indian(total_sip)}")
    with col_disc:
        st.metric(
            "Discretionary",
            f"Rs {format_indian(discretionary)}",
            delta=f"Rs {format_indian(discretionary)}",
            delta_color="normal" if discretionary >= 0 else "inverse",
        )
elif current_month_income is None:
    st.info(
        f"No income data for {datetime.date(2000, now.month, 1).strftime('%B')} {now.year}. "
        "Add an income entry above to see your monthly summary."
    )
elif fire_inputs is None:
    st.info("Configure your FIRE Settings to see the full monthly summary.")
