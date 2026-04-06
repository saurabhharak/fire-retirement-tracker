"""Edge-case tests for the FIRE calculation engine."""

import pytest
from app.core.engine import (
    compute_derived_inputs, compute_growth_projection,
    compute_retirement_metrics, compute_fund_allocation,
    compute_monthly_sips, blended_return, real_return,
)

# Test blended_return
def test_blended_return_standard():
    inputs = {"equity_pct": 0.75, "debt_pct": 0.15, "precious_metals_pct": 0.05, "cash_pct": 0.05,
              "equity_return": 0.11, "debt_return": 0.07, "precious_metals_return": 0.09, "cash_return": 0.05}
    assert abs(blended_return(inputs) - 0.10) < 0.001

def test_blended_return_all_equity():
    inputs = {"equity_pct": 1.0, "debt_pct": 0.0, "precious_metals_pct": 0.0, "cash_pct": 0.0,
              "equity_return": 0.11, "debt_return": 0.07, "precious_metals_return": 0.09, "cash_return": 0.05}
    assert abs(blended_return(inputs) - 0.11) < 0.001

# Test real_return (Fisher equation)
def test_real_return_fisher():
    r = real_return(0.10, 0.065)
    assert abs(r - 0.03286) < 0.001

def test_real_return_zero_inflation():
    assert abs(real_return(0.10, 0.0) - 0.10) < 0.001

# Test compute_derived_inputs
def test_derived_inputs_computes_all_fields():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    assert d["total_sip"] == 250000
    assert abs(d["debt_pct"] - 0.15) < 1e-10
    assert "blended_return" in d
    assert "real_return" in d
    assert "current_age" in d
    assert "years_to_retirement" in d

def test_derived_inputs_zero_sip():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 0, "wife_sip": 0, "step_up_pct": 0.10,
           "existing_corpus": 1000000, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    assert d["total_sip"] == 0

# Test growth projection
def test_growth_projection_returns_41_rows():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 25000, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    proj = compute_growth_projection(d)
    assert len(proj) == 41

def test_growth_projection_year0_no_investment():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 100000, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    proj = compute_growth_projection(d)
    assert proj[0]["annual_inv"] == 0
    assert proj[0]["portfolio"] == 100000

def test_growth_projection_year1_base_sip():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    proj = compute_growth_projection(d)
    assert proj[1]["monthly_sip"] == 250000  # Base SIP, no step-up

def test_growth_projection_post_retirement_sip_zero():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    ytr = d["years_to_retirement"]
    proj = compute_growth_projection(d)
    for row in proj[ytr+1:]:
        assert row["monthly_sip"] == 0

# Test fund allocation
def test_fund_allocation_10_funds():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    alloc = compute_fund_allocation(d)
    assert len(alloc) == 10

def test_fund_allocation_sums_to_total_sip():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    alloc = compute_fund_allocation(d)
    total = sum(f["monthly_sip"] for f in alloc)
    assert abs(total - 250000) < 1

# Test monthly SIPs
def test_monthly_sips_192_months():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    sips = compute_monthly_sips(d)
    assert len(sips) == 192

# Test retirement metrics
def test_retirement_metrics_has_required_fields():
    raw = {"dob": "1997-07-11", "retirement_age": 40, "life_expectancy": 90,
           "your_sip": 200000, "wife_sip": 50000, "step_up_pct": 0.10,
           "existing_corpus": 0, "equity_return": 0.11, "debt_return": 0.07,
           "precious_metals_return": 0.09, "cash_return": 0.05, "inflation": 0.065,
           "swr": 0.03, "equity_pct": 0.80, "precious_metals_pct": 0.0, "cash_pct": 0.05,
           "monthly_expense": 125000}
    d = compute_derived_inputs(raw)
    proj = compute_growth_projection(d)
    corpus = proj[d["years_to_retirement"]]["portfolio"]
    m = compute_retirement_metrics(d, corpus)
    assert "corpus" in m
    assert "funded_ratio" in m
    assert "monthly_swp" in m
    assert "surplus" in m
    assert "buckets" in m
    assert "swr_scenarios" in m
