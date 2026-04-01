"""Pydantic model validation tests for FIRE Retirement Tracker."""

import pytest
from pydantic import ValidationError
from app.core.models import FireInputs, IncomeEntry, FixedExpense, SipLogEntry

def test_fire_inputs_valid():
    fi = FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                    your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                    existing_corpus=0, equity_return=0.11, debt_return=0.07,
                    gold_return=0.09, cash_return=0.05, inflation=0.065,
                    swr=0.03, equity_pct=0.80, gold_pct=0.0, cash_pct=0.05,
                    monthly_expense=125000)
    assert fi.retirement_age == 40

def test_fire_inputs_allocation_over_100_rejects():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                   your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   gold_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.80, gold_pct=0.15, cash_pct=0.10,
                   monthly_expense=125000)

def test_fire_inputs_life_expectancy_must_exceed_retirement():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=60, life_expectancy=50,
                   your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   gold_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.75, gold_pct=0.05, cash_pct=0.05,
                   monthly_expense=125000)

def test_fire_inputs_negative_sip_rejects():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                   your_sip=-100, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   gold_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.75, gold_pct=0.05, cash_pct=0.05,
                   monthly_expense=125000)

def test_income_entry_valid():
    ie = IncomeEntry(month=3, year=2026, your_income=200000, wife_income=50000)
    assert ie.month == 3

def test_income_entry_month_out_of_range():
    with pytest.raises(ValidationError):
        IncomeEntry(month=13, year=2026, your_income=200000, wife_income=50000)

def test_fixed_expense_valid_with_owner():
    fe = FixedExpense(name="Netflix", amount=200, frequency="monthly", owner="you")
    assert fe.owner == "you"

def test_fixed_expense_one_time_frequency():
    fe = FixedExpense(name="Vacation", amount=50000, frequency="one-time")
    assert fe.frequency == "one-time"

def test_sip_log_entry_valid():
    sl = SipLogEntry(month=4, year=2026, planned_sip=250000, actual_invested=250000)
    assert sl.actual_invested == 250000

def test_sip_log_entry_negative_amount_rejects():
    with pytest.raises(ValidationError):
        SipLogEntry(month=4, year=2026, planned_sip=250000, actual_invested=-100)
