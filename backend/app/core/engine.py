"""Pure Python financial calculation engine for FIRE Retirement Tracker.

All math is extracted from the canonical test oracle in tests/conftest.py.
Functions must produce IDENTICAL results to the oracle.
"""

import math
from datetime import date

from app.core.constants import BUCKET_PERCENTAGES, FUNDS, SWR_SCENARIOS, SWR_VERDICTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_indian(amount: float) -> str:
    """Format a number in Indian comma notation (e.g. 1,30,20,768).

    Handles negative numbers and rounds to the nearest integer.
    """
    is_negative = amount < 0
    n = int(round(abs(amount)))
    s = str(n)

    if len(s) <= 3:
        result = s
    else:
        # Last 3 digits get their own group, then groups of 2 from the right
        last3 = s[-3:]
        remaining = s[:-3]
        # Insert commas every 2 digits from the right in the remaining part
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        result = ",".join(groups) + "," + last3

    return ("-" + result) if is_negative else result


# ---------------------------------------------------------------------------
# Derived inputs
# ---------------------------------------------------------------------------

def compute_derived_inputs(raw: dict) -> dict:
    """Add derived fields to a raw inputs dict.

    Adds: debt_pct, total_sip, current_age, years_to_retirement,
          retirement_duration, blended_return, real_return.

    The input dict is NOT mutated; a new dict is returned.
    """
    d = dict(raw)  # shallow copy

    d["debt_pct"] = 1.0 - d["equity_pct"] - d["gold_pct"] - d["cash_pct"]
    d["total_sip"] = d["your_sip"] + d["wife_sip"]

    # current_age: floor of fractional years since DOB
    if isinstance(d["dob"], str):
        dob = date.fromisoformat(d["dob"])
    else:
        dob = d["dob"]
    today = date.today()
    d["current_age"] = math.floor((today - dob).days / 365.25)

    d["years_to_retirement"] = d["retirement_age"] - d["current_age"]
    d["retirement_duration"] = d["life_expectancy"] - d["retirement_age"]

    d["blended_return"] = blended_return(d)
    d["real_return"] = real_return(d["blended_return"], d["inflation"])

    return d


# ---------------------------------------------------------------------------
# Return calculations
# ---------------------------------------------------------------------------

def blended_return(inputs: dict) -> float:
    """Weighted average nominal return across all asset classes.

    blended = equity_pct * equity_return + debt_pct * debt_return
            + gold_pct * gold_return + cash_pct * cash_return

    Mirrors conftest.py blended_return exactly.
    """
    # Compute debt_pct if not already present
    debt_pct = inputs.get(
        "debt_pct",
        1.0 - inputs["equity_pct"] - inputs["gold_pct"] - inputs["cash_pct"],
    )
    return (
        inputs["equity_pct"] * inputs["equity_return"]
        + debt_pct * inputs["debt_return"]
        + inputs["gold_pct"] * inputs["gold_return"]
        + inputs["cash_pct"] * inputs["cash_return"]
    )


def real_return(nominal: float, inflation: float) -> float:
    """Fisher equation: (1 + nominal) / (1 + inflation) - 1.

    NOT simple subtraction (nominal - inflation).
    """
    return (1.0 + nominal) / (1.0 + inflation) - 1.0


# ---------------------------------------------------------------------------
# Growth projection
# ---------------------------------------------------------------------------

def compute_growth_projection(inputs: dict) -> list[dict]:
    """Year-by-year growth projection (41 rows, year 0 through 40).

    Mirrors conftest.py compute_growth_projection EXACTLY:
    - Year 0: starting state, no investment, portfolio = existing_corpus.
    - Year 1: base SIP (NO step-up).
    - Years 2..years_to_retirement: SIP = previous year * (1 + step_up).
    - Post-retirement (year > years_to_retirement): SIP = 0.
    - Mid-year convention: portfolio = prev*(1+r) + annual*(1+r/2).
    """
    # Resolve debt_pct for blended return calculation
    debt_pct = inputs.get(
        "debt_pct",
        1.0 - inputs["equity_pct"] - inputs["gold_pct"] - inputs["cash_pct"],
    )
    inputs_with_debt = dict(inputs, debt_pct=debt_pct)
    br = blended_return(inputs_with_debt)

    # Handle both "step_up" and "step_up_pct" key names
    step_up = inputs.get("step_up", inputs.get("step_up_pct", 0))
    total_sip = inputs.get("total_sip", inputs["your_sip"] + inputs["wife_sip"])
    years_to_retirement = inputs.get(
        "years_to_retirement",
        inputs["retirement_age"] - inputs["current_age"],
    )
    equity_pct = inputs["equity_pct"]

    rows: list[dict] = []
    sip = total_sip
    portfolio = inputs["existing_corpus"]
    cumulative = inputs["existing_corpus"]

    for year in range(0, 41):
        age = inputs["current_age"] + year

        if year == 0:
            monthly_sip = total_sip
            annual_inv = 0
        elif year == 1:
            monthly_sip = total_sip  # Base SIP, NO step-up
            annual_inv = monthly_sip * 12
        elif year <= years_to_retirement:
            monthly_sip = sip * (1 + step_up)
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
            "equity_value": portfolio * equity_pct,
            "debt_gold_cash": portfolio * (1 - equity_pct),
        })

    return rows


# ---------------------------------------------------------------------------
# Retirement metrics
# ---------------------------------------------------------------------------

def compute_retirement_metrics(inputs: dict, corpus: float) -> dict:
    """Compute all retirement analysis metrics from the projected corpus.

    Returns dict with keys:
        corpus, annual_expense, monthly_expense, monthly_swp,
        surplus, funded_ratio, required_corpus,
        buckets (list of dicts), swr_scenarios (list of dicts).
    """
    years_to_retirement = inputs.get(
        "years_to_retirement",
        inputs["retirement_age"] - inputs["current_age"],
    )

    # Inflate current monthly expense to retirement
    monthly_expense = inputs["monthly_expense"] * (
        (1 + inputs["inflation"]) ** years_to_retirement
    )
    annual_expense = monthly_expense * 12

    # Safe withdrawal amounts
    monthly_swp = corpus * inputs["swr"] / 12
    surplus = monthly_swp - monthly_expense
    required_corpus = annual_expense / inputs["swr"]
    funded_ratio = corpus / required_corpus if required_corpus > 0 else 0.0

    # 3-Bucket strategy
    buckets = []
    for name, pct in BUCKET_PERCENTAGES.items():
        amount = corpus * pct
        coverage_years = amount / annual_expense if annual_expense > 0 else 0.0
        buckets.append({
            "name": name,
            "pct": pct,
            "amount": amount,
            "coverage_years": coverage_years,
        })

    # SWR comparison scenarios
    swr_scenarios = []
    for rate in SWR_SCENARIOS:
        annual = corpus * rate
        monthly = annual / 12
        vs_expense = monthly - monthly_expense
        swr_scenarios.append({
            "rate": rate,
            "annual": annual,
            "monthly": monthly,
            "vs_expense": vs_expense,
            "verdict": SWR_VERDICTS.get(rate, ""),
        })

    return {
        "corpus": corpus,
        "annual_expense": annual_expense,
        "monthly_expense": monthly_expense,
        "monthly_swp": monthly_swp,
        "surplus": surplus,
        "funded_ratio": funded_ratio,
        "required_corpus": required_corpus,
        "buckets": buckets,
        "swr_scenarios": swr_scenarios,
    }


# ---------------------------------------------------------------------------
# Fund allocation
# ---------------------------------------------------------------------------

def compute_fund_allocation(inputs: dict) -> list[dict]:
    """Compute the 10-fund allocation breakdown.

    Each fund has: name, category, pct (of total portfolio), monthly_sip.
    Mirrors the test oracle in test_02_fund_allocation.py EXACTLY.
    """
    debt_pct = inputs.get(
        "debt_pct",
        1.0 - inputs["equity_pct"] - inputs["gold_pct"] - inputs["cash_pct"],
    )
    total_sip = inputs.get("total_sip", inputs["your_sip"] + inputs["wife_sip"])

    # Build a lookup including the derived debt_pct
    pct_lookup = {
        "equity_pct": inputs["equity_pct"],
        "debt_pct": debt_pct,
        "gold_pct": inputs["gold_pct"],
        "cash_pct": inputs["cash_pct"],
    }

    result: list[dict] = []
    for fund_tuple in FUNDS:
        # Support both 4-tuple (old) and 5-tuple (with account) formats
        if len(fund_tuple) == 5:
            name, category, parent_key, sub_pct, account = fund_tuple
        else:
            name, category, parent_key, sub_pct = fund_tuple
            account = ""

        if category in ("gold", "cash"):
            pct = pct_lookup[parent_key]
        else:
            pct = pct_lookup[parent_key] * sub_pct / 100

        result.append({
            "name": name,
            "category": category,
            "pct": pct,
            "monthly_sip": pct * total_sip,
            "account": account,
        })

    return result


# ---------------------------------------------------------------------------
# Monthly SIP schedule
# ---------------------------------------------------------------------------

def compute_monthly_sips(inputs: dict) -> list[float]:
    """Compute planned monthly SIPs for 192 months (16 years).

    Mirrors conftest.py compute_monthly_sips EXACTLY:
    - Months 1-12: base total_sip (no step-up).
    - Step-up applied at months 13, 25, 37, ... (every 12 months).
    - current = current * (1 + step_up) at each boundary.
    """
    total_sip = inputs.get("total_sip", inputs["your_sip"] + inputs["wife_sip"])
    step_up = inputs.get("step_up", inputs.get("step_up_pct", 0))

    sips: list[float] = []
    current = total_sip

    for month in range(1, 193):
        if month > 1 and (month - 1) % 12 == 0:
            current = current * (1 + step_up)
        sips.append(current)

    return sips
