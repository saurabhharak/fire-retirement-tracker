"""Test auto-calculation of monthly expense from tracked expenses."""
from app.services.expenses_svc import compute_monthly_expense_total


def test_monthly_only():
    expenses = [
        {"amount": 10000, "frequency": "monthly"},
        {"amount": 5000, "frequency": "monthly"},
    ]
    assert compute_monthly_expense_total(expenses) == 15000.0


def test_quarterly_divided_by_3():
    expenses = [{"amount": 9000, "frequency": "quarterly"}]
    assert compute_monthly_expense_total(expenses) == 3000.0


def test_yearly_divided_by_12():
    expenses = [{"amount": 120000, "frequency": "yearly"}]
    assert compute_monthly_expense_total(expenses) == 10000.0


def test_one_time_excluded():
    expenses = [
        {"amount": 10000, "frequency": "monthly"},
        {"amount": 50000, "frequency": "one-time"},
    ]
    assert compute_monthly_expense_total(expenses) == 10000.0


def test_mixed_frequencies():
    expenses = [
        {"amount": 10000, "frequency": "monthly"},
        {"amount": 9000, "frequency": "quarterly"},
        {"amount": 60000, "frequency": "yearly"},
    ]
    # 10000 + 3000 + 5000 = 18000
    assert compute_monthly_expense_total(expenses) == 18000.0


def test_empty_expenses():
    assert compute_monthly_expense_total([]) == 0.0
