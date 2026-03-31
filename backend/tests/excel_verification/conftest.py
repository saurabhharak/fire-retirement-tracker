import pytest
import openpyxl
from pathlib import Path

WORKBOOK_PATH = Path(__file__).parent.parent / "fire-retirement-tracker.xlsx"

# Tolerance for floating point comparisons (0.01 = 1 paisa)
TOLERANCE = 0.01


@pytest.fixture(scope="session")
def wb():
    """Load workbook with formulas (not cached values).
    NOTE: openpyxl cannot recalculate formulas. We verify formula TEXT
    and use independent Python simulation to verify the MATH."""
    wb = openpyxl.load_workbook(str(WORKBOOK_PATH))
    yield wb
    wb.close()


@pytest.fixture(scope="session")
def inputs():
    """Raw input constants from the Inputs sheet - the single source of truth.
    Every test computes expected values from THESE numbers, never from other cells."""
    return {
        "dob": "1997-01-15",
        "current_age": 29,
        "retirement_age": 45,
        "life_expectancy": 90,
        "years_to_retirement": 16,  # 45 - 29
        "retirement_duration": 45,  # 90 - 45
        "your_sip": 225_000,
        "wife_sip": 100_000,
        "total_sip": 325_000,
        "step_up": 0.10,
        "existing_corpus": 2_500_000,
        "equity_return": 0.11,
        "debt_return": 0.07,
        "gold_return": 0.09,
        "cash_return": 0.05,
        "inflation": 0.065,
        "swr": 0.03,
        "equity_pct": 0.75,
        "debt_pct": 0.15,
        "gold_pct": 0.05,
        "cash_pct": 0.05,
        "monthly_expense": 125_000,
    }


def blended_return(inputs):
    """Compute blended pre-retirement return from raw inputs."""
    return (
        inputs["equity_pct"] * inputs["equity_return"]
        + inputs["debt_pct"] * inputs["debt_return"]
        + inputs["gold_pct"] * inputs["gold_return"]
        + inputs["cash_pct"] * inputs["cash_return"]
    )


def compute_growth_projection(inputs):
    """Independently compute the full year-by-year growth projection.
    This is the PYTHON ORACLE that mirrors what the Excel formulas should compute."""
    br = blended_return(inputs)
    rows = []
    sip = inputs["total_sip"]
    portfolio = inputs["existing_corpus"]
    cumulative = inputs["existing_corpus"]

    for year in range(0, 41):
        age = inputs["current_age"] + year

        if year == 0:
            monthly_sip = inputs["total_sip"]
            annual_inv = 0
        elif year == 1:
            monthly_sip = inputs["total_sip"]  # Base SIP, NO step-up
            annual_inv = monthly_sip * 12
        elif year <= inputs["years_to_retirement"]:
            monthly_sip = sip * (1 + inputs["step_up"])
            annual_inv = monthly_sip * 12
        else:
            monthly_sip = 0
            annual_inv = 0

        sip = monthly_sip

        if year > 0:
            portfolio = portfolio * (1 + br) + annual_inv * (1 + br / 2)

        cumulative += annual_inv
        gains = portfolio - cumulative

        rows.append({
            "year": year,
            "age": age,
            "monthly_sip": monthly_sip,
            "annual_inv": annual_inv,
            "cumulative": cumulative,
            "portfolio": portfolio,
            "gains": gains,
            "equity_value": portfolio * inputs["equity_pct"],
            "debt_gold_cash": portfolio * (1 - inputs["equity_pct"]),
        })

    return rows


def compute_monthly_sips(inputs):
    """Compute expected monthly SIPs for 192 months (SIP Tracker)."""
    sips = []
    current = inputs["total_sip"]
    for month in range(1, 193):
        if month > 1 and (month - 1) % 12 == 0:
            current = current * (1 + inputs["step_up"])
        sips.append(current)
    return sips
