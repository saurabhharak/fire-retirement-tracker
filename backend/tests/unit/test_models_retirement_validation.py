"""Regression tests: FireInputs must reject invalid retirement age combos.

Previously the model allowed:
- retirement_age <= current_age (a 50-year-old could set retirement_age 19,
  producing a negative years_to_retirement and the negative-index corpus bug)
- life_expectancy <= retirement_age (already covered, kept here as regression)
"""
import pytest
from pydantic import ValidationError

from app.core.models import FireInputs


def make_valid_inputs(**overrides) -> dict:
    base = {
        "dob": "1997-07-11",
        "retirement_age": 50,
        "life_expectancy": 90,
        "your_sip": 200000,
        "wife_sip": 50000,
        "step_up_pct": 0.10,
        "existing_corpus": 0,
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
    base.update(overrides)
    return base


def test_valid_inputs_accept() -> None:
    FireInputs(**make_valid_inputs())


def test_retirement_age_must_exceed_current_age() -> None:
    # Born 1950 => ~76 today. Retirement age 50 is in the past => reject.
    data = make_valid_inputs(dob="1950-01-01", retirement_age=50)
    with pytest.raises(ValidationError):
        FireInputs(**data)


def test_retirement_age_equal_to_current_age_rejected() -> None:
    data = make_valid_inputs(dob="1975-01-01", retirement_age=50)
    with pytest.raises(ValidationError):
        FireInputs(**data)


def test_life_expectancy_must_exceed_retirement_age() -> None:
    data = make_valid_inputs(retirement_age=80, life_expectancy=80)
    with pytest.raises(ValidationError):
        FireInputs(**data)
