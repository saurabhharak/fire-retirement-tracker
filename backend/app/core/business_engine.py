"""Pure Python business engine for the Amul parlour module.

All P&L math is extracted here as pure functions (dict in, dict out) so it can
be unit-tested without a database. Mirrors the design contract of core/engine.py.

Period buckets:
    day     -> 'YYYY-MM-DD'
    month   -> 'YYYY-MM'
    quarter -> 'YYYY-Qn'
    year    -> 'YYYY'
"""

import re
from datetime import datetime
from typing import Optional

PERIODS = ("day", "month", "quarter", "year")


def quarter_of_month(month: int) -> int:
    """Map a 1-12 month to its quarter (1..4)."""
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month: {month}")
    return (month - 1) // 3 + 1


def period_key(date_str: str, period: str) -> str:
    """Bucket an ISO date string into a period key.

    period: 'day' -> 'YYYY-MM-DD', 'month' -> 'YYYY-MM',
            'quarter' -> 'YYYY-Qn', 'year' -> 'YYYY'
    """
    try:
        dt = datetime.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        raise ValueError(f"Invalid date string: {date_str!r}")

    if period == "day":
        return date_str[:10]
    if period == "month":
        return f"{dt.year:04d}-{dt.month:02d}"
    if period == "quarter":
        return f"{dt.year:04d}-Q{quarter_of_month(dt.month)}"
    if period == "year":
        return f"{dt.year:04d}"
    raise ValueError(f"Invalid period: {period!r}")


def _as_float(value) -> float:
    """Coerce a DB row value to float, treating None as 0.0."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _year_from_period_value(period_value: Optional[str]) -> Optional[str]:
    """Extract the 4-digit year from a period value like '2026-Q3' or '2026-07'."""
    if not period_value:
        return None
    m = re.match(r"^(\d{4})", period_value)
    return m.group(1) if m else None


def _matches_period(date_str: str, period: str, period_value: Optional[str]) -> bool:
    """Return True if an ISO date falls within the selected period bucket."""
    if not period_value:
        return True
    try:
        return period_key(date_str, period) == period_value
    except ValueError:
        return False


def _row_date(row: dict, key: str) -> str:
    return row.get(key) or ""


# ===================================================================
# P&L summary for a single selected period
# ===================================================================

def compute_pnl(
    sales: list[dict],
    invoices: list[dict],
    period: str,
    period_value: Optional[str] = None,
    expenses: Optional[list[dict]] = None,
    *,
    year: Optional[int] = None,  # legacy optional fallback filter
) -> dict:
    """Compute sales, purchases, other expenses, and profit for a period.

    sales rows: {sale_date, cash_amount, online_amount}
    invoices rows: {bill_date, total_amount}
    expenses rows: {expense_date, amount}  (other operating expenses)
    period: 'day' | 'month' | 'quarter' | 'year'
    period_value: the specific bucket, e.g. month='2026-07', quarter='2026-Q3',
                  year='2026', day='2026-07-15'. If None, sums all rows.

    Profit = sales - purchases - other_expenses.
    """
    if period not in PERIODS:
        raise ValueError(f"Invalid period: {period!r}")

    total_sales = 0.0
    sales_cash = 0.0
    sales_online = 0.0
    invoice_count = 0
    total_purchases = 0.0
    total_expenses = 0.0

    year_str = str(year) if year is not None else _year_from_period_value(period_value)

    for sale in sales:
        sale_date = _row_date(sale, "sale_date")
        if not sale_date:
            continue
        if year_str and not sale_date.startswith(year_str):
            continue
        if not _matches_period(sale_date, period, period_value):
            continue
        cash = _as_float(sale.get("cash_amount"))
        online = _as_float(sale.get("online_amount"))
        total_sales += cash + online
        sales_cash += cash
        sales_online += online

    for invoice in invoices:
        bill_date = _row_date(invoice, "bill_date")
        if not bill_date:
            continue
        if year_str and not bill_date.startswith(year_str):
            continue
        if not _matches_period(bill_date, period, period_value):
            continue
        total_purchases += _as_float(invoice.get("total_amount"))
        invoice_count += 1

    for expense in expenses or []:
        expense_date = _row_date(expense, "expense_date")
        if not expense_date:
            continue
        if year_str and not expense_date.startswith(year_str):
            continue
        if not _matches_period(expense_date, period, period_value):
            continue
        total_expenses += _as_float(expense.get("amount"))

    # period_key = the selected bucket if given, else derive from first row
    key = period_value or ""
    if not key:
        sample = next(
            (s.get("sale_date") for s in sales if s.get("sale_date")),
            next(
                (i.get("bill_date") for i in invoices if i.get("bill_date")),
                next((e.get("expense_date") for e in expenses or [] if e.get("expense_date")), ""),
            ),
        )
        if sample:
            key = period_key(sample, period)

    return {
        "total_sales": round(total_sales, 2),
        "total_purchases": round(total_purchases, 2),
        "total_expenses": round(total_expenses, 2),
        "profit": round(total_sales - total_purchases - total_expenses, 2),
        "sales_cash": round(sales_cash, 2),
        "sales_online": round(sales_online, 2),
        "invoice_count": invoice_count,
        "period": period,
        "period_key": key,
    }


# ===================================================================
# Time-series trends bucketed by period granularity
# ===================================================================

def compute_trends(
    sales: list[dict],
    invoices: list[dict],
    period: str = "month",
    period_value: Optional[str] = None,
    expenses: Optional[list[dict]] = None,
) -> dict:
    """Aggregate a time series bucketed by `period`.

    period: 'day' | 'month' | 'quarter' | 'year'
    period_value: restricts the range (e.g. month='2026-07' yields that day
    series; year='2026' yields that year's months). When a year is derivable
    from period_value, rows outside that year are excluded.

    Returns Recharts-ready aligned arrays:
    {labels: [...], sales: [...], purchases: [...], expenses: [...], profit: [...]}
    """
    if period not in PERIODS:
        raise ValueError(f"Invalid period: {period!r}")

    def _bucket(date_str: str) -> str:
        try:
            return period_key(date_str, period)
        except ValueError:
            return ""

    # Restriction prefix derived from the selected period_value:
    #   day    -> YYYY-MM (show that month's days)
    #   month  -> YYYY   (show that year's months)
    #   quarter-> YYYY   (show that year's quarters)
    #   year   -> YYYY
    if period == "day":
        prefix = period_value[:7] if period_value and len(period_value) >= 7 else period_value
    else:
        prefix = _year_from_period_value(period_value)

    series: dict[str, dict] = {}

    for sale in sales:
        sale_date = _row_date(sale, "sale_date")
        if not sale_date:
            continue
        if prefix and not sale_date.startswith(prefix):
            continue
        key = _bucket(sale_date)
        if not key:
            continue
        m = series.setdefault(key, {"sales": 0.0, "purchases": 0.0, "expenses": 0.0})
        m["sales"] += _as_float(sale.get("cash_amount")) + _as_float(sale.get("online_amount"))

    for invoice in invoices:
        bill_date = _row_date(invoice, "bill_date")
        if not bill_date:
            continue
        if prefix and not bill_date.startswith(prefix):
            continue
        key = _bucket(bill_date)
        if not key:
            continue
        m = series.setdefault(key, {"sales": 0.0, "purchases": 0.0, "expenses": 0.0})
        m["purchases"] += _as_float(invoice.get("total_amount"))

    for expense in expenses or []:
        expense_date = _row_date(expense, "expense_date")
        if not expense_date:
            continue
        if prefix and not expense_date.startswith(prefix):
            continue
        key = _bucket(expense_date)
        if not key:
            continue
        m = series.setdefault(key, {"sales": 0.0, "purchases": 0.0, "expenses": 0.0})
        m["expenses"] += _as_float(expense.get("amount"))

    labels = sorted(series.keys())
    return {
        "labels": labels,
        "sales": [round(series[k]["sales"], 2) for k in labels],
        "purchases": [round(series[k]["purchases"], 2) for k in labels],
        "expenses": [round(series[k]["expenses"], 2) for k in labels],
        "profit": [
            round(series[k]["sales"] - series[k]["purchases"] - series[k]["expenses"], 2)
            for k in labels
        ],
    }


# Backward-compatible alias for any caller using compute_monthly_trends
def compute_monthly_trends(
    sales: list[dict],
    invoices: list[dict],
    year: Optional[int] = None,
    expenses: Optional[list[dict]] = None,
) -> dict:
    """Alias for compute_trends(period='month') kept for compatibility."""
    return compute_trends(
        sales, invoices, "month",
        period_value=(f"{year:04d}" if year is not None else None),
        expenses=expenses,
    )


def compute_sarvam_balance(starting_credits: float, usage_rows: list[dict]) -> dict:
    """Compute Sarvam credit spend summary from usage rows.

    usage rows: {credits_used, cost_estimate_inr}
    """
    used = 0.0
    cost_inr = 0.0
    for row in usage_rows:
        used += _as_float(row.get("credits_used"))
        cost_inr += _as_float(row.get("cost_estimate_inr"))
    return {
        "starting": round(starting_credits, 2),
        "used": round(used, 2),
        "remaining": round(starting_credits - used, 2),
        "call_count": len(usage_rows),
        "cost_inr": round(cost_inr, 2),
    }


def compute_invoice_total(items: list[dict]) -> float:
    """Sum item net_amounts; missing/None treated as zero."""
    return round(sum(_as_float(i.get("net_amount")) for i in items), 2)