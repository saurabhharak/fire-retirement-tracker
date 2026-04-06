"""Pydantic model validation tests for FIRE Retirement Tracker."""

import pytest
from pydantic import ValidationError
from datetime import date, timedelta
from app.core.models import (
    FireInputs,
    IncomeEntry,
    FixedExpense,
    SipLogEntry,
    GoldPurchase,
    GoldPurchaseUpdate,
    PreciousMetalPurchase,
    PreciousMetalPurchaseUpdate,
)

def test_fire_inputs_valid():
    fi = FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                    your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                    existing_corpus=0, equity_return=0.11, debt_return=0.07,
                    precious_metals_return=0.09, cash_return=0.05, inflation=0.065,
                    swr=0.03, equity_pct=0.80, precious_metals_pct=0.0, cash_pct=0.05,
                    monthly_expense=125000)
    assert fi.retirement_age == 40

def test_fire_inputs_allocation_over_100_rejects():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                   your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   precious_metals_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.80, precious_metals_pct=0.15, cash_pct=0.10,
                   monthly_expense=125000)

def test_fire_inputs_life_expectancy_must_exceed_retirement():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=60, life_expectancy=50,
                   your_sip=200000, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   precious_metals_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.75, precious_metals_pct=0.05, cash_pct=0.05,
                   monthly_expense=125000)

def test_fire_inputs_negative_sip_rejects():
    with pytest.raises(ValidationError):
        FireInputs(dob="1997-07-11", retirement_age=40, life_expectancy=90,
                   your_sip=-100, wife_sip=50000, step_up_pct=0.10,
                   existing_corpus=0, equity_return=0.11, debt_return=0.07,
                   precious_metals_return=0.09, cash_return=0.05, inflation=0.065,
                   swr=0.03, equity_pct=0.75, precious_metals_pct=0.05, cash_pct=0.05,
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
    fe = FixedExpense(name="Vacation", amount=50000, frequency="one-time", expense_month=4, expense_year=2026)
    assert fe.frequency == "one-time"

def test_fixed_expense_one_time_requires_month_year():
    with pytest.raises(ValidationError):
        FixedExpense(name="Vacation", amount=50000, frequency="one-time")

def test_fixed_expense_one_time_requires_both_month_and_year():
    with pytest.raises(ValidationError):
        FixedExpense(name="Vacation", amount=50000, frequency="one-time", expense_month=4)

def test_fixed_expense_monthly_no_month_year_ok():
    fe = FixedExpense(name="Netflix", amount=200, frequency="monthly")
    assert fe.expense_month is None
    assert fe.expense_year is None

def test_sip_log_entry_valid():
    sl = SipLogEntry(month=4, year=2026, planned_sip=250000, actual_invested=250000)
    assert sl.actual_invested == 250000

def test_sip_log_entry_negative_amount_rejects():
    with pytest.raises(ValidationError):
        SipLogEntry(month=4, year=2026, planned_sip=250000, actual_invested=-100)


# ---------------------------------------------------------------------------
# GoldPurchase model tests
# ---------------------------------------------------------------------------

def test_gold_purchase_valid():
    gp = GoldPurchase(purchase_date="2026-03-15", weight_grams=10.0,
                      price_per_gram=13500.0, purity="24K", owner="you")
    assert gp.purity == "24K"
    assert gp.owner == "you"

def test_gold_purchase_defaults():
    gp = GoldPurchase(purchase_date="2026-03-15", weight_grams=5.0,
                      price_per_gram=12000.0, purity="22K")
    assert gp.owner == "household"
    assert gp.notes == ""

def test_gold_purchase_date_before_2000_rejects():
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date="1999-12-31", weight_grams=10.0,
                     price_per_gram=5000.0, purity="24K")

def test_gold_purchase_future_date_rejects():
    future = date.today() + timedelta(days=30)
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date=future.isoformat(), weight_grams=10.0,
                     price_per_gram=13500.0, purity="24K")

def test_gold_purchase_weight_exceeds_upper_bound_rejects():
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date="2026-03-15", weight_grams=100001,
                     price_per_gram=13500.0, purity="24K")

def test_gold_purchase_price_exceeds_upper_bound_rejects():
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date="2026-03-15", weight_grams=10.0,
                     price_per_gram=1000001, purity="24K")

def test_gold_purchase_zero_weight_rejects():
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date="2026-03-15", weight_grams=0,
                     price_per_gram=13500.0, purity="24K")

def test_gold_purchase_invalid_purity_rejects():
    with pytest.raises(ValidationError):
        GoldPurchase(purchase_date="2026-03-15", weight_grams=10.0,
                     price_per_gram=13500.0, purity="14K")

def test_gold_purchase_update_partial_fields():
    gpu = GoldPurchaseUpdate(weight_grams=15.0)
    assert gpu.weight_grams == 15.0
    assert gpu.purity is None
    assert gpu.owner is None

def test_gold_purchase_update_date_validator():
    with pytest.raises(ValidationError):
        GoldPurchaseUpdate(purchase_date="1999-01-01")


# ---------------------------------------------------------------------------
# PreciousMetalPurchase model tests
# ---------------------------------------------------------------------------

def test_precious_metal_purchase_gold_valid():
    p = PreciousMetalPurchase(
        metal_type="gold",
        purchase_date="2026-03-15",
        weight_grams=10.0,
        price_per_gram=8500.0,
        purity="22K",
        owner="you",
    )
    assert p.metal_type == "gold"
    assert p.purity == "22K"
    assert p.owner == "you"


def test_precious_metal_purchase_silver_valid():
    p = PreciousMetalPurchase(
        metal_type="silver",
        purchase_date="2026-01-10",
        weight_grams=100.0,
        price_per_gram=95.0,
        purity="999",
    )
    assert p.metal_type == "silver"
    assert p.purity == "999"
    assert p.owner == "household"
    assert p.notes == ""


def test_precious_metal_purchase_platinum_valid():
    p = PreciousMetalPurchase(
        metal_type="platinum",
        purchase_date="2025-06-01",
        weight_grams=5.0,
        price_per_gram=3200.0,
        purity="950",
    )
    assert p.metal_type == "platinum"
    assert p.purity == "950"


def test_precious_metal_purchase_wrong_purity_for_gold_rejects():
    """Silver purity '999' is invalid for gold."""
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date="2026-01-01",
            weight_grams=10.0,
            price_per_gram=8000.0,
            purity="999",
        )


def test_precious_metal_purchase_wrong_purity_for_silver_rejects():
    """Gold purity '24K' is invalid for silver."""
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="silver",
            purchase_date="2026-01-01",
            weight_grams=50.0,
            price_per_gram=100.0,
            purity="24K",
        )


def test_precious_metal_purchase_wrong_purity_for_platinum_rejects():
    """'22K' is not a valid platinum purity."""
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="platinum",
            purchase_date="2026-01-01",
            weight_grams=5.0,
            price_per_gram=3000.0,
            purity="22K",
        )


def test_precious_metal_purchase_date_before_2000_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date="1999-12-31",
            weight_grams=10.0,
            price_per_gram=5000.0,
            purity="24K",
        )


def test_precious_metal_purchase_future_date_rejects():
    future = date.today() + timedelta(days=30)
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date=future.isoformat(),
            weight_grams=10.0,
            price_per_gram=8000.0,
            purity="24K",
        )


def test_precious_metal_purchase_zero_weight_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date="2026-01-01",
            weight_grams=0,
            price_per_gram=8000.0,
            purity="24K",
        )


def test_precious_metal_purchase_invalid_metal_type_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="copper",
            purchase_date="2026-01-01",
            weight_grams=10.0,
            price_per_gram=8000.0,
            purity="24K",
        )


def test_precious_metal_purchase_invalid_owner_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date="2026-01-01",
            weight_grams=10.0,
            price_per_gram=8000.0,
            purity="24K",
            owner="son",
        )


def test_precious_metal_purchase_notes_too_long_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchase(
            metal_type="gold",
            purchase_date="2026-01-01",
            weight_grams=10.0,
            price_per_gram=8000.0,
            purity="24K",
            notes="x" * 501,
        )


# ---------------------------------------------------------------------------
# PreciousMetalPurchaseUpdate model tests
# ---------------------------------------------------------------------------

def test_precious_metal_purchase_update_all_optional():
    u = PreciousMetalPurchaseUpdate()
    assert u.weight_grams is None
    assert u.purity is None
    assert u.owner is None
    assert u.purchase_date is None


def test_precious_metal_purchase_update_partial_fields():
    u = PreciousMetalPurchaseUpdate(weight_grams=20.0, owner="wife")
    assert u.weight_grams == 20.0
    assert u.owner == "wife"
    assert u.purity is None


def test_precious_metal_purchase_update_invalid_date_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchaseUpdate(purchase_date="1990-01-01")


def test_precious_metal_purchase_update_future_date_rejects():
    future = date.today() + timedelta(days=10)
    with pytest.raises(ValidationError):
        PreciousMetalPurchaseUpdate(purchase_date=future.isoformat())


def test_precious_metal_purchase_update_zero_weight_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchaseUpdate(weight_grams=0)


def test_precious_metal_purchase_update_invalid_owner_rejects():
    with pytest.raises(ValidationError):
        PreciousMetalPurchaseUpdate(owner="joint")
