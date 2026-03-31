"""Income & Expenses page -- detailed financial analysis with income, expenses, and summary."""

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pydantic import ValidationError

from auth import get_current_user_id
from db import (
    deactivate_fixed_expense,
    delete_income_entry,
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

now = datetime.datetime.now()

# Load all data upfront
income_entries = load_income_entries(user_id, limit=12)
expenses = load_fixed_expenses(user_id, active_only=True)

# Compute expense totals
total_monthly_expense = 0.0
total_onetime = 0.0
your_expenses = 0.0
wife_expenses = 0.0
household_expenses = 0.0

for exp in expenses:
    amount = float(exp["amount"])
    freq = exp["frequency"]
    owner = exp.get("owner", "household")
    monthly_equiv = 0.0

    if freq == "monthly":
        monthly_equiv = amount
    elif freq == "quarterly":
        monthly_equiv = amount / 3.0
    elif freq == "yearly":
        monthly_equiv = amount / 12.0
    elif freq == "one-time":
        total_onetime += amount
        continue

    total_monthly_expense += monthly_equiv
    if owner == "you":
        your_expenses += monthly_equiv
    elif owner == "wife":
        wife_expenses += monthly_equiv
    else:
        household_expenses += monthly_equiv

# Get latest income
latest_income = income_entries[0] if income_entries else None
total_income = 0.0
your_income_val = 0.0
wife_income_val = 0.0
if latest_income:
    your_income_val = float(latest_income.get("your_income", 0))
    wife_income_val = float(latest_income.get("wife_income", 0))
    total_income = your_income_val + wife_income_val

total_sip = 0.0
if fire_inputs:
    inputs = compute_derived_inputs(fire_inputs)
    total_sip = inputs.get("total_sip", 0.0)

# =====================================================================
# SECTION 1: FINANCIAL SUMMARY (at the top for quick overview)
# =====================================================================
st.header("Financial Summary")

if latest_income:
    month_name = datetime.date(2000, latest_income["month"], 1).strftime("%B")
    st.caption(f"Based on {month_name} {latest_income['year']} income + active recurring expenses")

    # Row 1: Income breakdown
    st.subheader("Income")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Your Income", f"Rs {format_indian(your_income_val)}")
    with col2:
        st.metric("Wife's Income", f"Rs {format_indian(wife_income_val)}")
    with col3:
        st.metric("Total Household Income", f"Rs {format_indian(total_income)}")

    # Row 2: Expense breakdown
    st.subheader("Monthly Outflow")
    col4, col5, col6, col7 = st.columns(4)
    with col4:
        st.metric("Fixed Expenses", f"Rs {format_indian(total_monthly_expense)}")
    with col5:
        st.metric("Total SIP", f"Rs {format_indian(total_sip)}")
    with col6:
        total_outflow = total_monthly_expense + total_sip
        st.metric("Total Outflow", f"Rs {format_indian(total_outflow)}")
    with col7:
        savings = total_income - total_outflow
        savings_rate = (savings / total_income * 100) if total_income > 0 else 0
        st.metric("Savings", f"Rs {format_indian(savings)}",
                  delta=f"{savings_rate:.1f}% savings rate")

    st.divider()

    # Row 3: Detailed breakdown chart
    st.subheader("Where Your Money Goes")

    categories = []
    amounts = []
    colors = []

    if your_expenses > 0:
        categories.append("Your Expenses")
        amounts.append(your_expenses)
        colors.append("#E5A100")
    if wife_expenses > 0:
        categories.append("Wife's Expenses")
        amounts.append(wife_expenses)
        colors.append("#C45B5B")
    if household_expenses > 0:
        categories.append("Household Expenses")
        amounts.append(household_expenses)
        colors.append("#6B7280")
    if total_sip > 0:
        categories.append("SIP Investment")
        amounts.append(total_sip)
        colors.append("#00895E")
    if savings > 0:
        categories.append("Savings/Discretionary")
        amounts.append(savings)
        colors.append("#1A3A5C")

    if categories:
        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=amounts,
            hole=0.4,
            marker_colors=colors,
            textinfo="label+percent",
            textposition="outside",
        )])
        fig.update_layout(
            showlegend=False,
            height=350,
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Row 4: Detailed numbers table
    st.subheader("Detailed Breakdown")
    breakdown_data = {
        "Category": ["Your Income", "Wife's Income", "**Total Income**", "---",
                      "Your Fixed Expenses", "Wife's Fixed Expenses", "Household Expenses",
                      "Total SIP Investment", "**Total Outflow**", "---",
                      "**Net Savings**", "Savings Rate"],
        "Amount": [
            f"Rs {format_indian(your_income_val)}",
            f"Rs {format_indian(wife_income_val)}",
            f"**Rs {format_indian(total_income)}**", "",
            f"Rs {format_indian(your_expenses)}",
            f"Rs {format_indian(wife_expenses)}",
            f"Rs {format_indian(household_expenses)}",
            f"Rs {format_indian(total_sip)}",
            f"**Rs {format_indian(total_outflow)}**", "",
            f"**Rs {format_indian(savings)}**",
            f"**{savings_rate:.1f}%**",
        ],
    }
    for row_cat, row_amt in zip(breakdown_data["Category"], breakdown_data["Amount"]):
        if row_cat == "---":
            st.divider()
        else:
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(row_cat)
            with c2:
                st.markdown(row_amt)

    if total_onetime > 0:
        st.divider()
        st.metric("One-time Expenses (not in monthly calc)", f"Rs {format_indian(total_onetime)}")

else:
    st.info("Add an income entry below to see your financial summary.")

st.divider()

# =====================================================================
# SECTION 2: INCOME LOG
# =====================================================================
st.header("Income Log")

with st.expander("Add New Income Entry", expanded=not bool(income_entries)):
    with st.form("income_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            income_month = st.selectbox(
                "Month", options=list(range(1, 13)), index=now.month - 1,
                format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"),
            )
        with col2:
            income_year = st.number_input("Year", min_value=2020, max_value=2100, value=now.year)

        col3, col4 = st.columns(2)
        with col3:
            your_income = st.number_input("Your Income", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
        with col4:
            wife_income = st.number_input("Wife's Income", min_value=0.0, value=0.0, step=1000.0, format="%.0f")

        income_notes = st.text_input("Notes", max_chars=500)
        submitted_income = st.form_submit_button("Save Income Entry", use_container_width=True)

    if submitted_income:
        try:
            entry = IncomeEntry(month=income_month, year=income_year,
                               your_income=your_income, wife_income=wife_income, notes=income_notes)
            result = save_income_entry(user_id, entry.model_dump())
            if result:
                log_audit(user_id, "save_income_entry", {"month": entry.month, "year": entry.year})
                st.success(f"Saved for {datetime.date(2000, entry.month, 1).strftime('%B')} {entry.year}.")
                st.rerun()
            else:
                st.error("Failed to save.")
        except ValidationError as exc:
            for err in exc.errors():
                st.error(f"{err['loc'][0]}: {err['msg']}")

# Income history table
if income_entries:
    st.subheader("History")

    # Column headers
    hdr = st.columns([1.5, 1, 1.5, 1.5, 1.5, 2, 0.8])
    hdr[0].markdown("**Month**")
    hdr[1].markdown("**Year**")
    hdr[2].markdown("**Your Income**")
    hdr[3].markdown("**Wife's Income**")
    hdr[4].markdown("**Total**")
    hdr[5].markdown("**Notes**")
    hdr[6].markdown("**Action**")

    for idx, e in enumerate(income_entries):
        month_name = datetime.date(2000, e["month"], 1).strftime("%B")
        total = float(e["your_income"]) + float(e["wife_income"])
        cols = st.columns([1.5, 1, 1.5, 1.5, 1.5, 2, 0.8])
        cols[0].text(month_name)
        cols[1].text(str(e["year"]))
        cols[2].text(format_indian(e["your_income"]))
        cols[3].text(format_indian(e["wife_income"]))
        cols[4].text(format_indian(total))
        cols[5].text(e.get("notes", "") or "-")
        if cols[6].button("Edit", key=f"edit_income_{idx}"):
            st.session_state["editing_income"] = {
                "month": e["month"], "year": e["year"],
                "your_income": float(e["your_income"]),
                "wife_income": float(e["wife_income"]),
                "notes": e.get("notes", ""),
            }
            st.rerun()

    # Edit form
    if "editing_income" in st.session_state:
        edit_data = st.session_state["editing_income"]
        edit_month_name = datetime.date(2000, edit_data["month"], 1).strftime("%B")
        st.markdown(f"---\n**Editing: {edit_month_name} {edit_data['year']}**")

        with st.form("edit_income_form"):
            ec1, ec2 = st.columns(2)
            with ec1:
                edit_your = st.number_input("Your Income", min_value=0.0,
                    value=edit_data["your_income"], step=1000.0, format="%.0f", key="edit_your_income")
            with ec2:
                edit_wife = st.number_input("Wife's Income", min_value=0.0,
                    value=edit_data["wife_income"], step=1000.0, format="%.0f", key="edit_wife_income")
            edit_notes = st.text_input("Notes", value=edit_data["notes"], max_chars=500, key="edit_income_notes")

            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                save_edit = st.form_submit_button("Save", use_container_width=True)
            with bc2:
                delete_edit = st.form_submit_button("Delete", use_container_width=True)
            with bc3:
                cancel_edit = st.form_submit_button("Cancel", use_container_width=True)

        if delete_edit:
            if delete_income_entry(user_id, edit_data["month"], edit_data["year"]):
                log_audit(user_id, "delete_income", {"month": edit_data["month"], "year": edit_data["year"]})
                st.success(f"Deleted {edit_month_name} {edit_data['year']}.")
                del st.session_state["editing_income"]
                st.rerun()
        if save_edit:
            result = save_income_entry(user_id, {
                "month": edit_data["month"], "year": edit_data["year"],
                "your_income": edit_your, "wife_income": edit_wife, "notes": edit_notes,
            })
            if result:
                log_audit(user_id, "edit_income", {"month": edit_data["month"], "year": edit_data["year"]})
                st.success(f"Updated {edit_month_name} {edit_data['year']}.")
                del st.session_state["editing_income"]
                st.rerun()
        if cancel_edit:
            del st.session_state["editing_income"]
            st.rerun()

st.divider()

# =====================================================================
# SECTION 3: FIXED EXPENSES
# =====================================================================
st.header("Fixed Expenses")

if expenses:
    # Column headers
    ehdr = st.columns([3, 1.5, 2, 1.5, 1])
    ehdr[0].markdown("**Expense**")
    ehdr[1].markdown("**Owner**")
    ehdr[2].markdown("**Amount**")
    ehdr[3].markdown("**Frequency**")
    ehdr[4].markdown("**Action**")

    for idx, exp in enumerate(expenses):
        ecols = st.columns([3, 1.5, 2, 1.5, 1])
        ecols[0].text(exp["name"])
        owner_label = {"you": "You", "wife": "Wife", "household": "Household"}.get(exp.get("owner", "household"), "Household")
        ecols[1].text(owner_label)
        ecols[2].text(f"Rs {format_indian(exp['amount'])}")
        freq_label = {"monthly": "Monthly", "quarterly": "Quarterly", "yearly": "Yearly", "one-time": "One-time"}.get(exp["frequency"], exp["frequency"])
        ecols[3].text(freq_label)
        if ecols[4].button("Remove", key=f"deactivate_{exp['id']}"):
            deactivate_fixed_expense(exp["id"], user_id)
            log_audit(user_id, "deactivate_fixed_expense", {"name": exp["name"]})
            st.rerun()

    # Totals
    st.divider()
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        st.metric("Monthly Recurring Total", f"Rs {format_indian(total_monthly_expense)}")
    with tcol2:
        if total_onetime > 0:
            st.metric("One-time Total", f"Rs {format_indian(total_onetime)}")
else:
    st.info("No active fixed expenses. Add one below.")

# Add new expense
with st.expander("Add New Expense"):
    with st.form("add_expense_form", clear_on_submit=True):
        ec1, ec2, ec3, ec4 = st.columns([3, 1.5, 2, 1.5])
        with ec1:
            expense_name = st.text_input("Expense Name", max_chars=100)
        with ec2:
            expense_owner = st.selectbox("Owner", options=["you", "wife", "household"],
                format_func=lambda x: {"you": "You", "wife": "Wife", "household": "Household"}[x])
        with ec3:
            expense_amount = st.number_input("Amount", min_value=0.01, value=1000.0, step=100.0, format="%.0f")
        with ec4:
            expense_frequency = st.selectbox("Frequency",
                options=["monthly", "quarterly", "yearly", "one-time"],
                format_func=lambda x: x.replace("-", " ").title())
        submitted_expense = st.form_submit_button("Add Expense", use_container_width=True)

    if submitted_expense:
        if not expense_name.strip():
            st.error("Expense name cannot be empty.")
        else:
            try:
                validated = FixedExpense(name=expense_name.strip(), amount=expense_amount, frequency=expense_frequency)
                expense_data = validated.model_dump()
                expense_data["owner"] = expense_owner
                result = save_fixed_expense(user_id, expense_data)
                if result:
                    log_audit(user_id, "save_fixed_expense", {"name": validated.name})
                    st.success(f"'{validated.name}' added.")
                    st.rerun()
            except ValidationError as exc:
                for err in exc.errors():
                    st.error(f"{err['loc'][0]}: {err['msg']}")
