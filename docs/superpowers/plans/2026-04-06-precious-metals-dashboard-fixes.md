# Precious Metals Expansion + Dashboard Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand gold-only tracking to gold/silver/platinum; fix Dashboard Net Worth, monthly expense auto-calc, and funded ratio.

**Architecture:** Unified `precious_metal_purchases` table with `metal_type` column. Metals.dev `/v1/latest` for all rates in one call. FIRE Settings renames `gold_pct` → `precious_metals_pct`. Dashboard auto-computes monthly expense from tracked expenses when FIRE Settings value is 0.

**Tech Stack:** FastAPI, Supabase (PostgreSQL), React + TypeScript, Streamlit, Pydantic v2, React Query

**Spec:** `docs/superpowers/specs/2026-04-06-precious-metals-expansion.md`

---

## File Map

### New Files
- `migrations/008_precious_metals.sql` — DB migration
- `backend/app/services/precious_metals_svc.py` — service (replaces gold_svc.py)
- `backend/app/routers/precious_metals.py` — API routes (replaces gold.py)
- `frontend/src/pages/PreciousMetals.tsx` — unified page (replaces GoldPortfolio.tsx)
- `frontend/src/hooks/usePreciousMetals.ts` — CRUD hook (replaces useGoldPurchases.ts)
- `frontend/src/hooks/useMetalRates.ts` — rates hook (replaces useGoldRate.ts)
- `frontend/src/hooks/useMetalsSummary.ts` — summary hook (replaces useGoldSummary.ts)
- `frontend/src/components/metals/MetalHoldingsTable.tsx` — table (replaces gold/)
- `frontend/src/components/metals/MetalPurchaseForm.tsx` — form
- `frontend/src/components/metals/MetalRateBar.tsx` — rate display
- `backend/tests/unit/test_precious_metals_svc.py` — service tests

### Modified Files
- `backend/app/core/models.py` — rename gold fields, add PreciousMetalPurchase model
- `backend/app/core/engine.py` — rename gold_pct/gold_return references
- `backend/app/core/constants.py` — rename FUNDS gold entry
- `backend/app/services/fire_inputs_svc.py` — no code change (uses select *)
- `backend/app/services/expenses_svc.py` — add monthly expense aggregation
- `backend/app/routers/projections.py` — auto-calc monthly expense from expenses
- `backend/app/main.py` — swap gold router for precious_metals router
- `frontend/src/hooks/useFireInputs.ts` — rename interface fields
- `frontend/src/pages/FireSettings.tsx` — rename form fields + labels
- `frontend/src/pages/Dashboard.tsx` — Net Worth fix, labels, metals integration
- `frontend/src/App.tsx` — route changes
- `pages/fire_settings.py` — Streamlit rename
- `pages/dashboard.py` — Streamlit Net Worth + labels
- `engine.py` — Streamlit engine rename
- `backend/tests/unit/test_engine_edge_cases.py` — rename fixtures
- `backend/tests/unit/test_models_validation.py` — rename fixtures

### Deleted Files (after new files are working)
- `backend/app/services/gold_svc.py`
- `backend/app/routers/gold.py`
- `frontend/src/pages/GoldPortfolio.tsx`
- `frontend/src/hooks/useGoldPurchases.ts`
- `frontend/src/hooks/useGoldRate.ts`
- `frontend/src/hooks/useGoldSummary.ts`
- `frontend/src/components/gold/` (entire directory)

---

## Phase 1: Dashboard Fixes

### Task 1: Auto-calculate monthly expense from tracked expenses

**Files:**
- Modify: `backend/app/services/expenses_svc.py`
- Modify: `backend/app/routers/projections.py`
- Test: `backend/tests/unit/test_expense_auto_calc.py`

- [ ] **Step 1: Write failing test for monthly expense aggregation**

Create `backend/tests/unit/test_expense_auto_calc.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/test_expense_auto_calc.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_monthly_expense_total'`

- [ ] **Step 3: Implement compute_monthly_expense_total**

Add to `backend/app/services/expenses_svc.py` (after existing functions):

```python
def compute_monthly_expense_total(expenses: list[dict]) -> float:
    """Compute total monthly expense from active recurring expenses.

    Monthly: as-is. Quarterly: /3. Yearly: /12. One-time: excluded.
    """
    divisors = {"monthly": 1, "quarterly": 3, "yearly": 12}
    total = 0.0
    for exp in expenses:
        freq = exp.get("frequency", "monthly")
        if freq in divisors:
            total += exp["amount"] / divisors[freq]
    return round(total, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/test_expense_auto_calc.py -v`
Expected: 6 passed

- [ ] **Step 5: Wire auto-calc into retirement projection endpoint**

Modify `backend/app/routers/projections.py` — update `_get_inputs()` to auto-compute monthly_expense when it's 0:

```python
from app.services import fire_inputs_svc, expenses_svc
from app.services.expenses_svc import compute_monthly_expense_total

def _get_inputs(user: CurrentUser) -> dict:
    raw = fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if raw is None:
        raise HTTPException(status_code=404, detail="Configure FIRE Settings first")
    # Auto-compute monthly_expense from tracked expenses when not manually set
    if raw.get("monthly_expense", 0) == 0:
        active_expenses = expenses_svc.load_fixed_expenses(user.id, user.access_token, active_only=True)
        raw = dict(raw)  # Don't mutate original
        raw["monthly_expense"] = compute_monthly_expense_total(active_expenses)
    return compute_derived_inputs(raw)
```

- [ ] **Step 6: Run all unit tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/ -v`
Expected: All pass (47+ tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/expenses_svc.py backend/app/routers/projections.py backend/tests/unit/test_expense_auto_calc.py
git commit -m "feat: auto-calculate monthly expense from tracked expenses for retirement projections"
```

---

### Task 2: Fix Dashboard Net Worth to include SIP invested

**Files:**
- Modify: `backend/app/services/sip_log_svc.py`
- Modify: `backend/app/routers/sip_log.py`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/hooks/useFireInputs.ts` (or new hook)

- [ ] **Step 1: Add total_invested aggregation to SIP log service**

Add to `backend/app/services/sip_log_svc.py`:

```python
def get_total_sip_invested(user_id: str, access_token: str) -> float:
    """Sum of actual_invested across all SIP log entries."""
    client = _get_client(access_token)
    result = client.table("sip_log").select("actual_invested").eq("user_id", user_id).execute()
    if not result.data:
        return 0.0
    return sum(row["actual_invested"] for row in result.data)
```

- [ ] **Step 2: Add API endpoint for total SIP invested**

Add to `backend/app/routers/sip_log.py`:

```python
@router.get("/sip-log/total-invested")
@limiter.limit("60/minute")
async def get_total_invested(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    total = sip_log_svc.get_total_sip_invested(user.id, user.access_token)
    return {"data": total}
```

- [ ] **Step 3: Create frontend hook for total SIP invested**

Create `frontend/src/hooks/useSipTotal.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useSipTotal() {
  return useQuery({
    queryKey: ["sip-log", "total-invested"],
    queryFn: () => api.get<{ data: number }>("/api/sip-log/total-invested").then((r) => r.data),
    staleTime: 15 * 60 * 1000, // 15 min
  });
}
```

- [ ] **Step 4: Update Dashboard Net Worth section**

In `frontend/src/pages/Dashboard.tsx`, add the hook import and update the Net Worth calculation:

Add import:
```typescript
import { useSipTotal } from "../hooks/useSipTotal";
```

Add hook call (after line 37):
```typescript
const sipTotal = useSipTotal();
```

Replace Net Worth computation (lines 96-98):
```typescript
const goldValue = goldSummary.summary?.current_value ?? 0;
const existingCorpus = inputs.existing_corpus ?? 0;
const totalSipInvested = sipTotal.data ?? 0;
const totalNetWorth = existingCorpus + totalSipInvested + goldValue;
```

Update the Net Worth section (lines 371-398) to show breakdown:
```tsx
<section className="bg-[#D4A843]/5 border border-[#D4A843]/20 rounded-2xl p-6">
  <h3 className="text-xs font-bold uppercase tracking-wider text-[#D4A843] mb-4">Net Worth</h3>
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div>
      <p className="text-xs text-[#E8ECF1]/50 mb-1">Existing Corpus</p>
      <p className="text-lg font-bold text-[#E8ECF1]" style={{ fontVariantNumeric: "tabular-nums" }}>
        {formatRupees(Math.round(existingCorpus))}
      </p>
    </div>
    <div>
      <p className="text-xs text-[#E8ECF1]/50 mb-1">SIP Invested</p>
      <p className="text-lg font-bold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
        {totalSipInvested > 0 ? formatRupees(Math.round(totalSipInvested)) : "--"}
      </p>
    </div>
    <div>
      <p className="text-xs text-[#E8ECF1]/50 mb-1">Gold Holdings</p>
      <p className="text-lg font-bold text-[#D4A843]" style={{ fontVariantNumeric: "tabular-nums" }}>
        {goldValue > 0 ? formatRupees(Math.round(goldValue)) : "--"}
      </p>
      {goldValue > 0 && goldSummary.summary && (
        <p className="text-[10px] text-[#E8ECF1]/40 mt-0.5">
          {goldSummary.summary.total_weight_grams}g physical gold
        </p>
      )}
    </div>
    <div>
      <p className="text-xs text-[#E8ECF1]/50 mb-1">Total Net Worth</p>
      <p className="text-lg font-bold text-[#00895E]" style={{ fontVariantNumeric: "tabular-nums" }}>
        {formatRupees(Math.round(totalNetWorth))}
      </p>
    </div>
  </div>
</section>
```

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd C:/Projects/fire-retirement-tracker/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/sip_log_svc.py backend/app/routers/sip_log.py frontend/src/hooks/useSipTotal.ts frontend/src/pages/Dashboard.tsx
git commit -m "feat: fix Net Worth to include SIP invested + precious metals value"
```

---

## Phase 2: Database Migration

### Task 3: Create migration for precious metals tables

**Files:**
- Create: `migrations/008_precious_metals.sql`

- [ ] **Step 1: Write the migration SQL**

Create `migrations/008_precious_metals.sql`:

```sql
-- Migration 008: Expand gold tracking to precious metals (gold, silver, platinum)
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 2.1: Rename gold_purchases → precious_metal_purchases
-- ============================================================
ALTER TABLE gold_purchases RENAME TO precious_metal_purchases;

-- Add metal_type column (default 'gold' for existing rows)
ALTER TABLE precious_metal_purchases
  ADD COLUMN metal_type TEXT NOT NULL DEFAULT 'gold';

-- Add CHECK for valid metal types
ALTER TABLE precious_metal_purchases
  ADD CONSTRAINT precious_metal_type_check
  CHECK (metal_type IN ('gold', 'silver', 'platinum'));

-- Drop old purity constraint, add metal-specific one
ALTER TABLE precious_metal_purchases
  DROP CONSTRAINT IF EXISTS gold_purchases_purity_check;
ALTER TABLE precious_metal_purchases
  ADD CONSTRAINT precious_metal_purity_check
  CHECK (
    (metal_type = 'gold'     AND purity IN ('24K', '22K', '18K'))
    OR (metal_type = 'silver'   AND purity IN ('999', '925', '900'))
    OR (metal_type = 'platinum' AND purity IN ('999', '950', '900'))
  );

-- Add index for metal_type queries
CREATE INDEX IF NOT EXISTS idx_precious_metal_type
  ON precious_metal_purchases(user_id, metal_type, is_active);

-- Recreate RLS policies (old ones reference table by name)
DROP POLICY IF EXISTS "Users can view own gold purchases" ON precious_metal_purchases;
DROP POLICY IF EXISTS "Users can insert own gold purchases" ON precious_metal_purchases;
DROP POLICY IF EXISTS "Users can update own gold purchases" ON precious_metal_purchases;
DROP POLICY IF EXISTS "Users can delete own gold purchases" ON precious_metal_purchases;

CREATE POLICY "Users can view own purchases"
  ON precious_metal_purchases FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own purchases"
  ON precious_metal_purchases FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own purchases"
  ON precious_metal_purchases FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own purchases"
  ON precious_metal_purchases FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2.2: Normalize rate cache
-- ============================================================
DROP TABLE IF EXISTS gold_rate_cache;

CREATE TABLE precious_metal_rate_cache (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metal_type    TEXT NOT NULL CHECK (metal_type IN ('gold', 'silver', 'platinum')),
  purity        TEXT NOT NULL,
  rate_per_gram NUMERIC NOT NULL CHECK (rate_per_gram > 0),
  currency      TEXT NOT NULL DEFAULT 'INR',
  source        TEXT NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metal_rate_latest
  ON precious_metal_rate_cache(metal_type, fetched_at DESC);

-- Auto-cleanup: delete rows older than 90 days
CREATE OR REPLACE FUNCTION cleanup_old_metal_rates() RETURNS TRIGGER AS $$
BEGIN
  DELETE FROM precious_metal_rate_cache WHERE fetched_at < now() - INTERVAL '90 days';
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cleanup_metal_rates
  AFTER INSERT ON precious_metal_rate_cache
  FOR EACH STATEMENT
  EXECUTE FUNCTION cleanup_old_metal_rates();

-- ============================================================
-- 2.3: FIRE Settings column rename
-- ============================================================
ALTER TABLE fire_inputs RENAME COLUMN gold_pct TO precious_metals_pct;
ALTER TABLE fire_inputs RENAME COLUMN gold_return TO precious_metals_return;

COMMIT;
```

- [ ] **Step 2: Review migration for safety**

Check that:
- All `DROP POLICY` names match actual policy names in `migrations/007_gold_portfolio.sql`
- `gold_purchases_purity_check` constraint name is correct
- Transaction wraps everything

- [ ] **Step 3: Commit migration (do NOT run yet)**

```bash
git add migrations/008_precious_metals.sql
git commit -m "feat: add migration 008 for precious metals expansion"
```

---

## Phase 3: FIRE Settings Rename (gold_pct → precious_metals_pct)

### Task 4: Rename backend model and engine

**Files:**
- Modify: `backend/app/core/models.py`
- Modify: `backend/app/core/engine.py`
- Modify: `backend/app/core/constants.py`

- [ ] **Step 1: Rename fields in Pydantic model**

In `backend/app/core/models.py`, replace all occurrences:
- `gold_return` → `precious_metals_return` (line 32)
- `gold_pct` → `precious_metals_pct` (line 37)
- Update allocation validator (line 49-57): `gold_pct` → `precious_metals_pct` in variable name and error message

```python
# Line 32
precious_metals_return: float = Field(ge=0, le=0.3)
# Line 37
precious_metals_pct: float = Field(ge=0, le=1.0)

# Validator (line 49-57)
@field_validator("cash_pct")
@classmethod
def allocation_sum(cls, v: float, info) -> float:
    equity_pct = info.data.get("equity_pct", 0)
    precious_metals_pct = info.data.get("precious_metals_pct", 0)
    total = equity_pct + precious_metals_pct + v
    if total > 1.0:
        raise ValueError("Equity + Precious Metals + Cash cannot exceed 100%")
    return v
```

- [ ] **Step 2: Rename in engine.py**

In `backend/app/core/engine.py`, find-and-replace:
- `gold_pct` → `precious_metals_pct` (all occurrences: lines 28, 63, 69, 98, 130, 236)
- `gold_return` → `precious_metals_return` (all occurrences: lines 65)

Key sections that change:

```python
# compute_derived_inputs (line 28)
d["debt_pct"] = 1.0 - d["equity_pct"] - d["precious_metals_pct"] - d["cash_pct"]

# blended_return (lines 63-69)
return (
    inputs["equity_pct"] * inputs["equity_return"]
    + debt_pct * inputs["debt_return"]
    + inputs["precious_metals_pct"] * inputs["precious_metals_return"]
    + inputs["cash_pct"] * inputs["cash_return"]
)
```

- [ ] **Step 3: Rename in constants.py**

In `backend/app/core/constants.py`, line ~51:
```python
# Before:
("Gold ETF", "gold", "gold_pct", 100, "Zerodha"),
# After:
("Precious Metals", "precious_metals", "precious_metals_pct", 100, "Zerodha"),
```

- [ ] **Step 4: Run unit tests — expect failures from fixtures**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/ -v`
Expected: FAIL in test_engine_edge_cases.py and test_models_validation.py (old field names)

- [ ] **Step 5: Fix test fixtures**

In `backend/tests/unit/test_engine_edge_cases.py`, find-and-replace:
- `"gold_pct"` → `"precious_metals_pct"`
- `"gold_return"` → `"precious_metals_return"`

In `backend/tests/unit/test_models_validation.py`, same replacements.

In `backend/tests/excel_verification/conftest.py`, same replacements (lines 39, 45).
In `backend/tests/excel_verification/test_02_fund_allocation.py`, same replacements (lines 15, 69).

- [ ] **Step 6: Run all tests — should pass**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/ -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/models.py backend/app/core/engine.py backend/app/core/constants.py backend/tests/
git commit -m "refactor: rename gold_pct/gold_return to precious_metals_pct/precious_metals_return in backend"
```

---

### Task 5: Rename in frontend

**Files:**
- Modify: `frontend/src/hooks/useFireInputs.ts`
- Modify: `frontend/src/pages/FireSettings.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Update TypeScript interface**

In `frontend/src/hooks/useFireInputs.ts`, rename in `FireInputsData` interface:
```typescript
precious_metals_return: number;  // was gold_return
precious_metals_pct: number;     // was gold_pct
```

- [ ] **Step 2: Update FireSettings.tsx**

Find-and-replace throughout the file:
- `gold_return` → `precious_metals_return`
- `gold_pct` → `precious_metals_pct`

Update the UI labels:
- "Gold" return field label → "Precious Metals"
- "Gold" allocation field label → "Precious Metals"

In DEFAULT_INPUTS:
```typescript
precious_metals_pct: 0.05,      // was gold_pct
precious_metals_return: 0.09,   // was gold_return
```

- [ ] **Step 3: Update Dashboard.tsx**

Find-and-replace `gold_pct` → `precious_metals_pct` in asset allocation section.
Update allocation pie chart label: `"Gold"` → `"Precious Metals"`.

```typescript
const allocationData = [
  { name: "Equity", value: Math.round(inputs.equity_pct * 100), color: "#00895E" },
  { name: "Precious Metals", value: Math.round(inputs.precious_metals_pct * 100), color: "#D4A843" },
  { name: "Cash", value: Math.round(inputs.cash_pct * 100), color: "#6B7280" },
  { name: "Debt", value: Math.round(debtPct * 100), color: "#1A3A5C" },
].filter((d) => d.value > 0);
```

Also update debtPct computation:
```typescript
const debtPct = 1 - inputs.equity_pct - inputs.precious_metals_pct - inputs.cash_pct;
```

- [ ] **Step 4: TypeScript check**

Run: `cd C:/Projects/fire-retirement-tracker/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useFireInputs.ts frontend/src/pages/FireSettings.tsx frontend/src/pages/Dashboard.tsx
git commit -m "refactor: rename gold_pct/gold_return to precious_metals in frontend"
```

---

### Task 6: Rename in Streamlit

**Files:**
- Modify: `engine.py`
- Modify: `pages/fire_settings.py`
- Modify: `pages/dashboard.py`
- Modify: `pages/growth_projection.py`

- [ ] **Step 1: Rename in Streamlit engine.py**

Find-and-replace throughout:
- `gold_pct` → `precious_metals_pct`
- `gold_return` → `precious_metals_return`

- [ ] **Step 2: Rename in pages/fire_settings.py**

Find-and-replace field names and update UI labels:
- `"gold_return"` → `"precious_metals_return"`
- `"gold_pct"` → `"precious_metals_pct"`
- Label "Gold Return" → "Precious Metals Return"
- Label "Gold %" → "Precious Metals %"

- [ ] **Step 3: Rename in pages/dashboard.py**

Update allocation references and chart labels.

- [ ] **Step 4: Rename in pages/growth_projection.py**

Update chart legend: "Debt + Gold + Cash" → "Debt + Metals + Cash".

- [ ] **Step 5: Validate Python syntax**

Run: `python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['engine.py', 'pages/fire_settings.py', 'pages/dashboard.py', 'pages/growth_projection.py']]; print('All OK')"`

- [ ] **Step 6: Commit**

```bash
git add engine.py pages/fire_settings.py pages/dashboard.py pages/growth_projection.py
git commit -m "refactor: rename gold_pct/gold_return to precious_metals in Streamlit"
```

---

## Phase 4: Backend — Precious Metals Service + Routes

### Task 7: Create precious_metals_svc.py with multi-metal support

**Files:**
- Create: `backend/app/services/precious_metals_svc.py`
- Create: `backend/tests/unit/test_precious_metals_svc.py`

This is the largest task. The service is a refactored copy of `gold_svc.py` with:
1. `metal_type` parameter on all CRUD functions
2. `/v1/latest` API call instead of `/v1/metal/spot`
3. Per-metal purity factors and sanity bounds
4. Normalized rate cache (one row per metal+purity)

- [ ] **Step 1: Write failing tests for purity factors and sanity bounds**

Create `backend/tests/unit/test_precious_metals_svc.py`:

```python
"""Tests for precious metals service — purity, sanity, rate parsing."""
import pytest


def test_purity_factors():
    from app.services.precious_metals_svc import PURITY_FACTORS
    assert PURITY_FACTORS["gold"]["24K"] == 1.0
    assert PURITY_FACTORS["gold"]["22K"] == pytest.approx(0.917, abs=0.001)
    assert PURITY_FACTORS["silver"]["999"] == 1.0
    assert PURITY_FACTORS["silver"]["925"] == 0.925
    assert PURITY_FACTORS["platinum"]["950"] == 0.95


def test_sanity_bounds():
    from app.services.precious_metals_svc import SANITY_BOUNDS
    gold_min, gold_max = SANITY_BOUNDS["gold"]
    assert gold_min == 1000
    assert gold_max == 500000
    silver_min, silver_max = SANITY_BOUNDS["silver"]
    assert silver_min == 50
    assert silver_max == 500


def test_compute_purity_rates_gold():
    from app.services.precious_metals_svc import compute_purity_rates
    rates = compute_purity_rates("gold", 8000.0)
    assert rates["24K"] == 8000.0
    assert rates["22K"] == pytest.approx(8000.0 * 22 / 24, abs=1)
    assert rates["18K"] == pytest.approx(8000.0 * 18 / 24, abs=1)


def test_compute_purity_rates_silver():
    from app.services.precious_metals_svc import compute_purity_rates
    rates = compute_purity_rates("silver", 100.0)
    assert rates["999"] == 100.0
    assert rates["925"] == pytest.approx(92.5, abs=0.1)
    assert rates["900"] == pytest.approx(90.0, abs=0.1)


def test_is_rate_sane():
    from app.services.precious_metals_svc import is_rate_sane
    assert is_rate_sane("gold", 8000.0) is True
    assert is_rate_sane("gold", 0.5) is False
    assert is_rate_sane("silver", 100.0) is True
    assert is_rate_sane("silver", 1000.0) is False
    assert is_rate_sane("platinum", 3000.0) is True
```

- [ ] **Step 2: Run tests — should fail**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/test_precious_metals_svc.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Create precious_metals_svc.py with constants and pure functions**

Create `backend/app/services/precious_metals_svc.py`. Start with the constants and pure functions (no API calls yet):

```python
"""Precious metals service — CRUD, rate fetching, portfolio summary.

Supports gold, silver, and platinum with per-metal purity factors,
sanity bounds, and live rate fetching from Metals.dev + GoldAPI.io fallback.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METAL_TYPES = ("gold", "silver", "platinum")

PURITY_FACTORS: dict[str, dict[str, float]] = {
    "gold": {"24K": 1.0, "22K": 22 / 24, "18K": 18 / 24},
    "silver": {"999": 1.0, "925": 0.925, "900": 0.90},
    "platinum": {"999": 1.0, "950": 0.95, "900": 0.90},
}

# Pure purity label per metal (used for base rate)
PURE_PURITY = {"gold": "24K", "silver": "999", "platinum": "999"}

SANITY_BOUNDS: dict[str, tuple[float, float]] = {
    "gold": (1000, 500000),
    "silver": (50, 500),
    "platinum": (1000, 200000),
}

# GoldAPI.io metal symbols
GOLDAPI_SYMBOLS = {"gold": "XAU", "silver": "XAG", "platinum": "XPT"}

# Troy ounce to gram conversion
TROY_OZ_TO_GRAMS = 31.1035

# Cache TTLs
MEMORY_CACHE_SECONDS = 6 * 3600   # 6 hours
DB_CACHE_SECONDS = 12 * 3600      # 12 hours


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def compute_purity_rates(metal: str, pure_rate: float) -> dict[str, float]:
    """Compute rates for all purities of a metal from the pure rate."""
    factors = PURITY_FACTORS[metal]
    return {purity: round(pure_rate * factor, 2) for purity, factor in factors.items()}


def is_rate_sane(metal: str, rate_per_gram: float) -> bool:
    """Check if a rate falls within plausible INR/gram range for the metal."""
    lo, hi = SANITY_BOUNDS[metal]
    return lo <= rate_per_gram <= hi
```

- [ ] **Step 4: Run tests — should pass**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/test_precious_metals_svc.py -v`
Expected: All 5 pass

- [ ] **Step 5: Add rate fetching functions (Metals.dev /v1/latest + GoldAPI.io fallback)**

Append to `precious_metals_svc.py`:

```python
# ---------------------------------------------------------------------------
# In-memory rate cache
# ---------------------------------------------------------------------------

_rate_cache: dict[str, dict] = {}  # keyed by metal_type


def _is_memory_fresh(metal: str) -> bool:
    entry = _rate_cache.get(metal)
    if not entry:
        return False
    age = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
    return age < MEMORY_CACHE_SECONDS


# ---------------------------------------------------------------------------
# Rate fetching — Metals.dev /v1/latest (all metals in one call)
# ---------------------------------------------------------------------------

def _fetch_from_metals_dev() -> Optional[dict[str, float]]:
    """Call Metals.dev /v1/latest. Returns {metal: rate_per_gram} or None."""
    settings = get_settings()
    if not settings.gold_api_key:
        logger.warning("GOLD_API_KEY not configured, skipping Metals.dev")
        return None

    try:
        url = "https://api.metals.dev/v1/latest"
        params = {"api_key": settings.gold_api_key, "currency": "INR"}
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
        resp.raise_for_status()
        body = resp.json()

        if body.get("status") != "success" or body.get("currency") != "INR":
            logger.error("Metals.dev unexpected response: %s", body)
            return None

        metals_data = body.get("metals", {})
        result = {}
        unit = body.get("unit", "toz")

        for metal in METAL_TYPES:
            price = metals_data.get(metal)
            if price is None:
                logger.warning("Metals.dev missing %s in response", metal)
                continue
            rate = float(price)
            if unit == "toz":
                rate = rate / TROY_OZ_TO_GRAMS
            if is_rate_sane(metal, rate):
                result[metal] = round(rate, 2)
            else:
                logger.error(
                    "Metals.dev %s rate outside sane range: %.2f INR/g",
                    metal, rate,
                )

        return result if result else None
    except Exception as e:
        logger.error("Metals.dev API call failed: %s", e)
        return None


def _fetch_from_goldapi(metal: str) -> Optional[float]:
    """Call GoldAPI.io for a single metal. Returns pure rate per gram or None."""
    settings = get_settings()
    if not settings.gold_api_key_fallback:
        return None

    symbol = GOLDAPI_SYMBOLS.get(metal)
    if not symbol:
        return None

    try:
        url = f"https://www.goldapi.io/api/{symbol}/INR"
        headers = {"x-access-token": settings.gold_api_key_fallback}
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()

        # GoldAPI returns per-gram prices directly
        key = "price_gram_24k" if metal == "gold" else "price_gram_24k"
        rate = float(body.get(key, 0))
        if rate <= 0:
            logger.error("GoldAPI.io %s returned invalid rate: %s", metal, body)
            return None
        if not is_rate_sane(metal, rate):
            logger.error("GoldAPI.io %s rate outside sane range: %.2f", metal, rate)
            return None
        return round(rate, 2)
    except Exception as e:
        logger.error("GoldAPI.io %s API call failed: %s", metal, e)
        return None
```

- [ ] **Step 6: Add CRUD functions (load, save, update, deactivate)**

Append to `precious_metals_svc.py`:

```python
# ---------------------------------------------------------------------------
# Supabase client helpers
# ---------------------------------------------------------------------------

def _get_client(access_token: str):
    from db import get_supabase_client_with_token
    return get_supabase_client_with_token(access_token)


def _get_anon_client():
    from db import get_supabase_client
    return get_supabase_client()


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

TABLE = "precious_metal_purchases"


def load_purchases(
    user_id: str, access_token: str, metal_type: Optional[str] = None, active_only: bool = True,
) -> list[dict]:
    client = _get_client(access_token)
    query = client.table(TABLE).select("*").eq("user_id", user_id)
    if active_only:
        query = query.eq("is_active", True)
    if metal_type:
        query = query.eq("metal_type", metal_type)
    result = query.order("purchase_date", desc=True).execute()
    return result.data or []


def save_purchase(user_id: str, data: dict, access_token: str) -> dict:
    client = _get_client(access_token)
    row = {**data, "user_id": user_id}
    result = client.table(TABLE).insert(row).execute()
    return result.data[0] if result.data else {}


def update_purchase(purchase_id: str, user_id: str, data: dict, access_token: str) -> Optional[dict]:
    client = _get_client(access_token)
    # Reject updates on deactivated rows
    existing = client.table(TABLE).select("is_active").eq("id", purchase_id).eq("user_id", user_id).execute()
    if not existing.data or not existing.data[0].get("is_active"):
        from app.core.errors import DataNotFoundError
        raise DataNotFoundError("Purchase not found or already deactivated")
    result = client.table(TABLE).update(data).eq("id", purchase_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def deactivate_purchase(purchase_id: str, user_id: str, access_token: str) -> Optional[dict]:
    client = _get_client(access_token)
    existing = client.table(TABLE).select("is_active").eq("id", purchase_id).eq("user_id", user_id).execute()
    if not existing.data or not existing.data[0].get("is_active"):
        from app.core.errors import DataNotFoundError
        raise DataNotFoundError("Purchase not found or already deactivated")
    result = client.table(TABLE).update({"is_active": False}).eq("id", purchase_id).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None
```

- [ ] **Step 7: Add get_rates and portfolio summary functions**

Append to `precious_metals_svc.py`:

```python
# ---------------------------------------------------------------------------
# Rate retrieval (3-tier cache)
# ---------------------------------------------------------------------------

def get_rates(metal: Optional[str] = None) -> dict:
    """Get current rates for one or all metals.

    Returns: {"gold": {"24K": rate, "22K": rate, ...}, "silver": {...}, ...}
    Plus "source", "fetched_at", "is_stale" per metal.
    """
    metals = [metal] if metal else list(METAL_TYPES)
    result = {}
    stale_metals = []

    # Tier 1: Memory cache
    for m in metals:
        if _is_memory_fresh(m):
            result[m] = _rate_cache[m]["rates"]
        else:
            stale_metals.append(m)

    if not stale_metals:
        return result

    # Tier 2: DB cache (check for each stale metal)
    db_stale = []
    try:
        anon = _get_anon_client()
        for m in stale_metals:
            rows = (
                anon.table("precious_metal_rate_cache")
                .select("purity, rate_per_gram, source, fetched_at")
                .eq("metal_type", m)
                .order("fetched_at", desc=True)
                .limit(10)
                .execute()
            )
            if rows.data:
                fetched = datetime.fromisoformat(rows.data[0]["fetched_at"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - fetched).total_seconds()
                if age < DB_CACHE_SECONDS:
                    rates = {r["purity"]: r["rate_per_gram"] for r in rows.data}
                    result[m] = rates
                    _rate_cache[m] = {"rates": rates, "timestamp": datetime.now(timezone.utc)}
                    continue
            db_stale.append(m)
    except Exception as e:
        logger.error("DB rate cache read failed: %s", e)
        db_stale = stale_metals

    if not db_stale:
        return result

    # Tier 3: External API
    api_rates = _fetch_from_metals_dev()
    for m in db_stale:
        pure_rate = api_rates.get(m) if api_rates else None
        if pure_rate is None:
            # Fallback per metal
            pure_rate = _fetch_from_goldapi(m)
        if pure_rate is not None:
            rates = compute_purity_rates(m, pure_rate)
            result[m] = rates
            _rate_cache[m] = {"rates": rates, "timestamp": datetime.now(timezone.utc)}
            # Persist to DB
            _save_rates_to_db(m, rates)

    return result


def _save_rates_to_db(metal: str, rates: dict[str, float]) -> None:
    try:
        anon = _get_anon_client()
        rows = [
            {
                "metal_type": metal,
                "purity": purity,
                "rate_per_gram": rate,
                "source": "metals.dev",
                "currency": "INR",
            }
            for purity, rate in rates.items()
        ]
        anon.table("precious_metal_rate_cache").insert(rows).execute()
    except Exception as e:
        logger.error("Failed to save %s rates to DB: %s", metal, e)


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------

def compute_portfolio_summary(
    user_id: str, access_token: str, metal_type: Optional[str] = None,
) -> dict:
    """Compute portfolio summary with live rates."""
    purchases = load_purchases(user_id, access_token, metal_type=metal_type)
    rates = get_rates()

    total_cost = 0.0
    current_value = 0.0
    by_metal: dict[str, dict] = {}
    by_owner: dict[str, dict] = {}

    for p in purchases:
        metal = p["metal_type"]
        purity = p["purity"]
        cost = float(p.get("total_cost", 0) or p["weight_grams"] * p["price_per_gram"])
        total_cost += cost

        # Current value from live rate
        metal_rates = rates.get(metal, {})
        rate = metal_rates.get(purity, 0)
        value = p["weight_grams"] * rate
        current_value += value

        # By metal
        if metal not in by_metal:
            by_metal[metal] = {"metal": metal, "weight_grams": 0, "cost": 0, "value": 0, "pnl": 0}
        by_metal[metal]["weight_grams"] += p["weight_grams"]
        by_metal[metal]["cost"] += cost
        by_metal[metal]["value"] += value

        # By owner
        owner = p.get("owner", "household")
        if owner not in by_owner:
            by_owner[owner] = {"owner": owner, "weight_grams": 0, "cost": 0, "value": 0, "pnl": 0}
        by_owner[owner]["weight_grams"] += p["weight_grams"]
        by_owner[owner]["cost"] += cost
        by_owner[owner]["value"] += value

    # Compute PnL
    total_pnl = current_value - total_cost
    for d in list(by_metal.values()) + list(by_owner.values()):
        d["pnl"] = d["value"] - d["cost"]

    return {
        "total_weight_grams": sum(d["weight_grams"] for d in by_metal.values()),
        "total_cost": round(total_cost, 2),
        "current_value": round(current_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_cost * 100) if total_cost > 0 else 0, 2),
        "by_metal": list(by_metal.values()),
        "by_owner": list(by_owner.values()),
        "rate_used": rates,
    }
```

- [ ] **Step 8: Run tests**

Run: `cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/test_precious_metals_svc.py -v`
Expected: All pass

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/precious_metals_svc.py backend/tests/unit/test_precious_metals_svc.py
git commit -m "feat: add precious_metals_svc with multi-metal CRUD, rates, and portfolio summary"
```

---

### Task 8: Create precious_metals router and wire into main.py

**Files:**
- Create: `backend/app/routers/precious_metals.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/models.py` (add PreciousMetalPurchase model)

- [ ] **Step 1: Add Pydantic models for precious metal purchases**

Add to `backend/app/core/models.py` (after existing GoldPurchase class — which will be replaced):

```python
class PreciousMetalPurchase(BaseModel):
    """New precious metal purchase entry."""
    metal_type: Literal["gold", "silver", "platinum"]
    purchase_date: date
    weight_grams: float = Field(gt=0, le=100000)
    price_per_gram: float = Field(gt=0, le=1000000)
    purity: str = Field(max_length=5)
    owner: Literal["you", "wife", "household"] = "household"
    notes: str = Field(max_length=500, default="")

    @model_validator(mode="after")
    def validate_purity_for_metal(self):
        valid = {
            "gold": ("24K", "22K", "18K"),
            "silver": ("999", "925", "900"),
            "platinum": ("999", "950", "900"),
        }
        allowed = valid.get(self.metal_type, ())
        if self.purity not in allowed:
            raise ValueError(f"Invalid purity '{self.purity}' for {self.metal_type}. Must be one of {allowed}")
        return self

    @field_validator("purchase_date")
    @classmethod
    def purchase_date_in_range(cls, v: date) -> date:
        from datetime import date as date_type
        if not (date_type(2000, 1, 1) <= v <= date_type.today()):
            raise ValueError("purchase_date must be between 2000-01-01 and today")
        return v


class PreciousMetalPurchaseUpdate(BaseModel):
    """Partial update for a precious metal purchase."""
    purchase_date: Optional[date] = None
    weight_grams: Optional[float] = Field(None, gt=0, le=100000)
    price_per_gram: Optional[float] = Field(None, gt=0, le=1000000)
    purity: Optional[str] = Field(None, max_length=5)
    owner: Optional[Literal["you", "wife", "household"]] = None
    notes: Optional[str] = Field(None, max_length=500)
```

- [ ] **Step 2: Create the router**

Create `backend/app/routers/precious_metals.py`:

```python
"""Precious metals API routes — purchases, rates, portfolio summary."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from app.core.models import PreciousMetalPurchase, PreciousMetalPurchaseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import precious_metals_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["precious-metals"])


@router.get("/precious-metals")
@limiter.limit("60/minute")
async def list_purchases(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    metal: Optional[str] = Query(None),
    active: bool = Query(True),
) -> dict:
    data = precious_metals_svc.load_purchases(user.id, user.access_token, metal_type=metal, active_only=active)
    return {"data": data}


@router.post("/precious-metals")
@limiter.limit("30/minute")
async def create_purchase(
    request: Request,
    body: PreciousMetalPurchase,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    data = body.model_dump()
    data["purchase_date"] = str(data["purchase_date"])
    result = precious_metals_svc.save_purchase(user.id, data, user.access_token)
    log_audit(user.id, "create_precious_metal_purchase", {"metal": body.metal_type}, user.access_token)
    return {"data": result}


@router.patch("/precious-metals/{purchase_id}")
@limiter.limit("30/minute")
async def update_purchase(
    request: Request,
    purchase_id: str,
    body: PreciousMetalPurchaseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    data = body.model_dump(exclude_none=True)
    if "purchase_date" in data:
        data["purchase_date"] = str(data["purchase_date"])
    result = precious_metals_svc.update_purchase(purchase_id, user.id, data, user.access_token)
    log_audit(user.id, "update_precious_metal_purchase", {"id": purchase_id}, user.access_token)
    return {"data": result}


@router.delete("/precious-metals/{purchase_id}")
@limiter.limit("10/minute")
async def deactivate_purchase(
    request: Request,
    purchase_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    precious_metals_svc.deactivate_purchase(purchase_id, user.id, user.access_token)
    log_audit(user.id, "deactivate_precious_metal_purchase", {"id": purchase_id}, user.access_token)
    return {"message": "Purchase deactivated"}


@router.get("/precious-metals/rates")
@limiter.limit("60/minute")
async def get_rates(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    rates = precious_metals_svc.get_rates()
    return {"data": rates}


@router.get("/precious-metals/summary")
@limiter.limit("30/minute")
async def get_summary(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    metal: Optional[str] = Query(None),
) -> dict:
    summary = precious_metals_svc.compute_portfolio_summary(user.id, user.access_token, metal_type=metal)
    return {"data": summary}
```

- [ ] **Step 3: Register new router, remove old gold router**

In `backend/app/main.py`, replace:
```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, gold
# ...
app.include_router(gold.router, prefix="/api")
```

With:
```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals
# ...
app.include_router(precious_metals.router, prefix="/api")
```

- [ ] **Step 4: Verify server starts**

Run: `cd C:/Projects/fire-retirement-tracker && python -c "from app.main import app; print('OK')"`
Expected: OK (no import errors)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/models.py backend/app/routers/precious_metals.py backend/app/main.py
git commit -m "feat: add precious metals API routes with multi-metal support"
```

---

## Phase 5: Frontend — Unified Precious Metals Page

### Task 9: Create frontend hooks for precious metals

**Files:**
- Create: `frontend/src/hooks/usePreciousMetals.ts`
- Create: `frontend/src/hooks/useMetalRates.ts`
- Create: `frontend/src/hooks/useMetalsSummary.ts`

- [ ] **Step 1: Create usePreciousMetals.ts**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface PreciousMetalEntry {
  id?: string;
  metal_type: "gold" | "silver" | "platinum";
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  total_cost?: number;
  purity: string;
  owner: "you" | "wife" | "household";
  notes?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export function usePreciousMetals(filters: { active?: boolean; metal?: string } = {}) {
  const qc = useQueryClient();
  const params = new URLSearchParams();
  if (filters.active !== undefined) params.set("active", String(filters.active));
  if (filters.metal) params.set("metal", filters.metal);
  const qs = params.toString() ? `?${params}` : "";

  const query = useQuery({
    queryKey: ["precious-metals", filters],
    queryFn: () => api.get<{ data: PreciousMetalEntry[] }>(`/api/precious-metals${qs}`).then((r) => r.data),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["precious-metals"] });
    qc.invalidateQueries({ queryKey: ["metals-summary"] });
  };

  const save = useMutation({ mutationFn: (data: Omit<PreciousMetalEntry, "id">) => api.post("/api/precious-metals", data), onSuccess: invalidate });
  const update = useMutation({ mutationFn: ({ id, ...data }: { id: string } & Partial<PreciousMetalEntry>) => api.patch(`/api/precious-metals/${id}`, data), onSuccess: invalidate });
  const deactivate = useMutation({ mutationFn: (id: string) => api.delete(`/api/precious-metals/${id}`), onSuccess: invalidate });

  return { entries: query.data ?? [], isLoading: query.isLoading, save: save.mutateAsync, update: update.mutateAsync, deactivate: deactivate.mutateAsync };
}
```

- [ ] **Step 2: Create useMetalRates.ts**

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export type MetalRates = Record<string, Record<string, number>>;

export function useMetalRates() {
  return useQuery({
    queryKey: ["metal-rates"],
    queryFn: () => api.get<{ data: MetalRates }>("/api/precious-metals/rates").then((r) => r.data),
    staleTime: 6 * 60 * 60 * 1000,
    refetchInterval: 6 * 60 * 60 * 1000,
  });
}
```

- [ ] **Step 3: Create useMetalsSummary.ts**

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface MetalBreakdown {
  metal: string;
  weight_grams: number;
  cost: number;
  value: number;
  pnl: number;
}

export interface MetalsSummary {
  total_weight_grams: number;
  total_cost: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  by_metal: MetalBreakdown[];
  by_owner: { owner: string; weight_grams: number; cost: number; value: number; pnl: number }[];
  rate_used: Record<string, Record<string, number>>;
}

export function useMetalsSummary(metal?: string) {
  const qs = metal ? `?metal=${metal}` : "";
  return useQuery({
    queryKey: ["metals-summary", metal],
    queryFn: () => api.get<{ data: MetalsSummary }>(`/api/precious-metals/summary${qs}`).then((r) => r.data),
    staleTime: 15 * 60 * 1000,
  });
}
```

- [ ] **Step 4: TypeScript check**

Run: `cd C:/Projects/fire-retirement-tracker/frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/usePreciousMetals.ts frontend/src/hooks/useMetalRates.ts frontend/src/hooks/useMetalsSummary.ts
git commit -m "feat: add frontend hooks for precious metals CRUD, rates, and summary"
```

---

### Task 10: Create unified PreciousMetals page and components

**Files:**
- Create: `frontend/src/components/metals/MetalRateBar.tsx`
- Create: `frontend/src/components/metals/MetalPurchaseForm.tsx`
- Create: `frontend/src/components/metals/MetalHoldingsTable.tsx`
- Create: `frontend/src/pages/PreciousMetals.tsx`
- Modify: `frontend/src/App.tsx` — update routes

This task involves creating 4 new UI files. These are refactored copies of the gold components with `metal_type` support, tab filtering, and color coding. Due to size, the implementer should:

- [ ] **Step 1: Create MetalRateBar.tsx**

Copy from `frontend/src/components/gold/GoldRateBar.tsx`. Changes:
- Accept `rates: MetalRates` (all metals) and `selectedMetal: string | null`
- When selectedMetal is set, show only that metal's rates
- When null ("All"), show all metals' rates in a row
- Color-code per metal: gold `#D4A843`, silver `#C0C0C0`, platinum `#A0B2C6`

- [ ] **Step 2: Create MetalPurchaseForm.tsx**

Copy from `frontend/src/components/gold/GoldPurchaseForm.tsx`. Changes:
- Add metal_type dropdown as first field (default: "gold")
- Purity dropdown options change based on selected metal_type:
  - gold → 24K, 22K, 18K
  - silver → 999, 925, 900
  - platinum → 999, 950, 900

- [ ] **Step 3: Create MetalHoldingsTable.tsx**

Copy from `frontend/src/components/gold/GoldHoldingsTable.tsx`. Changes:
- Add "Metal" column after Date
- Color-coded metal badges
- Accept `rate` as `MetalRates` (all metals) instead of single number
- P&L calculation uses correct rate per metal+purity

- [ ] **Step 4: Create PreciousMetals.tsx page**

Copy structure from `frontend/src/pages/GoldPortfolio.tsx`. Changes:
- Add metal tab bar: Gold | Silver | Platinum | All
- Pass selected metal filter to hooks
- Use new components (MetalRateBar, MetalPurchaseForm, MetalHoldingsTable)

- [ ] **Step 5: Update App.tsx routes**

Remove the `/gold-portfolio` route, add `/precious-metals`:
```tsx
<Route path="/precious-metals" element={<ProtectedRoute><PreciousMetals /></ProtectedRoute>} />
```

Update nav menu label from "Gold Portfolio" to "Precious Metals".

- [ ] **Step 6: Update Dashboard to use new metals summary**

In `Dashboard.tsx`, replace `useGoldSummary` with `useMetalsSummary`. Update Net Worth section:
- "Gold Holdings" → "Precious Metals"
- Use `metalsSummary.data?.current_value` instead of `goldSummary.summary?.current_value`

- [ ] **Step 7: TypeScript check and verify**

Run: `cd C:/Projects/fire-retirement-tracker/frontend && npx tsc --noEmit`

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/metals/ frontend/src/pages/PreciousMetals.tsx frontend/src/App.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat: add unified Precious Metals page with gold/silver/platinum support"
```

---

## Phase 6: Cleanup

### Task 11: Delete old gold-specific files

**Files:**
- Delete: `backend/app/services/gold_svc.py`
- Delete: `backend/app/routers/gold.py`
- Delete: `frontend/src/pages/GoldPortfolio.tsx`
- Delete: `frontend/src/hooks/useGoldPurchases.ts`
- Delete: `frontend/src/hooks/useGoldRate.ts`
- Delete: `frontend/src/hooks/useGoldSummary.ts`
- Delete: `frontend/src/components/gold/` (entire directory)

- [ ] **Step 1: Verify no remaining imports of old files**

Search for any remaining references:
```bash
grep -r "gold_svc\|useGoldPurchases\|useGoldRate\|useGoldSummary\|GoldPortfolio\|GoldHoldingsTable\|GoldPurchaseForm\|GoldRateBar" frontend/src/ backend/app/ --include="*.ts" --include="*.tsx" --include="*.py" | grep -v node_modules | grep -v __pycache__
```

Fix any remaining imports.

- [ ] **Step 2: Delete old files**

```bash
rm backend/app/services/gold_svc.py
rm backend/app/routers/gold.py
rm frontend/src/pages/GoldPortfolio.tsx
rm frontend/src/hooks/useGoldPurchases.ts
rm frontend/src/hooks/useGoldRate.ts
rm frontend/src/hooks/useGoldSummary.ts
rm -rf frontend/src/components/gold/
```

- [ ] **Step 3: Verify everything still compiles**

```bash
cd C:/Projects/fire-retirement-tracker && python -m pytest backend/tests/unit/ -v
cd C:/Projects/fire-retirement-tracker/frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old gold-specific files replaced by precious metals"
```

---

### Task 12: Run migration on Supabase

- [ ] **Step 1: Run migration 008 in Supabase SQL Editor**

Copy contents of `migrations/008_precious_metals.sql` and execute in Supabase SQL Editor. Verify:
- `precious_metal_purchases` table exists with `metal_type` column
- Existing gold rows have `metal_type = 'gold'`
- `precious_metal_rate_cache` table exists
- `fire_inputs` table has `precious_metals_pct` and `precious_metals_return` columns
- RLS policies are active

- [ ] **Step 2: Smoke test the app end-to-end**

Verify in browser:
- Dashboard loads with correct Net Worth (corpus + SIP + metals)
- Monthly expense auto-calculated → Funded Ratio is non-zero
- Precious Metals page shows existing gold purchases
- Can add a new silver purchase
- FIRE Settings shows "Precious Metals" labels
- Growth projection chart shows "Debt + Metals + Cash"

- [ ] **Step 3: Final commit + push**

```bash
git push
```
