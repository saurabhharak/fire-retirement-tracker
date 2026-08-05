"""Regression tests for how the retirement corpus row is picked from the growth projection.

Covers two real bugs found in the audit:

1. Negative years_to_retirement (current_age >= retirement_age). The router
   indexed projection[years] with years negative, which Python resolves as a
   NEGATIVE index from the END of the list, silently returning a late row as
   the "retirement corpus".

2. years_to_retirement > 40 (the projection is hard-capped at 41 rows,
   years 0..40). The router silently clamped to the year-40 portfolio,
   understating the corpus by the missing years of contributions/growth.
"""
import pytest

from app.core.engine import (
    compute_derived_inputs,
    compute_growth_projection,
)
from app.routers.projections import _pick_corpus_row


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


def _row_portfolios(projection: list[dict]) -> list[float]:
    return [row["portfolio"] for row in projection]


def _assert_monotonic_non_decreasing(values: list[float]) -> None:
    for prev, cur in zip(values, values[1:]):
        assert cur >= prev, f"corpus fell from {prev} to {cur}"


# ---------------------------------------------------------------------------
# Negative years_to_retirement (current_age >= retirement_age)
# ---------------------------------------------------------------------------

def test_years_to_retirement_is_never_negative() -> None:
    # Born 1950 -> ~76 years old today, retirement_age 50 => years_to_retirement
    # should be clamped to 0, NOT -26.
    inputs = make_inputs("1950-01-01", retirement_age=50)
    assert inputs["current_age"] > 50
    assert inputs["years_to_retirement"] == 0


def test_pick_corpus_with_negative_years_does_not_negative_index() -> None:
    inputs = make_inputs("1950-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    corpus = _pick_corpus_row(projection, inputs["years_to_retirement"])

    # Must be the year-0 row (existing corpus), NOT the year-36 row that a
    # negative index (projection[-26]) would return.
    assert corpus == projection[0]["portfolio"]
    assert corpus == inputs["existing_corpus"]


def test_retirement_metrics_use_year0_corpus_when_already_retired() -> None:
    from app.core.engine import compute_retirement_metrics

    inputs = make_inputs("1950-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    corpus = _pick_corpus_row(projection, inputs["years_to_retirement"])
    metrics = compute_retirement_metrics(inputs, corpus)

    assert metrics["corpus"] == inputs["existing_corpus"]


# ---------------------------------------------------------------------------
# years_to_retirement > 40 (projection hard cap)
# ---------------------------------------------------------------------------

def test_long_horizon_corpus_exceeds_year40_row() -> None:
    # Age ~26 today (born 2000), retire at 90 (max) => 64 years to retirement,
    # far beyond the 41-row projection. The corpus used by retirement metrics
    # must exceed the year-40 value (still accumulating SIPs after year 40).
    inputs = make_inputs("2000-01-01", retirement_age=90)
    projection = compute_growth_projection(inputs)
    corpus = _pick_corpus_row(projection, inputs["years_to_retirement"], inputs["blended_return"])

    assert inputs["years_to_retirement"] > 40
    assert corpus > projection[-1]["portfolio"]


def test_long_horizon_corpus_not_clamped_to_last_row() -> None:
    inputs = make_inputs("2000-01-01", retirement_age=90)
    projection = compute_growth_projection(inputs)
    corpus = _pick_corpus_row(projection, inputs["years_to_retirement"], inputs["blended_return"])

    # Clamping bug would return projection[-1]; the fixed version must not.
    assert corpus != projection[-1]["portfolio"]


def test_short_horizon_corpus_matches_projection_row() -> None:
    # Normal case unchanged: 40-year-old, retire at 50 => row year 10.
    inputs = make_inputs("1986-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    corpus = _pick_corpus_row(projection, inputs["years_to_retirement"])

    assert inputs["years_to_retirement"] == projection[inputs["years_to_retirement"]]["year"]
    assert corpus == projection[inputs["years_to_retirement"]]["portfolio"]


# ---------------------------------------------------------------------------
# Post-retirement rows should NOT keep compounding with new contributions
# ---------------------------------------------------------------------------

def test_contribution_years_never_exceed_years_to_retirement() -> None:
    inputs = make_inputs("1986-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    ytr = inputs["years_to_retirement"]

    # Before retirement: contributions happen. After retirement: none.
    for row in projection[: ytr + 1]:
        assert row["annual_inv"] >= 0
    for row in projection[ytr + 1 :]:
        assert row["annual_inv"] == 0


def test_gains_stop_accumulating_after_retirement() -> None:
    """After retirement there are no contributions, so cumulative stays flat
    and gains only grow by compounding — they must NOT get new-money bumps.
    """
    inputs = make_inputs("1986-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    ytr = inputs["years_to_retirement"]

    post = projection[ytr + 1 :]
    if not post:
        pytest.skip("no post-retirement rows in projection")

    # Cumulative (invested principal) must be frozen after retirement.
    cumulative_at_retirement = projection[ytr]["cumulative"]
    for row in post:
        assert row["annual_inv"] == 0
        assert row["cumulative"] == pytest.approx(cumulative_at_retirement)

    # Gains = portfolio - cumulative must be monotonic (compounding only).
    gains = [row["gains"] for row in [projection[ytr], *post]]
    for prev, cur in zip(gains, gains[1:]):
        assert cur >= prev


def test_corpus_growth_post_retirement_is_compounding_only() -> None:
    """portfolio[y+1] == portfolio[y] * (1+br) once contributions stop."""
    inputs = make_inputs("1986-01-01", retirement_age=50)
    projection = compute_growth_projection(inputs)
    ytr = inputs["years_to_retirement"]
    br = inputs["blended_return"]

    post = projection[ytr + 1 :]
    for prev_row, next_row in zip(post, post[1:]):
        expected = prev_row["portfolio"] * (1 + br)
        assert abs(next_row["portfolio"] - expected) < 1.0
