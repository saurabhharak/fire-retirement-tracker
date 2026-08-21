"""Unit tests for the parlour business engine (pure P&L math).

Covers period bucketing, month/quarter/year P&L aggregation, monthly
trends for charts, Sarvam credit balance, and invoice-total cross-checks.
All functions are pure (dict in, dict out) — no DB.
"""

import pytest

from app.core.business_engine import (
    quarter_of_month,
    period_key,
    compute_pnl,
    compute_trends,
    compute_monthly_trends,
    compute_sarvam_balance,
    compute_invoice_total,
)


# ===================================================================
# quarter_of_month
# ===================================================================
class TestQuarterOfMonth:
    @pytest.mark.parametrize(
        "month,quarter",
        [
            (1, 1), (2, 1), (3, 1),
            (4, 2), (5, 2), (6, 2),
            (7, 3), (8, 3), (9, 3),
            (10, 4), (11, 4), (12, 4),
        ],
    )
    def test_quarter_mapping(self, month, quarter):
        assert quarter_of_month(month) == quarter

    def test_out_of_range_month_raises(self):
        with pytest.raises(ValueError):
            quarter_of_month(13)


# ===================================================================
# period_key
# ===================================================================
class TestPeriodKey:
    def test_day_key(self):
        assert period_key("2026-07-15", "day") == "2026-07-15"

    def test_month_key(self):
        assert period_key("2026-07-15", "month") == "2026-07"

    def test_quarter_key(self):
        assert period_key("2026-08-01", "quarter") == "2026-Q3"

    def test_year_key(self):
        assert period_key("2026-12-31", "year") == "2026"

    @pytest.mark.parametrize("bad", ["week", "", None])
    def test_invalid_period_rejected(self, bad):
        with pytest.raises(ValueError):
            period_key("2026-07-15", bad)


# ===================================================================
# compute_pnl
# ===================================================================
class TestComputePnl:
    def test_monthly_pnl_single_month(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 60000, "online_amount": 40000}]
        invoices = [{"bill_date": "2026-07-05", "total_amount": 60000}]
        result = compute_pnl(sales, invoices, "month", year=2026)
        assert result["total_sales"] == 100000
        assert result["total_purchases"] == 60000
        assert result["profit"] == 40000

    def test_quarterly_pnl_aggregates_three_months(self):
        sales = [
            {"sale_date": "2026-04-01", "cash_amount": 10000, "online_amount": 0},
            {"sale_date": "2026-05-01", "cash_amount": 20000, "online_amount": 0},
            {"sale_date": "2026-06-01", "cash_amount": 30000, "online_amount": 0},
        ]
        invoices = [
            {"bill_date": "2026-04-02", "total_amount": 5000},
            {"bill_date": "2026-05-02", "total_amount": 6000},
            {"bill_date": "2026-06-02", "total_amount": 7000},
        ]
        result = compute_pnl(sales, invoices, "quarter", year=2026)
        assert result["total_sales"] == 60000
        assert result["total_purchases"] == 18000
        assert result["profit"] == 42000
        assert result["period_key"] == "2026-Q2"

    def test_yearly_pnl_aggregates_twelve_months(self):
        sales = [
            {"sale_date": f"2026-{m:02d}-01", "cash_amount": 10000, "online_amount": 0}
            for m in range(1, 13)
        ]
        invoices = [
            {"bill_date": f"2026-{m:02d}-02", "total_amount": 4000}
            for m in range(1, 13)
        ]
        result = compute_pnl(sales, invoices, "year", year=2026)
        assert result["total_sales"] == 120000
        assert result["total_purchases"] == 48000
        assert result["profit"] == 72000
        assert result["period_key"] == "2026"

    def test_empty_inputs_returns_zeros(self):
        result = compute_pnl([], [], "month", year=2026)
        assert result["total_sales"] == 0
        assert result["total_purchases"] == 0
        assert result["profit"] == 0
        assert result["invoice_count"] == 0

    def test_profit_negative_when_purchases_exceed_sales(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        invoices = [{"bill_date": "2026-07-02", "total_amount": 500}]
        result = compute_pnl(sales, invoices, "month", year=2026)
        assert result["profit"] == -400

    def test_sales_sums_cash_plus_online(self):
        sales = [
            {"sale_date": "2026-07-01", "cash_amount": 2750, "online_amount": 5769},
            {"sale_date": "2026-07-02", "cash_amount": 2860, "online_amount": 3079},
        ]
        result = compute_pnl(sales, [], "month", year=2026)
        assert result["total_sales"] == 2750 + 5769 + 2860 + 3079
        assert result["sales_cash"] == 2750 + 2860
        assert result["sales_online"] == 5769 + 3079

    def test_purchases_sums_invoice_total_amount(self):
        invoices = [
            {"bill_date": "2026-07-01", "total_amount": 1761.88},
            {"bill_date": "2026-07-05", "total_amount": 14062.75},
        ]
        result = compute_pnl([], invoices, "month", year=2026)
        assert result["total_purchases"] == pytest.approx(1761.88 + 14062.75)
        assert result["invoice_count"] == 2

    def test_filters_by_year_when_given(self):
        sales = [
            {"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0},
            {"sale_date": "2025-07-01", "cash_amount": 999, "online_amount": 0},
        ]
        result = compute_pnl(sales, [], "month", year=2026)
        assert result["total_sales"] == 100

    def test_handles_missing_amount_keys_robustly(self):
        sales = [
            {"sale_date": "2026-07-01", "cash_amount": 100},  # missing online
            {"sale_date": "2026-07-02", "cash_amount": None, "online_amount": 50},  # None
        ]
        result = compute_pnl(sales, [], "month", year=2026)
        assert result["total_sales"] == 150

    def test_profit_subtracts_other_expenses(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100000, "online_amount": 0}]
        invoices = [{"bill_date": "2026-07-02", "total_amount": 40000}]
        expenses = [
            {"expense_date": "2026-07-03", "amount": 20000},  # rent
            {"expense_date": "2026-07-05", "amount": 5000},   # electricity
        ]
        result = compute_pnl(sales, invoices, "month", year=2026, expenses=expenses)
        assert result["total_sales"] == 100000
        assert result["total_purchases"] == 40000
        assert result["total_expenses"] == 25000
        assert result["profit"] == 35000

    def test_expenses_filters_by_year(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        expenses = [
            {"expense_date": "2026-07-01", "amount": 10},
            {"expense_date": "2025-07-01", "amount": 999},  # wrong year
        ]
        result = compute_pnl(sales, [], "month", year=2026, expenses=expenses)
        assert result["total_expenses"] == 10

    def test_empty_expenses_defaults_zero(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        result = compute_pnl(sales, [], "month", year=2026)
        assert result["total_expenses"] == 0

    # --- period_value specific-bucket filtering (the core A1 fix) ---

    def test_month_filters_to_specific_month_not_all_year(self):
        sales = [
            {"sale_date": "2026-07-01", "cash_amount": 1000, "online_amount": 0},
            {"sale_date": "2026-08-01", "cash_amount": 9999, "online_amount": 0},
        ]
        invoices = [{"bill_date": "2026-07-15", "total_amount": 400}]
        result = compute_pnl(sales, invoices, "month", period_value="2026-07")
        # Must EXCLUDE August 9999 — this was the original bug (showed all months)
        assert result["total_sales"] == 1000
        assert result["total_purchases"] == 400
        assert result["profit"] == 600
        assert result["period_key"] == "2026-07"

    def test_quarter_filters_to_specific_quarter(self):
        sales = [
            {"sale_date": "2026-04-15", "cash_amount": 10, "online_amount": 0},
            {"sale_date": "2026-06-30", "cash_amount": 20, "online_amount": 0},
            # outside Q2
            {"sale_date": "2026-03-15", "cash_amount": 999, "online_amount": 0},
            {"sale_date": "2026-07-01", "cash_amount": 888, "online_amount": 0},
        ]
        result = compute_pnl(sales, [], "quarter", period_value="2026-Q2")
        assert result["total_sales"] == 30
        assert result["period_key"] == "2026-Q2"

    def test_year_filters_to_specific_year(self):
        sales = [
            {"sale_date": "2026-01-01", "cash_amount": 10, "online_amount": 0},
            {"sale_date": "2025-01-01", "cash_amount": 999, "online_amount": 0},
        ]
        result = compute_pnl(sales, [], "year", period_value="2026")
        assert result["total_sales"] == 10
        assert result["period_key"] == "2026"

    def test_day_filters_to_specific_date(self):
        sales = [
            {"sale_date": "2026-08-15", "cash_amount": 2750, "online_amount": 5769},
            {"sale_date": "2026-08-16", "cash_amount": 9999, "online_amount": 0},
        ]
        result = compute_pnl(sales, [], "day", period_value="2026-08-15")
        assert result["total_sales"] == 2750 + 5769
        assert result["period_key"] == "2026-08-15"

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            compute_pnl([], [], "week")


# ===================================================================
# compute_monthly_trends / compute_trends
# ===================================================================
class TestComputeTrends:
    def test_monthly_trends(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        invoices = [{"bill_date": "2026-07-02", "total_amount": 40}]
        trends = compute_trends(sales, invoices, "month")
        assert trends["labels"] == ["2026-07"]
        assert trends["sales"] == [100]
        assert trends["purchases"] == [40]
        assert trends["profit"] == [60]

    def test_quarterly_trends_buckets_by_quarter(self):
        sales = [
            {"sale_date": "2026-01-15", "cash_amount": 10, "online_amount": 0},
            {"sale_date": "2026-02-15", "cash_amount": 20, "online_amount": 0},
            {"sale_date": "2026-04-15", "cash_amount": 100, "online_amount": 0},
        ]
        trends = compute_trends(sales, [], "quarter")
        assert trends["labels"] == ["2026-Q1", "2026-Q2"]
        assert trends["sales"] == [30, 100]

    def test_year_trends_buckets_by_year(self):
        sales = [
            {"sale_date": "2025-05-01", "cash_amount": 10, "online_amount": 0},
            {"sale_date": "2026-05-01", "cash_amount": 20, "online_amount": 0},
        ]
        trends = compute_trends(sales, [], "year")
        assert trends["labels"] == ["2025", "2026"]
        assert trends["sales"] == [10, 20]

    def test_day_trends_within_month(self):
        sales = [
            {"sale_date": "2026-07-01", "cash_amount": 10, "online_amount": 0},
            {"sale_date": "2026-07-02", "cash_amount": 20, "online_amount": 0},
            {"sale_date": "2026-08-01", "cash_amount": 999, "online_amount": 0},
        ]
        trends = compute_trends(sales, [], "day", period_value="2026-07")
        assert trends["labels"] == ["2026-07-01", "2026-07-02"]
        assert trends["sales"] == [10, 20]

    def test_year_restriction_from_period_value(self):
        sales = [
            {"sale_date": "2025-12-01", "cash_amount": 999, "online_amount": 0},
            {"sale_date": "2026-01-01", "cash_amount": 10, "online_amount": 0},
        ]
        trends = compute_trends(sales, [], "month", period_value="2026-01")
        assert trends["labels"] == ["2026-01"]
        assert trends["sales"] == [10]
class TestComputeMonthlyTrends:
    def test_returns_aligned_sales_purchases_profit_arrays(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        invoices = [{"bill_date": "2026-07-02", "total_amount": 40}]
        trends = compute_monthly_trends(sales, invoices, year=2026)
        assert trends["labels"] == ["2026-07"]
        assert trends["sales"] == [100]
        assert trends["purchases"] == [40]
        assert trends["profit"] == [60]

    def test_labels_sorted_chronologically(self):
        sales = [
            {"sale_date": "2026-08-01", "cash_amount": 1, "online_amount": 0},
            {"sale_date": "2026-07-01", "cash_amount": 2, "online_amount": 0},
        ]
        trends = compute_monthly_trends(sales, [], year=2026)
        assert trends["labels"] == ["2026-07", "2026-08"]

    def test_month_with_only_sales_has_zero_purchases(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        trends = compute_monthly_trends(sales, [], year=2026)
        assert trends["purchases"] == [0]
        assert trends["profit"] == [100]

    def test_multiple_invoices_same_month_summed(self):
        invoices = [
            {"bill_date": "2026-07-01", "total_amount": 10},
            {"bill_date": "2026-07-20", "total_amount": 20},
        ]
        trends = compute_monthly_trends([], invoices, year=2026)
        assert trends["purchases"] == [30]

    def test_expenses_included_in_trends_and_profit(self):
        sales = [{"sale_date": "2026-07-01", "cash_amount": 100, "online_amount": 0}]
        invoices = [{"bill_date": "2026-07-02", "total_amount": 40}]
        expenses = [{"expense_date": "2026-07-03", "amount": 20}]
        trends = compute_monthly_trends(sales, invoices, year=2026, expenses=expenses)
        assert trends["expenses"] == [20]
        assert trends["profit"] == [40]  # 100 - 40 - 20


# ===================================================================
# compute_sarvam_balance
# ===================================================================
class TestComputeSarvamBalance:
    def test_remaining_equals_starting_minus_used(self):
        usage = [
            {"credits_used": 2, "cost_estimate_inr": 0.1},
            {"credits_used": 3, "cost_estimate_inr": 0.15},
        ]
        result = compute_sarvam_balance(10, usage)
        assert result["starting"] == 10
        assert result["used"] == 5
        assert result["remaining"] == 5

    def test_no_usage_returns_starting(self):
        result = compute_sarvam_balance(100, [])
        assert result["remaining"] == 100
        assert result["call_count"] == 0

    def test_over_spend_returns_negative_remaining(self):
        usage = [{"credits_used": 12, "cost_estimate_inr": 1.0}]
        result = compute_sarvam_balance(10, usage)
        assert result["remaining"] == -2

    def test_call_count_and_cost_inr_summed(self):
        usage = [
            {"credits_used": 1, "cost_estimate_inr": 0.05},
            {"credits_used": 1, "cost_estimate_inr": 0.05},
            {"credits_used": 1, "cost_estimate_inr": 0.05},
        ]
        result = compute_sarvam_balance(5, usage)
        assert result["call_count"] == 3
        assert result["cost_inr"] == pytest.approx(0.15)


# ===================================================================
# compute_invoice_total
# ===================================================================
class TestComputeInvoiceTotal:
    def test_sums_net_amounts(self):
        items = [
            {"net_amount": 312.38},
            {"net_amount": 320.0},
            {"net_amount": 594.0},
            {"net_amount": 535.5},
        ]
        assert compute_invoice_total(items) == pytest.approx(1761.88)

    def test_empty_items_returns_zero(self):
        assert compute_invoice_total([]) == 0

    def test_handles_missing_net_amount_as_zero(self):
        items = [
            {"net_amount": 100},
            {"description": "no amount"},
            {"net_amount": None},
        ]
        assert compute_invoice_total(items) == 100
