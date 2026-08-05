"""Regression tests for already-retired users.

The old growth-projection branch order gave a user who is already past
retirement age one full extra year of SIP contributions (year 1 was checked
before the `year <= years_to_retirement` guard), so the projected corpus was
too high.
"""
import pytest

from app.core.engine import compute_derived_inputs, compute_growth_projection


def make_inputs(dob: str, retirement_age: int, life_expectancy: int = 90) -> dict:
    raw = {
        "dob": dob,
        "retirement_age": retirement_age,
        "life_expectancy": life_expectancy,
        "your_sip": 200000,
        "wife_sip": 50000,
        "step_up_pct": 0.10,
        "existing_corpus": 100000,
        "equity_return": 0.11,
        "debt_return": 0.07,
        "precious_metals_return": 0.09,
        "cash_return": 0.05,
        "inflation": 0.065,
        "swr": 0.03,
        "equity_pct": 0.80,
        "precious_metals_pct": 0.0,
        "cash_pct": 0.05,
        "monthly_expense": 125000,
    }
    return compute_derived_inputs(raw)


def test_retired_user_has_no_sip_contributions() -> None:
    """A 76-year-old who already passed retirement age (50) must have ZERO
    contributions in every year of the projection -- not one extra year of SIP.
    """
    inputs = make_inputs("1950-01-01", retirement_age=50)
    assert inputs["years_to_retirement"] == 0

    projection = compute_growth_projection(inputs)
    for row in projection:
        assert row["annual_inv"] == 0, f"retired user contributed in year {row['year']}"
        assert row["monthly_sip"] == 0


def test_retired_user_portfolio_compounds_from_existing_corpus() -> None:
    """With zero contributions, portfolio grows purely by compounding."""
    inputs = make_inputs("1950-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    br = inputs["blended_return"]

    expected = inputs["existing_corpus"]
    assert projection[0]["portfolio"] == pytest.approx(expected)
    for row in projection[1:]:
        expected *= 1 + br
        assert row["portfolio"] == pytest.approx(expected)


def test_one_year_to_retirement_contributes_year1_then_stops() -> None:
    """User with exactly 1 year left contributes in year 1 and not after."""
    # ~49 today (born 1977), retire at 50 => 1 year to retirement.
    inputs = make_inputs("1977-01-01", retirement_age=50)
    assert inputs["years_to_retirement"] == 1

    projection = compute_growth_projection(inputs)
    assert projection[1]["annual_inv"] > 0
    for row in projection[2:]:
        assert row["annual_inv"] == 0


def test_retired_user_growth_never_has_sip() -> None:
    inputs = make_inputs("1950-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    for row in projection:
        assert row["monthly_sip"] == 0
