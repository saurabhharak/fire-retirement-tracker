# Feature Spec: Gold Portfolio Tracker

**Author:** Brainstormer Agent  
**Date:** 2026-04-02  
**Status:** Draft — awaiting user review  
**Stack:** FastAPI (Python) + React/TypeScript + Supabase (PostgreSQL)

---

## 1. Purpose

Gold is a core asset class in Indian household wealth and already appears in the FIRE engine
(`gold_pct`, `gold_return` in `fire_inputs`). However, there is currently no way to track
*actual* physical gold purchases, see their live market value, or roll that value into the
net-worth / FIRE corpus calculation.

This feature closes that gap: Saurabh (and his wife) can log every physical gold purchase,
see today's value based on live Indian gold rates, and have the gold portfolio automatically
feed into the existing FIRE projections as part of `existing_corpus`.

---

## 2. User Stories

| # | As a... | I want to... | So that... |
|---|---------|-------------|-----------|
| US-1 | User | Log a gold purchase (date, weight in grams, price paid per gram, purity, owner) | I have a complete record of my physical gold holdings |
| US-2 | User | See the current Indian gold rate (24K and 22K, INR/gram) | I know what my gold is worth today |
| US-3 | User | View my total gold portfolio value at today's rate | I can see total gold wealth at a glance |
| US-4 | User | See profit/loss on each purchase and overall | I know how my gold investments are performing |
| US-5 | User | Filter holdings by owner (you / wife / household) | I can see who owns what, consistent with expense tracking |
| US-6 | User | Edit or soft-delete a gold purchase entry | I can correct mistakes without losing history |
| US-7 | User | Have gold value included in my FIRE corpus calculations | My FIRE projections reflect my complete net worth |
| US-8 | User | See gold rate even when the API is down (cached/stale) | The page is never broken due to an external API outage |

---

## 3. Data Model

### 3.1 New Table: `gold_purchases`

```sql
CREATE TABLE public.gold_purchases (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    purchase_date   date        NOT NULL,
    weight_grams    numeric     NOT NULL CHECK (weight_grams > 0),
    price_per_gram  numeric     NOT NULL CHECK (price_per_gram > 0),
    total_cost      numeric     NOT NULL GENERATED ALWAYS AS (weight_grams * price_per_gram) STORED,
    purity          text        NOT NULL CHECK (purity IN ('24K', '22K', '18K')),
    owner           text        NOT NULL DEFAULT 'household'
                                CHECK (owner IN ('you', 'wife', 'household')),
    notes           text        CHECK (char_length(notes) <= 500),
    is_active       boolean     NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_gold_purchases_user_active ON public.gold_purchases(user_id, is_active);

CREATE TRIGGER trg_gold_purchases_updated_at
    BEFORE UPDATE ON public.gold_purchases
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

**Design notes:**
- `total_cost` is a generated column (`weight_grams * price_per_gram`) for data integrity.
  If PostgreSQL version does not support `GENERATED ALWAYS AS ... STORED`, compute it in
  the application layer and store it as a regular column instead.
- `purity` is text with a CHECK constraint (matches the existing pattern for `frequency` and
  `owner` in `fixed_expenses`).
- `is_active` enables soft-delete, matching the `fixed_expenses` pattern.
- Reuses the existing `set_updated_at()` trigger function from `schema.sql`.

### 3.2 New Table: `gold_rate_cache`

Server-side cache for the latest fetched gold rate so the UI never has a blank state.

```sql
CREATE TABLE public.gold_rate_cache (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_24k        numeric     NOT NULL CHECK (rate_24k > 0),
    rate_22k        numeric     NOT NULL CHECK (rate_22k > 0),
    rate_18k        numeric     NOT NULL CHECK (rate_18k > 0),
    currency        text        NOT NULL DEFAULT 'INR',
    source          text        NOT NULL,
    fetched_at      timestamptz NOT NULL DEFAULT now()
);
```

**Design notes:**
- This is a global table (no `user_id`) — gold rate is the same for all users.
- No RLS needed; the backend reads/writes this table with the service role key.
- Old rows can be pruned periodically (keep last 90 days for history).
- The frontend never calls this table directly — the backend exposes it via an API endpoint.

### 3.3 RLS Policies for `gold_purchases`

```sql
ALTER TABLE public.gold_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.gold_purchases
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.gold_purchases
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.gold_purchases
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.gold_purchases
    FOR DELETE USING (auth.uid() = user_id);
```

### 3.4 Migration File: `migrations/007_gold_portfolio.sql`

Follow the existing idempotent migration pattern (wrapped in `BEGIN; ... COMMIT;`, using
`DO $$ ... END $$` blocks for idempotent `ALTER TABLE` operations, and
`CREATE INDEX IF NOT EXISTS`).

---

## 4. API Endpoints

All endpoints are under `/api` prefix, follow existing FastAPI patterns, and require
Bearer token authentication via `get_current_user` dependency.

### 4.1 Gold Purchases CRUD

| Method | Path | Description | Rate Limit |
|--------|------|-------------|-----------|
| `GET` | `/api/gold-purchases?active=true` | List user's gold purchases | 60/min |
| `POST` | `/api/gold-purchases` | Create a new gold purchase | 30/min |
| `PATCH` | `/api/gold-purchases/{id}` | Update a gold purchase | 30/min |
| `DELETE` | `/api/gold-purchases/{id}` | Soft-delete (set `is_active=false`) | 10/min |

#### POST `/api/gold-purchases` — Request Body

```json
{
  "purchase_date": "2026-03-15",
  "weight_grams": 10.0,
  "price_per_gram": 13500.00,
  "purity": "24K",
  "owner": "you",
  "notes": "Birthday gift purchase"
}
```

#### GET `/api/gold-purchases` — Response

```json
{
  "data": [
    {
      "id": "uuid",
      "purchase_date": "2026-03-15",
      "weight_grams": 10.0,
      "price_per_gram": 13500.00,
      "total_cost": 135000.00,
      "purity": "24K",
      "owner": "you",
      "notes": "Birthday gift purchase",
      "is_active": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### 4.2 Live Gold Rate

| Method | Path | Description | Rate Limit |
|--------|------|-------------|-----------|
| `GET` | `/api/gold-rate` | Get current gold rate (INR/gram, all purities) | 60/min |

#### GET `/api/gold-rate` — Response

```json
{
  "data": {
    "rate_24k": 14897.00,
    "rate_22k": 13655.00,
    "rate_18k": 11173.00,
    "currency": "INR",
    "source": "metals.dev",
    "fetched_at": "2026-04-02T10:30:00Z",
    "is_stale": false
  }
}
```

**`is_stale`**: `true` if `fetched_at` is older than 6 hours. The UI shows a warning badge.

### 4.3 Gold Portfolio Summary (computed endpoint)

| Method | Path | Description | Rate Limit |
|--------|------|-------------|-----------|
| `GET` | `/api/gold-portfolio/summary` | Portfolio value, total P&L, per-owner breakdown | 30/min |

#### GET `/api/gold-portfolio/summary` — Response

```json
{
  "data": {
    "total_weight_grams": 25.5,
    "total_cost": 350000.00,
    "current_value": 379873.50,
    "total_pnl": 29873.50,
    "total_pnl_pct": 8.53,
    "by_owner": [
      { "owner": "you", "weight_grams": 15.0, "cost": 202500.00, "value": 223455.00, "pnl": 20955.00 },
      { "owner": "wife", "weight_grams": 10.5, "cost": 147500.00, "value": 156418.50, "pnl": 8918.50 }
    ],
    "by_purity": [
      { "purity": "24K", "weight_grams": 20.0, "cost": 270000.00, "value": 297940.00 },
      { "purity": "22K", "weight_grams": 5.5, "cost": 80000.00, "value": 81933.50 }
    ],
    "rate_used": {
      "rate_24k": 14897.00,
      "rate_22k": 13655.00,
      "rate_18k": 11173.00,
      "fetched_at": "2026-04-02T10:30:00Z"
    }
  }
}
```

---

## 5. Pydantic Models

Following the conventions in `backend/app/core/models.py`:

```python
class GoldPurchase(BaseModel):
    """New gold purchase entry."""
    purchase_date: date
    weight_grams: float = Field(gt=0)
    price_per_gram: float = Field(gt=0)
    purity: Literal["24K", "22K", "18K"]
    owner: Literal["you", "wife", "household"] = "household"
    notes: str = Field(max_length=500, default="")

class GoldPurchaseUpdate(BaseModel):
    """Partial update for a gold purchase."""
    purchase_date: Optional[date] = None
    weight_grams: Optional[float] = Field(None, gt=0)
    price_per_gram: Optional[float] = Field(None, gt=0)
    purity: Optional[Literal["24K", "22K", "18K"]] = None
    owner: Optional[Literal["you", "wife", "household"]] = None
    notes: Optional[str] = Field(None, max_length=500)
```

---

## 6. Service Layer

New file: `backend/app/services/gold_svc.py`

Functions (following `expenses_svc.py` pattern):

| Function | Description |
|----------|-------------|
| `load_gold_purchases(user_id, access_token, active_only=True)` | Fetch all gold purchases for user |
| `save_gold_purchase(user_id, data, access_token)` | Insert a new gold purchase |
| `update_gold_purchase(id, user_id, data, access_token)` | Partial update |
| `deactivate_gold_purchase(id, user_id, access_token)` | Soft-delete |
| `fetch_gold_rate()` | Call external API, cache result, return rate dict |
| `get_cached_gold_rate()` | Read latest cached rate from `gold_rate_cache` |
| `compute_gold_portfolio_summary(user_id, access_token)` | Aggregate holdings against live rate |

### Gold Rate Fetching Logic

```
1. Check in-memory cache (TTL: 15 minutes)
2. If miss → check gold_rate_cache table (latest row)
3. If row is < 1 hour old → return it, refresh in-memory cache
4. If row is stale or missing → call external API
5. On API success → upsert into gold_rate_cache, update in-memory cache
6. On API failure → return stale cached row with is_stale=true
7. If no cache at all → return error
```

---

## 7. Backend Router

New file: `backend/app/routers/gold.py`

Registered in `main.py` as:
```python
from app.routers import gold
app.include_router(gold.router, prefix="/api")
```

---

## 8. Frontend

### 8.1 New Files

| File | Purpose |
|------|---------|
| `frontend/src/pages/GoldPortfolio.tsx` | Main page component |
| `frontend/src/hooks/useGoldPurchases.ts` | React Query hook for CRUD |
| `frontend/src/hooks/useGoldRate.ts` | React Query hook for live rate |
| `frontend/src/components/gold/GoldSummaryCards.tsx` | Summary metric cards |
| `frontend/src/components/gold/GoldPurchaseForm.tsx` | Quick-add form |
| `frontend/src/components/gold/GoldHoldingsTable.tsx` | Holdings table with P&L |
| `frontend/src/components/gold/GoldOwnerBreakdown.tsx` | Owner-filtered breakdown |

### 8.2 Navigation

Add to `frontend/src/lib/constants.ts` `NAV_ITEMS` array:

```typescript
{ path: "/gold-portfolio", label: "Gold Portfolio", icon: "Gem" }
```

Position it after "Income & Expenses" since gold is an asset tracker (similar to SIP Tracker).

Import `Gem` from `lucide-react` in `Sidebar.tsx` and add to `iconMap`.

Add lazy route in `App.tsx`:
```typescript
const GoldPortfolio = lazy(() => import("./pages/GoldPortfolio"));
// + <Route path="/gold-portfolio" element={<ProtectedRoute><GoldPortfolio /></ProtectedRoute>} />
```

### 8.3 Page Layout

The Gold Portfolio page follows the same visual structure as `IncomeExpenses.tsx` and
`SipTracker.tsx`:

```
+------------------------------------------------------------+
| PageHeader: "Gold Portfolio"                                |
|   subtitle: "Track your physical gold holdings"             |
+------------------------------------------------------------+
| Summary Cards (grid: 4 cols on desktop)                     |
| [Total Weight]  [Total Invested]  [Current Value]  [P&L %] |
|  25.5 grams      Rs 3,50,000       Rs 3,79,874     +8.5%   |
+------------------------------------------------------------+
| Live Gold Rate Bar                                          |
| 24K: Rs 14,897/g  |  22K: Rs 13,655/g  |  18K: Rs 11,173  |
| Source: metals.dev  |  Updated: 10:30 AM  | [Stale badge?]  |
+------------------------------------------------------------+
| Owner Filter: [All] [You] [Wife] [Household]                |
+------------------------------------------------------------+
| Quick-Add Form (inline, matches ExpenseQuickAdd)            |
| [Date] [Weight g] [Price/g] [Purity v] [Owner v] [+ Add]   |
+------------------------------------------------------------+
| Holdings Table                                              |
| Date | Weight | Purity | Price Paid | Cost | Value | P&L   |
| (each row shows owner badge, color-coded)                   |
| ...                                                         |
| [Running Totals Row — gold-colored, like SipTracker]        |
+------------------------------------------------------------+
```

### 8.4 Design Tokens (matching existing theme)

| Element | Color | Usage |
|---------|-------|-------|
| Gold metric highlights | `#D4A843` | Total value, weight, gold rate bar |
| Positive P&L | `#00895E` | Gain amounts and percentages |
| Negative P&L | `#E5A100` (amber/warning) | Loss amounts — NO red per design rules |
| Owner badge: You | `#D4A843` | Consistent with `IncomeExpenses.tsx` |
| Owner badge: Wife | `#E07A5F` (coral) | Consistent with `IncomeExpenses.tsx` |
| Owner badge: Household | `#6B7280` (gray) | Consistent with `IncomeExpenses.tsx` |
| Purity badge: 24K | `#D4A843` gold bg | Premium purity |
| Purity badge: 22K | `#D4A843/60` muted gold | Standard purity |
| Purity badge: 18K | `#6B7280` gray | Lower purity |
| Stale rate warning | `#E5A100` amber | When gold rate is > 6 hours old |
| Background/surface | `#0D1B2A` / `#132E3D` | Matches existing dark theme |

### 8.5 React Query Hook Pattern

`useGoldPurchases.ts` follows the exact same pattern as `useExpenses.ts`:

```typescript
// Query key: ["gold-purchases", { active }]
// Mutations: save, update, deactivate — each invalidates query key
// Returns: { entries, isLoading, save, update, deactivate }
```

`useGoldRate.ts`:

```typescript
// Query key: ["gold-rate"]
// Stale time: 15 minutes (refetch interval)
// refetchInterval: 15 * 60 * 1000
// Returns: { rate, isLoading, isStale }
```

---

## 9. Gold Price API Selection

### 9.1 Evaluation Matrix

| Criteria | GoldAPI.io | MetalpriceAPI | Metals.dev | IndiaGoldRatesAPI |
|----------|-----------|---------------|-----------|-------------------|
| **Free tier** | ~100 req/day (~3,000/mo) | 100 req/month | 100 req/month | Unknown (no public pricing) |
| **Paid entry** | $19.99/mo (5,000/day) | $3.99/mo (1,000/mo) | $1.79/mo (2,000/mo) | Unknown |
| **INR support** | Yes (currency param) | Yes (150+ currencies) | Yes (170+ currencies, confirmed) | Yes (native INR) |
| **Indian market data** | International spot only | International spot only | MCX + IBJA rates | IBJA rates (native) |
| **Purity (22K/18K)** | No (24K spot only) | No (24K spot only) | No (24K spot only) | Yes (IBJA publishes all) |
| **Data freshness** | Real-time | 60s (paid) / daily (free) | 60s delay | Daily |
| **Reliability** | Established, good uptime | Established, good uptime | Established, good uptime | Small provider, unknown |
| **Response format** | JSON | JSON | JSON | JSON |

### 9.2 Recommendation: Metals.dev (Primary) + Purity Conversion (Application Layer)

**Primary API: Metals.dev**

Reasoning:
1. **MCX + IBJA data sources** — closest to actual Indian market rates, not just international spot converted to INR.
2. **Confirmed INR support** — tested in their documentation (`currency=INR`).
3. **Affordable scaling** — $1.79/mo for 2,000 requests covers daily fetches for years; free tier (100/mo) is enough for development and low-usage periods.
4. **Good documentation** — clean REST endpoints, standard JSON responses.
5. **Spot endpoint** includes bid/ask/high/low, useful for future features.

**Purity conversion (application layer):**

No API provides 22K and 18K rates directly. We derive them from the 24K rate using
standard purity ratios:

```
24K = 99.9% pure gold → rate from API (base rate)
22K = 91.6% pure gold → rate_24k * (22/24) = rate_24k * 0.9167
18K = 75.0% pure gold → rate_24k * (18/24) = rate_24k * 0.75
```

These ratios are industry standard. The actual retail rates for 22K/18K gold in India
track very closely to these calculated values (within 1-2% due to making charges, which
are not part of the metal rate).

**Fallback strategy:**

```
Primary:  Metals.dev /v1/metal/spot?metal=gold&currency=INR
Fallback: GoldAPI.io /XAU/INR  (generous free tier, different provider)
Last resort: Return cached rate with is_stale=true
```

### 9.3 API Key Management

- Store as `GOLD_API_KEY` (Metals.dev) and `GOLD_API_KEY_FALLBACK` (GoldAPI.io) in `.env`.
- Add to `Settings` in `backend/app/config.py` as optional fields with empty-string defaults.
- Never expose API keys to the frontend — all fetches happen server-side.

### 9.4 Caching Strategy

| Layer | TTL | Purpose |
|-------|-----|---------|
| In-memory (Python dict + timestamp) | 15 minutes | Avoid redundant API calls across users |
| Database (`gold_rate_cache` table) | Indefinite (latest row used) | Survive server restarts, provide stale fallback |
| Frontend (React Query `staleTime`) | 15 minutes | Avoid redundant HTTP calls from browser |

**Fetch frequency budget (free tier: 100 req/month):**
- 1 fetch every 15 minutes during active hours (say 12 hours/day) = 48/day = ~1,440/month
- This exceeds free tier. For production use, the $1.79/mo Copper plan (2,000 req/mo) is recommended.
- During development, use longer TTL (1 hour) to stay within free tier.

---

## 10. Net Worth / FIRE Integration

### 10.1 How Gold Value Feeds Into FIRE Calculations

The existing FIRE engine uses `existing_corpus` as the starting portfolio value. Gold
portfolio value should be **additive** to this corpus.

**Approach: New computed endpoint, not mutation of existing fields.**

Add `GET /api/gold-portfolio/fire-value` that returns:

```json
{
  "data": {
    "gold_current_value": 379873.50,
    "last_rate_at": "2026-04-02T10:30:00Z"
  }
}
```

The Dashboard can then display:

```
Existing Corpus (from settings):  Rs 20,00,000
+ Gold Portfolio (live):          Rs  3,79,874
= Total Net Worth:                Rs 23,79,874
```

**Important decision:** The gold value should be *displayed alongside* the existing corpus
on the Dashboard, NOT silently added to `existing_corpus` in the database. This keeps the
FIRE settings pure (user-entered values only) and avoids confusion when the gold rate
fluctuates.

### 10.2 Dashboard Changes

Add a new metric card or info row on the Dashboard showing:

```
| Existing Corpus | Gold Holdings | Total Net Worth |
|  Rs 20,00,000   |  Rs 3,79,874  |  Rs 23,79,874   |
```

This is a display-only enhancement — the FIRE engine projections continue to use the
user-entered `existing_corpus` value. A future enhancement could optionally let users
toggle "include gold in projections."

---

## 11. Edge Cases

| # | Edge Case | Handling |
|---|-----------|---------|
| E-1 | Gold API is down | Return cached rate with `is_stale: true`. UI shows amber "Rate may be outdated" badge. |
| E-2 | Gold API returns unexpected currency | Validate response; reject if currency is not INR. Log error and fall back to cache. |
| E-3 | No cached rate exists AND API is down | Return `null` rate. UI shows "Gold rate unavailable" message. P&L columns show "--". |
| E-4 | User enters gold weight as tola instead of grams | **Not supported in v1.** Form accepts grams only. Add a tooltip: "1 tola = 11.664 grams". Future: add unit selector. |
| E-5 | Price per gram includes making charges | Notes field can record this. The `price_per_gram` is whatever the user actually paid. P&L will reflect true cost basis. |
| E-6 | User edits a deactivated (soft-deleted) purchase | Backend should reject PATCH on `is_active=false` rows. Return 404. |
| E-7 | Floating-point precision on weight (e.g., 0.5 grams) | Use `numeric` type in PostgreSQL (arbitrary precision). Frontend input allows up to 3 decimal places. |
| E-8 | Rate cache has entries for multiple currencies | Filter by `currency = 'INR'` and take the latest `fetched_at`. |
| E-9 | User has 0 gold purchases | Empty state: "No gold purchases yet. Use the form above to start tracking." (matches SipTracker pattern). |
| E-10 | Very old gold purchases (pre-2020) | Allow `purchase_date` back to 2000-01-01 (unlike expenses which start at 2020). Gold is often held for decades. |
| E-11 | Gold rate changes significantly between page load and form submit | P&L is always computed against the *latest* rate at display time, not at form submission time. This is expected behavior. |

---

## 12. Open Questions (Need User Input)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| Q-1 | Should gold value be **automatically added** to FIRE projections, or **display-only** alongside corpus? | (a) Auto-add to engine calculations (b) Display-only on Dashboard | **(b) Display-only** in v1 to keep FIRE settings clean. Add opt-in toggle later. |
| Q-2 | Do you want a **tola** input option alongside grams? | (a) Grams only (b) Grams + Tola toggle | **(a) Grams only** in v1, with a helper tooltip. Simpler form. |
| Q-3 | Should the gold rate fetch run on a **background cron** or only **on-demand** when users visit the page? | (a) Background cron every 15 min (b) On-demand only | **(b) On-demand** in v1, simpler to implement. Cron can be added later if there are many active users. |
| Q-4 | Where should Gold Portfolio appear in the sidebar navigation? | (a) After Income & Expenses (b) After SIP Tracker (c) Own "Assets" section | **(a) After Income & Expenses** — it's an asset tracker, logically follows income/expenses. |
| Q-5 | Do you want to track **gold type** (coin, bar, jewelry, digital gold)? | (a) No, just weight+purity (b) Yes, add a `type` field | **(a) No** in v1. Can add later if needed. Notes field can capture this for now. |
| Q-6 | Should the paid Metals.dev plan ($1.79/mo) be used from the start, or develop against the free tier? | (a) Free tier + longer cache TTL (b) Paid from day one | **(a) Free tier** during development, upgrade when deploying to production. |
| Q-7 | Do you track gold sold/disposed? | (a) No, just purchases (b) Yes, add sell transactions | **(a) Purchases only** in v1. Selling physical gold is rare. Can be added as a future feature. |

---

## 13. Implementation Order (Suggested Phases)

### Phase 1: Core Backend (1-2 days)
1. Migration `007_gold_portfolio.sql` — create tables + RLS
2. Pydantic models in `models.py`
3. Service layer `gold_svc.py` — CRUD for purchases
4. Router `gold.py` — purchase endpoints
5. Register router in `main.py`

### Phase 2: Gold Rate Integration (1 day)
1. Add API key settings to `config.py`
2. Implement `fetch_gold_rate()` with Metals.dev integration
3. Implement caching logic (in-memory + DB)
4. Implement purity conversion (22K, 18K from 24K rate)
5. Add `/api/gold-rate` endpoint
6. Add `/api/gold-portfolio/summary` computed endpoint

### Phase 3: Frontend — Page + CRUD (1-2 days)
1. `useGoldPurchases.ts` hook
2. `useGoldRate.ts` hook
3. `GoldPortfolio.tsx` page with summary cards, form, table
4. Owner filter + purity badges
5. Navigation entry in sidebar + App.tsx route

### Phase 4: Dashboard Integration (0.5 day)
1. Add gold portfolio value to Dashboard
2. Display alongside existing corpus

### Phase 5: Polish + Edge Cases (0.5 day)
1. Stale rate warnings
2. Empty states
3. Error handling for API failures
4. Audit logging for gold purchase CRUD

---

## 14. Out of Scope (Future Enhancements)

- Digital gold (Sovereign Gold Bonds, Gold ETFs) — different data model
- Gold sell/disposal tracking
- Historical gold rate charts
- Tola/sovereign unit input
- Gold type categorization (jewelry, coins, bars)
- Automatic FIRE engine integration (gold auto-added to corpus)
- Multi-currency support (only INR in v1)
- Gold alerts (price target notifications)

---

## Appendix A: Metals.dev API Integration Details

### Spot Price Request

```
GET https://api.metals.dev/v1/metal/spot?api_key={KEY}&metal=gold&currency=INR
```

### Expected Response

```json
{
  "status": "success",
  "currency": "INR",
  "unit": "toz",
  "metal": "gold",
  "price": 463000.00,
  "bid": 462800.00,
  "ask": 463200.00,
  "high": 465000.00,
  "low": 460000.00,
  "change": 2500.00,
  "change_percent": 0.54,
  "timestamp": "2026-04-02T10:30:00Z"
}
```

### Conversion to INR per gram

```python
TROY_OZ_TO_GRAMS = 31.1035

def toz_to_gram(price_per_toz: float) -> float:
    """Convert price per troy ounce to price per gram."""
    return price_per_toz / TROY_OZ_TO_GRAMS

def compute_purity_rates(rate_24k_per_gram: float) -> dict:
    """Derive 22K and 18K rates from 24K rate."""
    return {
        "rate_24k": round(rate_24k_per_gram, 2),
        "rate_22k": round(rate_24k_per_gram * 22 / 24, 2),
        "rate_18k": round(rate_24k_per_gram * 18 / 24, 2),
    }
```

### Fallback: GoldAPI.io

```
GET https://www.goldapi.io/api/XAU/INR
Headers: x-access-token: {FALLBACK_KEY}
```

Response includes `price_gram_24k`, `price_gram_22k`, `price_gram_18k` directly (no
conversion needed).
