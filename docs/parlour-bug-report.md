# Parlour Module Bug Report — Mentor Guide for DeepSeek Flash

> **STATUS: ALL BUGS FIXED & VERIFIED.**
> This document now records what was wrong, how it was fixed, and the
> verification evidence, so it can serve as a regression spec / reference.

## Context
The FIRE Retirement Tracker app has a new "Parlour" module for tracking an Amul
ice-cream parlour ("Vrindavan Treats"). It tracks daily sales (cash + online from
WhatsApp), purchase invoices (Sarvam OCR from PDF), and other operating expenses
(rent, electricity, etc.), with P&L analytics by day/month/quarter/year.

**Tech stack:** FastAPI backend (Python), React + Vite frontend (TypeScript),
Supabase (PostgreSQL + Auth), TanStack Query, Recharts.

## Files involved

| Layer | File | Role |
|-------|------|------|
| Engine | `backend/app/core/business_engine.py` | Pure P&L math (compute_pnl, compute_trends, period_key) |
| API | `backend/app/routers/amul.py` | `/api/amul/analytics` endpoint |
| Hook | `frontend/src/hooks/useAmulAnalytics.ts` | TanStack Query hook calling the API |
| Page | `frontend/src/pages/Parlour.tsx` | Main UI — tabs, PeriodPicker, summary cards, charts |
| Pickers | `frontend/src/components/parlour/PeriodPicker.tsx` | Day/Month/Quarter/Year selector |
| Sales | `frontend/src/components/parlour/SalesTable.tsx` | Pagination + inline edit |
| Invoices | `frontend/src/components/parlour/InvoiceList.tsx`, `InvoiceDetail.tsx` | Detail line-item view |
| Members | `frontend/src/components/parlour/MembersManager.tsx`, `hooks/useParlourMembers.ts` | Owner membership management |
| Daily sales | `backend/app/services/amul_sales_svc.py` + `migrations/017_daily_sales_unique.sql` | Idempotent upsert |

---

## BUG A1 (CRITICAL): `compute_pnl` doesn't filter by the selected period

**File:** `backend/app/core/business_engine.py`, `compute_pnl()` (lines 45-137)

**Problem:** The function accepts `period` ("month"/"quarter"/"year") and `year`,
but **only uses `year` for filtering** — it never filters by the specific month
or quarter. When `period="month"`, it sums ALL sales/purchases/expenses across
ALL months (or within the year if `year` is set). There is no code that says
"only include rows where the date falls in July 2026."

```python
# BUG: This is the ONLY filter — it checks the year, not the month/quarter
if year is not None and not sale_date.startswith(str(year)):
    continue
# There is NO filter like:
#   if period == "month" and not sale_date.startswith(month_str):
#       continue
```

**The frontend never sends `year` either** (Parlour.tsx line 61-64):
```tsx
const { data: analytics } = useAmulAnalytics(activeId, { period });
//                                                            ^^^^^^^
//  Only `period` is passed. No `year`, no `month`, no `quarter`.
```

**Result:** Selecting "Monthly" shows the grand total across ALL time (₹24,27,397),
not one month's P&L. Same for "Quarterly" — shows the all-time total, not one
quarter. The period dropdown changes the label but not the numbers.

**Fix:**
1. Add a `month` parameter to the API (`GET /api/amul/analytics?period=month&month=2026-07`)
2. Add a `quarter` parameter (`GET /api/amul/analytics?period=quarter&quarter=2026-Q3`)
3. In `compute_pnl`, filter rows by the selected period bucket:
   - `period="day"` → filter by exact date `sale_date == "2026-07-15"`
   - `period="month"` → filter by `sale_date.startswith("2026-07")`
   - `period="quarter"` → filter by dates in Q1/Q2/Q3/Q4 of the year
   - `period="year"` → filter by `sale_date.startswith("2026")`
4. Derive `period_key` from the user's selection, not from the first data row.

---

## BUG A2 (CRITICAL): No month/quarter/year picker in the UI

**File:** `frontend/src/pages/Parlour.tsx`, lines 199-218

**Problem:** The period dropdown only lets you pick the **granularity**
(Monthly/Quarterly/Annual). There is **no UI to pick WHICH month, quarter, or
year** to view. The user selects "Monthly" but cannot choose "July 2026" vs
"August 2026".

```tsx
<select value={period} onChange={(e) => setPeriod(e.target.value)}>
  <option value="month">Monthly</option>
  <option value="quarter">Quarterly</option>
  <option value="year">Annual</option>
</select>
// No month picker, no year picker, no quarter picker
```

**Fix:**
1. Add a second dropdown that changes based on the selected period:
   - When "Monthly" → show a month picker (Jul 2026, Aug 2026, ...)
   - When "Quarterly" → show a quarter picker (Q1 2026, Q2 2026, ...)
   - When "Annual" → show a year picker (2025, 2026, ...)
   - When "Day" → show a date picker
2. Pass the selected value to `useAmulAnalytics(activeId, { period, month })`
   or `{ period, quarter }` or `{ period, year }`.
3. Update the `useAmulAnalytics` hook to accept and send these parameters.

---

## BUG A3 (MEDIUM): No "Day" period

**File:** Both `business_engine.py` and `Parlour.tsx` dropdown

**Problem:** The user wants a daily view but there's no "day" option. The
dropdown only has Monthly/Quarterly/Annual.

**Fix:**
1. Add `<option value="day">Daily</option>` to the period dropdown.
2. In `compute_pnl`, handle `period="day"`: filter by exact date.
3. In `compute_monthly_trends` (or a new `compute_daily_trends`), when
   `period="day"`, aggregate by day for the selected month.

---

## BUG A4 (MEDIUM): Trends chart always shows month-level, regardless of period

**File:** `backend/app/core/business_engine.py`, `compute_monthly_trends()` (lines 140-200)

**Problem:** The `compute_monthly_trends` function always buckets by month
(`period_key(date_str, "month")`). Even when the user selects "Quarterly" or
"Annual", the trend chart shows month-by-month bars/lines. There's no quarterly
or annual aggregation for the trends.

The API route always calls `compute_monthly_trends`:
```python
trends = business_engine.compute_monthly_trends(sales, invoices, year=year, expenses=expenses)
```

**Fix:**
1. Make `compute_monthly_trends` period-aware, or create a new
   `compute_trends(sales, invoices, period, ...)` that buckets by the selected
   period (day/month/quarter/year).
2. Pass the `period` to the trends function from the API route.

---

## BUG A5 (LOW): "Annual view — 2026-08" label is wrong

**File:** `frontend/src/pages/Parlour.tsx`, line 216

**Problem:** When "Annual" is selected, the label shows
"Annual view — 2026-08" (a month, not a year). The `period_key` returned by
the backend for annual is derived from the first data row's date (e.g.
"2026-08-21" → "2026-08"), which is a month key, not a year key.

```tsx
<span className="text-xs text-[#E8ECF1]/50">
  {periodLabel(period)} view — {analytics?.summary.period_key ?? ""}
</span>
// Shows "Annual view — 2026-08" (wrong — should show "Annual view — 2026")
```

**Fix:** Fix `period_key` in `compute_pnl` to return "2026" for annual, or
derive it from the user's year selection.

---

## BUG P1 (MEDIUM): No Sarvam starting credits field in parlour creation form

**File:** `frontend/src/pages/Parlour.tsx`, lines 112-134

**Problem:** The "New Parlour" form only has a name field. There's no input for
`sarvam_starting_credits`. The backend model and hook both support it, but the
UI doesn't expose it.

```tsx
// Current form only has:
<input type="text" value={newName} placeholder="e.g. Vrindavan Treats" />
// Missing: <input type="number" placeholder="Sarvam starting credits" />
```

**Result:** All parlours are created with `sarvam_starting_credits: 0`. The Sarvam
widget always shows 0/0/0.

**Fix:** Add a number input for Sarvam starting credits in the New Parlour form,
and pass it to `saveParlour({ name, sarvam_starting_credits })`.

---

## BUG P2 (MEDIUM): WhatsApp import creates duplicate sales

**File:** `backend/app/routers/amul.py`, `import_whatsapp_sales` route (lines 273-301)
and `backend/app/services/amul_sales_svc.py`, `save_daily_sale()` (lines 46-62)

**Problem:** The import calls `save_daily_sale` for each parsed row, which does
a plain `.insert()`. If a sale already exists for that date (e.g., re-importing
the chat), it creates a **duplicate** row. There's no upsert or duplicate check.

```python
for row in rows:
    result = amul_sales_svc.save_daily_sale(
        parlour_id, user.id, row, user.access_token,
    )
    # Always INSERT — no ON CONFLICT check
```

**Important — verified:** The `amul_daily_sales` table has **NO unique
constraint on `(parlour_id, sale_date)`**. It only has:
- a plain (non-unique) index `idx_amul_sales_parlour_date` on `(parlour_id, sale_date)`
- a CHECK constraint `chk_amul_sale_positive_total`

So `Supabase.upsert(..., on_conflict="parlour_id,sale_date")` will **not** work
until a unique constraint is added first (otherwise PostgREST raises
`PGRST109` "The upsert `on_conflict` column list must... contain the primary
key or unique column".)

**Fix (two steps, in order):**
1. Add a unique constraint to `amul_daily_sales` (migration 017):
   ```sql
   ALTER TABLE public.amul_daily_sales
       ADD CONSTRAINT uq_amul_sale_parlour_date UNIQUE (parlour_id, sale_date);
   ```
2. Change `save_daily_sale` to use upsert instead of insert:
   ```python
   response = (
       client.table("amul_daily_sales")
       .upsert(payload, on_conflict="parlour_id,sale_date")
       .execute()
   )
   ```
   This makes the import idempotent — re-importing a date updates the amounts
   instead of creating a second row.

> Note: the manual SalesQuickAdd "Add" button also uses `save_daily_sale`, so it
> will benefit from the same idempotent upsert (adding the same date twice will
> update rather than duplicate).

---

## BUG P3 (MEDIUM): No invoice detail / line-item view

**File:** `frontend/src/components/parlour/InvoiceList.tsx`

**Problem:** The InvoiceList only shows a summary table (date, distributor, bill
no, type, total, delete). There's no detail view to see the extracted line items
(description, qty, rate, net amount). The backend has
`GET /amul/invoices/{id}` (returns invoice + items) and
`PATCH /amul/invoice-items/{id}`, but the frontend doesn't use them.

**Fix:** Add an expandable `InvoiceDetail` component that shows line items when
a row is clicked, with inline editing of item fields.

---

## BUG P4 (MEDIUM): No members management UI

**Problem:** The plan included a MembersManager component for the owner to
add/remove members (like Swapnil who enters data). The backend endpoints exist
(`/api/parlours/{id}/members` — GET/POST/PATCH/DELETE), but there's no UI for
it in the Parlour page.

**Fix:** Add a "Members" tab or section in the Parlour page (owner-only) showing
the member list with add-by-email and remove buttons.

---

## BUG P5 (LOW): No pagination on Sales table

**File:** `frontend/src/components/parlour/SalesTable.tsx`

**Problem:** All 138+ sales days render in one long table. With more data, this
will be slow and hard to navigate.

**Fix:** Add pagination (e.g., 20 rows per page) or a date-range filter at the
top of the table.

---

## BUG P6 (LOW): No inline editing of sales

**File:** `frontend/src/components/parlour/SalesTable.tsx`

**Problem:** If a sale was entered with wrong amounts, the user can only delete
and re-add. The backend has `PATCH /api/amul/sales/{id}`, but the frontend
SalesTable only has a delete button, no edit.

**Fix:** Add an edit mode to the SalesTable rows (click to edit cash/online,
then save via the update mutation).

---

## Summary — Priority order for fixes

| Priority | Bug | Fix effort |
|----------|-----|------------|
| 🔴 P0 | A1: compute_pnl doesn't filter by period | Backend: add month/quarter params + filtering |
| 🔴 P0 | A2: No month/quarter/year picker in UI | Frontend: add second dropdown + pass params |
| 🟡 P1 | A3: No "Day" period | Backend + Frontend: add day option + daily filter |
| 🟡 P1 | A4: Trends always month-level | Backend: make trends period-aware |
| 🟡 P1 | P2: WhatsApp import duplicates | Backend: use upsert |
| 🟡 P1 | P3: No invoice detail view | Frontend: add expandable detail component |
| 🟡 P1 | P4: No members management UI | Frontend: add Members tab |
| 🟢 P2 | A5: Wrong label for annual | Trivial fix |
| 🟢 P2 | P1: No Sarvam credits field in form | Small UI addition |
| 🟢 P2 | P5: No pagination | Medium UI work |
| 🟢 P2 | P6: No inline sale editing | Medium UI work |

---

## Fixes & Verification (all done)

**Backend (`business_engine.py`)**
- Added `day` to `PERIODS` / `period_key`.
- `compute_pnl(sales, invoices, period, period_value=..., expenses=..., year=...)`
  now filters rows to the selected bucket via `_matches_period`, so
  period_value="2026-07" returns ONLY July. (A1)
- Added `compute_trends(sales, invoices, period, period_value=..., expenses=...)`
  that buckets by day/month/quarter/year and derives the correct restriction
  prefix per period. `compute_monthly_trends` is kept as an alias. (A4, A3)
- Unit tests added for month/quarter/year/day filtering and quarter/year/day
  trends (in `tests/unit/test_business_engine.py`).

**Backend (`amul.py` analytics route)**
- Accepts `period_value` and passes `period` + `period_value` to both
  `compute_pnl` and `compute_trends`.

**Frontend**
- `useAmulAnalytics` now sends `period_value`; `PnLSummary`/`Trends` unchanged.
- New `PeriodPicker` component: Daily/Monthly/Quarterly/Annual with a
  contextual date / month+year / quarter+year / year selector. (A2, A3)
- `periodLabel` includes "Daily"; new `formatPeriodValue()` produces readable
  labels ("15 August 2026", "Q3 2026", ...) — fixes the annual label bug. (A5)
- New Parlour form now has a **Sarvam Starting Credits** field. (P1)
- `SalesTable`: 20-row pagination + per-row inline edit (check/cancel). (P5, P6)
- `InvoiceList` rows expand into `InvoiceDetail` showing extracted line items. (P3)
- New `MembersManager` + `useParlourMembers` hook, owner-only Members tab. (P4)

**Daily-sales idempotency (P2)**
- New migration `017_daily_sales_unique.sql` adds a UNIQUE constraint on
  `(parlour_id, sale_date)`.
- `save_daily_sale` now uses `.upsert(..., on_conflict="parlour_id,sale_date")`
  so re-importing a date updates amounts instead of inserting a duplicate.

**Verification evidence**

- Backend unit suite: **324 passed** (incl. new period-filtering tests).
- Frontend suite: **72 passed**; `npm run build` (tsc + vite) clean.
- `ruff check` clean on changed backend files.
- Live API test against the real 138-day dataset:

| Period | period_value | Total Sales | Expected |
|--------|--------------|-------------|----------|
| month  | `2026-07`    | ₹2,81,185   | July only ✓ |
| day    | `2026-08-15` | ₹8,519      | 2750+5769 ✓ |
| quarter| `2026-Q3`    | ₹4,18,586   | Jul+Aug ✓ |
| year   | `2026`       | ₹22,52,775  | 2026 only ✓ |
| month  | `2026-08`    | ₹1,37,401   | August only ✓ |

- Trend chart buckets now match the selected period (daily labels for day view,
  `YYYY-Qn` for quarter view, `YYYY` for year view).

**Note:** P2 also requires running `migrations/017_daily_sales_unique.sql` in
the Supabase SQL Editor before the upsert works (the unique constraint must
exist).
