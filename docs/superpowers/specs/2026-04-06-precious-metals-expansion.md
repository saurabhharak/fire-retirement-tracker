# Precious Metals Expansion + Dashboard Fixes

**Date**: 2026-04-06
**Status**: Approved
**Scope**: Expand gold-only tracking to gold/silver/platinum unified page; fix Dashboard bugs

---

## 1. Overview

Expand the existing gold portfolio tracker into a unified "Precious Metals" tracker supporting gold, silver, and platinum. Simultaneously fix Dashboard calculation bugs (Net Worth, monthly expense auto-calculation, funded ratio).

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Page structure | Unified page with metal tab filter | Investors think of precious metals as one asset class |
| FIRE allocation | Single "precious metals" bucket | Over-engineering to split per-metal allocations for a FIRE tracker |
| DB column rename | Yes — `gold_pct` → `precious_metals_pct` | Clean code > expedience; it's mechanical find-and-replace |
| Rate API | Metals.dev `/v1/latest` — single call for all metals | Free tier, 60s max delay, returns gold/silver/platinum in one JSON response |
| Backward compat routes | No | Personal 2-user app; clean cut, no redirects |

---

## 2. Database Migration

### 2.1 Rename & Extend `gold_purchases` → `precious_metal_purchases`

```sql
-- Step 1: Rename table
ALTER TABLE gold_purchases RENAME TO precious_metal_purchases;

-- Step 2: Add metal_type column with default for existing rows
ALTER TABLE precious_metal_purchases
  ADD COLUMN metal_type TEXT NOT NULL DEFAULT 'gold'
  CHECK (metal_type IN ('gold', 'silver', 'platinum'));

-- Step 3: Expand purity CHECK constraint
-- Drop old constraint, add new metal-specific one
ALTER TABLE precious_metal_purchases DROP CONSTRAINT IF EXISTS gold_purchases_purity_check;
ALTER TABLE precious_metal_purchases ADD CONSTRAINT precious_metal_purity_check
  CHECK (
    (metal_type = 'gold'     AND purity IN ('24K', '22K', '18K'))
    OR (metal_type = 'silver'   AND purity IN ('999', '925', '900'))
    OR (metal_type = 'platinum' AND purity IN ('999', '950', '900'))
  );

-- Step 4: Add index for metal_type queries
CREATE INDEX idx_precious_metal_type ON precious_metal_purchases(user_id, metal_type, is_active);

-- Step 5: Drop and recreate ALL 4 RLS policies (they reference table name)
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
```

### 2.2 Normalize Rate Cache → `precious_metal_rate_cache`

Replace wide-column design with normalized rows:

```sql
DROP TABLE IF EXISTS gold_rate_cache;

CREATE TABLE precious_metal_rate_cache (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metal_type TEXT NOT NULL CHECK (metal_type IN ('gold', 'silver', 'platinum')),
  purity     TEXT NOT NULL,
  rate_per_gram NUMERIC NOT NULL,
  currency   TEXT NOT NULL DEFAULT 'INR',
  source     TEXT NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metal_rate_latest ON precious_metal_rate_cache(metal_type, fetched_at DESC);

-- Auto-cleanup: rows older than 90 days
-- (same trigger pattern as existing gold_rate_cache)
```

### 2.3 FIRE Settings Column Rename

```sql
ALTER TABLE fire_inputs RENAME COLUMN gold_pct TO precious_metals_pct;
ALTER TABLE fire_inputs RENAME COLUMN gold_return TO precious_metals_return;
```

**Blast radius** (all mechanical rename — find-and-replace):
- `backend/app/core/models.py` — FireInputs model
- `backend/app/core/engine.py` — blended_return, compute_derived_inputs, compute_fund_allocation, compute_growth_projection
- `backend/app/core/constants.py` — FUNDS list
- `backend/app/services/fire_inputs_svc.py` — upsert
- `frontend/src/pages/Dashboard.tsx` — allocation pie
- `frontend/src/pages/FireSettings.tsx` — form fields
- `frontend/src/hooks/useFireInputs.ts` — interface
- `pages/fire_settings.py` — Streamlit form
- `pages/dashboard.py` — Streamlit allocation
- `pages/growth_projection.py` — Streamlit chart
- `backend/tests/unit/` — all test files referencing gold_pct/gold_return

### 2.4 Purity Factors

| Metal | Purity | Factor | Label |
|-------|--------|--------|-------|
| Gold | 24K | 1.000 | Pure Gold |
| Gold | 22K | 0.917 | Jewelry Gold |
| Gold | 18K | 0.750 | 18 Karat |
| Silver | 999 | 1.000 | Fine Silver |
| Silver | 925 | 0.925 | Sterling Silver |
| Silver | 900 | 0.900 | Coin Silver |
| Platinum | 999 | 1.000 | Fine Platinum |
| Platinum | 950 | 0.950 | Jewelry Platinum |
| Platinum | 900 | 0.900 | Coin Platinum |

---

## 3. Backend Service

### 3.1 Rename `gold_svc.py` → `precious_metals_svc.py`

All functions gain a `metal_type` parameter. Logic stays identical — only rate sanity bounds and purity mappings differ per metal.

### 3.2 Rate Fetching — Switch to `/v1/latest`

**Current**: `GET /v1/metal/spot?metal=gold&currency=INR` — one metal per call.

**New**: `GET /v1/latest?api_key=KEY&currency=INR` — all metals in one call.

Default unit is troy ounces (toz). Convert to grams using existing `_toz_to_gram()` (divide by 31.1035). Do NOT pass `unit=g` — it may not be supported on all plans.

Response structure:
```json
{
  "status": "success",
  "currency": "INR",
  "unit": "toz",
  "metals": {
    "gold": 244150.00,
    "silver": 2968.00,
    "platinum": 99520.00
  }
}
```

Parse all three metals from one response. Apply per-metal sanity bounds:

| Metal | Min INR/gram | Max INR/gram |
|-------|-------------|-------------|
| Gold | 1,000 | 500,000 |
| Silver | 50 | 500 |
| Platinum | 1,000 | 200,000 |

Same 3-tier caching (memory 6hr → DB 12hr → API), but cache keyed per metal. Single API call populates all three metals' caches simultaneously.

### 3.3 Fallback API — GoldAPI.io

Extend to support multiple metals:
- Gold: `GET /api/XAU/INR`
- Silver: `GET /api/XAG/INR`
- Platinum: `GET /api/XPT/INR`

Three separate calls only triggered if Metals.dev `/v1/latest` fails. Each returns `price_gram_*` fields.

### 3.4 Portfolio Summary

`compute_portfolio_summary()` accepts optional `metal_type` filter.

When `metal=all`, returns:
```python
{
  "total_cost": float,        # All metals combined
  "current_value": float,     # All metals combined
  "total_pnl": float,
  "total_pnl_pct": float,
  "by_metal": [
    {"metal": "gold", "weight_grams": ..., "cost": ..., "value": ..., "pnl": ...},
    {"metal": "silver", ...},
    {"metal": "platinum", ...},
  ],
  "by_owner": [...],
  "rate_used": {...},
}
```

Note: "All" view shows value-based aggregation only. Summing grams across metals is meaningless — weights are per-metal only.

### 3.5 Pydantic Validation

```python
class PreciousMetalPurchase(BaseModel):
    metal_type: Literal["gold", "silver", "platinum"]
    purchase_date: date
    weight_grams: float = Field(gt=0, le=100000)
    price_per_gram: float = Field(gt=0, le=1000000)
    purity: str
    owner: Literal["you", "wife", "household"] = "household"
    notes: str = Field(max_length=500, default="")

    @model_validator(mode="after")
    def validate_purity_for_metal(self):
        valid = {
            "gold": ("24K", "22K", "18K"),
            "silver": ("999", "925", "900"),
            "platinum": ("999", "950", "900"),
        }
        if self.purity not in valid[self.metal_type]:
            raise ValueError(
                f"Invalid purity '{self.purity}' for {self.metal_type}. "
                f"Must be one of {valid[self.metal_type]}"
            )
        return self
```

---

## 4. Backend API Routes

Rename `/api/gold-*` → `/api/precious-metals/*`. No backward compat redirects.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/precious-metals?metal=gold&active=true` | List purchases (filterable) |
| POST | `/api/precious-metals` | Create purchase (body includes metal_type) |
| PATCH | `/api/precious-metals/{id}` | Update purchase |
| DELETE | `/api/precious-metals/{id}` | Soft-delete |
| GET | `/api/precious-metals/rates` | All metal rates in one response |
| GET | `/api/precious-metals/summary?metal=all` | Portfolio summary (filterable) |

Rate limits: same as current gold endpoints (60/min read, 30/min write, 10/min delete).

---

## 5. Frontend

### 5.1 Unified Page — `PreciousMetals.tsx`

Rename `GoldPortfolio.tsx` → `PreciousMetals.tsx`. Route: `/precious-metals`.

Layout:
1. **Header**: "Precious Metals — Track your gold, silver & platinum"
2. **Metal Tab Bar**: `Gold | Silver | Platinum | All` — filters entire page
3. **Summary Cards** (4 cols): Total Weight, Total Invested, Current Value, P&L
4. **Rate Bar**: Live rates for selected metal(s)
5. **Purchase Form**: Metal type dropdown → auto-adjusts purity options
6. **Holdings Table**: Metal column added, color-coded badges

### 5.2 Color Scheme

| Metal | Badge Color | Semantic |
|-------|------------|----------|
| Gold | `#D4A843` | Warm gold (existing) |
| Silver | `#C0C0C0` | Silver |
| Platinum | `#A0B2C6` | Cool steel blue |

### 5.3 Hooks Renamed

| Old | New | Change |
|-----|-----|--------|
| `useGoldPurchases` | `usePreciousMetals` | Accepts `metal` filter param |
| `useGoldRate` | `useMetalRates` | Returns rates for all metals |
| `useGoldSummary` | `useMetalsSummary` | Accepts `metal` filter param |

### 5.4 Components Renamed

| Old | New |
|-----|-----|
| `GoldHoldingsTable.tsx` | `MetalHoldingsTable.tsx` |
| `GoldPurchaseForm.tsx` | `MetalPurchaseForm.tsx` |
| `GoldRateBar.tsx` | `MetalRateBar.tsx` |

### 5.5 Router

Remove `/gold-portfolio` route. Add `/precious-metals`.
Update navigation menu label: "Gold Portfolio" → "Precious Metals".

---

## 6. Dashboard Fixes

### 6.1 Net Worth Calculation

**Current** (wrong): `existing_corpus + goldValue`
**Fixed**: `existing_corpus + totalSipInvested + allMetalsValue`

`totalSipInvested` = aggregate of all SIP log entries (`actual_invested` column summed). This needs a new backend endpoint or extending the existing SIP service with a `total_invested()` query.

**Net Worth card breakdown**:
- Existing Corpus (manual entry in FIRE Settings)
- SIP Invested (auto-calculated from SIP tracker)
- Precious Metals (live value from metals summary)
- **Total Net Worth** (sum of above)

### 6.2 Monthly Expense Auto-Calculation

**Current**: `monthly_expense` is manually entered in FIRE Settings (currently 0).
**Fixed**: Auto-compute from tracked active recurring expenses:
- Monthly expenses: as-is
- Quarterly expenses: amount / 3
- Yearly expenses: amount / 12
- One-time expenses: excluded

The retirement analysis API endpoint (`/api/projections/retirement`) should compute `monthly_expense` from expenses data instead of relying on the FIRE Settings field.

**Override logic**: The `monthly_expense` field in `fire_inputs` DB remains. If it is `> 0`, it is treated as a manual override and used as-is. If it is `0` (default), the backend auto-computes from tracked expenses. This lets the user set a custom retirement expense target that differs from current spending.

### 6.3 Funded Ratio

No separate fix. Once `monthly_expense` is non-zero (via auto-calculation):
- `required_corpus = annual_expense / swr` becomes non-zero
- `funded_ratio = projected_corpus / required_corpus` computes correctly

### 6.4 Dashboard Labels

- "Gold Holdings" → "Precious Metals" in Net Worth section
- "Gold" → "Precious Metals" in asset allocation pie chart
- Show combined metals value with per-metal mini-breakdown

---

## 7. Engine Changes

### 7.1 Blended Return

```python
# Before
blended = equity_pct * equity_return + debt_pct * debt_return
        + gold_pct * gold_return + cash_pct * cash_return

# After
blended = equity_pct * equity_return + debt_pct * debt_return
        + precious_metals_pct * precious_metals_return + cash_pct * cash_return
```

### 7.2 Fund Allocation

`FUNDS` constant: rename `("Gold ETF", "gold", "gold_pct", 100, "Zerodha")` to `("Precious Metals", "precious_metals", "precious_metals_pct", 100, "Zerodha")`.

### 7.3 Growth Projection

Replace all `gold_pct` references with `precious_metals_pct`. The projection chart label changes from "Debt + Gold + Cash" to "Debt + Metals + Cash".

---

## 8. Streamlit Changes

All Streamlit pages referencing `gold_pct` / `gold_return` must be updated:
- `pages/fire_settings.py` — form labels and column names
- `pages/dashboard.py` — allocation pie chart, net worth section
- `pages/growth_projection.py` — chart legend
- `engine.py` (Streamlit copy) — blended_return, projections

---

## 9. Testing

### Unit Tests
- Rename all `gold_pct`/`gold_return` references in test fixtures
- Add test cases for silver and platinum purchases (CRUD + validation)
- Test metal-specific purity validation (gold+999 should fail, silver+24K should fail)
- Test rate sanity bounds per metal
- Test portfolio summary with mixed metals

### Integration Tests
- Create purchases for all three metals, verify summary aggregation
- Verify rate cache stores per-metal entries
- Verify Dashboard Net Worth includes all metals

---

## 10. Implementation Phases

| Phase | Scope | Dependencies |
|-------|-------|-------------|
| **Phase 1** | Dashboard fixes (Net Worth, monthly expense auto-calc) | None |
| **Phase 2** | DB migration + backend service + API routes | Phase 1 |
| **Phase 3** | FIRE Settings rename (gold_pct → precious_metals_pct) | Phase 2 |
| **Phase 4** | Frontend unified page + hooks + components | Phase 3 |
| **Phase 5** | Streamlit updates | Phase 3 |
| **Phase 6** | Testing + cleanup | All |

---

## 11. Out of Scope

- Palladium or industrial metals (can be added later with same pattern)
- Per-metal allocation percentages in FIRE Settings
- Streamlit precious metals page (React-only for now, like current gold)
- Historical rate charts or trend analysis

Sources:
- [Metals.dev API Documentation](https://metals.dev/docs)
- [Metals.dev Pricing](https://metals.dev/pricing)
