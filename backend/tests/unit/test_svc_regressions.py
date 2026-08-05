"""Regression tests for service-layer calculation bugs found in the audit.

Covers:
1. compute_monthly_expense_total must skip NULL / missing amounts (not crash).
2. kite_svc monthly SIP normalization: weekly -> amt * 52 / 12 (~= 4.333x),
   not amt * 4.
3. project_expenses_svc compute_project_summary must round category_totals and
   monthly_totals (not just total_paid) to avoid float artifacts.
4. sip_log_svc total: sum of actual_invested (may add robustness for NULLs).
"""
import pytest

from app.services import expenses_svc
from app.services import project_expenses_svc
from app.services import sip_log_svc
from app.services import kite_svc


# ---------------------------------------------------------------------------
# 1. compute_monthly_expense_total — NULL amount / frequency robustness
# ---------------------------------------------------------------------------

def test_compute_monthly_expense_total_skips_null_amount() -> None:
    expenses = [
        {"amount": 10000, "frequency": "monthly"},
        {"amount": None, "frequency": "monthly"},  # NULL from DB
        {"amount": 3000, "frequency": "monthly"},
    ]
    assert expenses_svc.compute_monthly_expense_total(expenses) == 13000.0


def test_compute_monthly_expense_total_skips_missing_amount() -> None:
    expenses = [
        {"frequency": "monthly"},  # no amount key at all
        {"amount": 2000, "frequency": "monthly"},
    ]
    assert expenses_svc.compute_monthly_expense_total(expenses) == 2000.0


def test_compute_monthly_expense_total_all_null() -> None:
    assert expenses_svc.compute_monthly_expense_total([{"amount": None, "frequency": "monthly"}]) == 0.0


# ---------------------------------------------------------------------------
# 2. kite_svc — weekly SIP normalization
# ---------------------------------------------------------------------------

def _sip(freq: str, amt: float = 1000) -> dict:
    return {
        "sip_id": "1",
        "tradingsymbol": "TEST",
        "status": "ACTIVE",
        "frequency": freq,
        "instalment_amount": amt,
        "completed_instalments": 0,
        "instalment_day": 1,
    }


def test_weekly_sip_uses_52_weeks_per_year() -> None:
    monthly = kite_svc._normalize_sip_to_monthly(_sip("weekly", 1000))
    # 1000 * 52/12 = 4333.33 (NOT 1000*4 = 4000)
    assert monthly == pytest.approx(1000 * 52 / 12)


def test_quarterly_sip_divided_by_3() -> None:
    monthly = kite_svc._normalize_sip_to_monthly(_sip("quarterly", 3000))
    assert monthly == pytest.approx(1000)


def test_monthly_sip_unchanged() -> None:
    monthly = kite_svc._normalize_sip_to_monthly(_sip("monthly", 5000))
    assert monthly == pytest.approx(5000)


# ---------------------------------------------------------------------------
# 3. project_expenses_svc — rounding of category/monthly totals
# ---------------------------------------------------------------------------

class _FakeClient:
    """Minimal stand-in for the Supabase query chain."""

    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        class _Resp:
            data = self._rows
        return _Resp()


def _inject_fake_expenses(monkeypatch, rows):
    import app.services.project_expenses_svc as module
    monkeypatch.setattr(
        module,
        "load_project_expenses",
        lambda user_id, access_token, project_id=None: rows,
    )


def test_project_summary_rounds_category_and_monthly_totals(monkeypatch) -> None:
    # 0.1 + 0.2 in float != 0.3; if unrounded, category_totals leaks artifacts.
    rows = [
        {"id": "1", "paid_amount": 0.1, "category": "Materials", "date": "2026-01-05", "is_active": True},
        {"id": "2", "paid_amount": 0.2, "category": "Materials", "date": "2026-01-10", "is_active": True},
    ]
    _inject_fake_expenses(monkeypatch, rows)
    summary = project_expenses_svc.compute_project_summary("u", "tok", "p1")

    assert summary["total_paid"] == 0.3
    assert summary["category_totals"]["Materials"] == 0.3
    assert summary["monthly_totals"]["2026-01"] == 0.3


# ---------------------------------------------------------------------------
# 4. sip_log_svc — total invested
# ---------------------------------------------------------------------------

def test_get_total_sip_invested_sum(monkeypatch) -> None:
    class _FakeSipClient(_FakeClient):
        def __init__(self):
            super().__init__([{"actual_invested": 10000.5}, {"actual_invested": 20000.25}])

    monkeypatch.setattr(
        sip_log_svc,
        "get_user_client",
        lambda token: _FakeSipClient(),
    )
    total = sip_log_svc.get_total_sip_invested("u", "tok")
    assert total == pytest.approx(30000.75)


def test_get_total_sip_invested_empty(monkeypatch) -> None:
    class _EmptyClient(_FakeClient):
        def __init__(self):
            super().__init__([])

    monkeypatch.setattr(sip_log_svc, "get_user_client", lambda token: _EmptyClient())
    assert sip_log_svc.get_total_sip_invested("u", "tok") == 0.0
