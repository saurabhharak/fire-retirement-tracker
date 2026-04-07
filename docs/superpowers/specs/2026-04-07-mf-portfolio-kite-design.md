# MF Portfolio (Kite Connect Integration) — Design Spec

**Date:** 2026-04-07
**Status:** Draft
**Scope:** Live mutual fund portfolio tracking via Zerodha Kite Connect API — holdings, P&L, and active SIPs on a new "MF Portfolio" page. Read-only, no trading.

## Context

Saurabh invests in mutual funds through Zerodha Coin. The FIRE Tracker needs a live view of his MF portfolio — what he holds, what it's worth, P&L per fund, and which SIPs are running. The Kite Connect API (free personal tier) provides `mf_holdings()`, `mf_sips()`, and `mf_orders()` endpoints that return exactly this data. The existing SIP Tracker page (manual monthly logging) stays as-is.

## Requirements

1. **Kite Connect OAuth** — "Connect Zerodha" button initiates browser-based login, exchanges token, stores session. Token expires daily — user re-authenticates when needed.
2. **Live Portfolio View** — Fetch MF holdings with current NAV and P&L. Show summary cards + fund-level table.
3. **Active SIPs** — Fetch SIP details (fund, amount, frequency, next date) and show alongside holdings.
4. **Offline Fallback** — Cache portfolio snapshot in Supabase. When token expires, show last cached data with a "stale" indicator.
5. **New page** — "MF Portfolio" in sidebar. Existing SIP Tracker unchanged.

## Authentication Flow

### OAuth with State Parameter (CSRF + User Identification)

```
Frontend                     Backend                      Zerodha
   |                           |                            |
   |-- GET /kite/login-url --->|                            |
   |   (with Supabase JWT)     |-- generate state JWT ------|
   |                           |   (user_id + 10min exp)    |
   |<-- {url: "https://kite..  |                            |
   |     &state=signed_jwt"} --|                            |
   |                           |                            |
   |-- browser redirect ------>|                            |
   |                           |                     Zerodha login UI
   |                           |                            |
   |                           |<-- GET /kite/callback -----|
   |                           |    ?request_token=X&state=Y|
   |                           |                            |
   |                           |-- validate state JWT ------|
   |                           |-- exchange token --------->|
   |                           |<-- access_token -----------|
   |                           |-- store in kite_sessions --|
   |                           |                            |
   |<-- 302 redirect to -------|                            |
   |    FRONTEND_URL/mf-portfolio?connected=true            |
```

**State JWT contents:** `{ user_id: "uuid", exp: now + 10min }` signed with `kite_api_secret` (HMAC-SHA256). On callback, validate signature + expiry + extract user_id. This prevents CSRF and identifies the user without requiring a Supabase JWT on the callback (since it's a browser redirect from Zerodha).

### Token Lifecycle

- Access token valid for one trading day (resets ~6 AM IST)
- `expires_at` set to next day 6:00 AM IST on storage
- Frontend checks `/kite/status` on page load — if expired, shows "Reconnect" prompt
- On Kite API 403/401, service returns cached snapshot with `is_stale: true`

## Database Schema

### Table: `kite_sessions`

```sql
CREATE TABLE public.kite_sessions (
    user_id      uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    access_token text        NOT NULL,
    connected_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_kite_sessions_updated_at
    BEFORE UPDATE ON public.kite_sessions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: standard 4 policies (`select_own`, `insert_own`, `update_own`, `delete_own`) with `auth.uid() = user_id`.

**Design decisions:**
- `user_id` as PK = one Kite session per Supabase user (wife needs her own login)
- `access_token` stored as plain text — acceptable for a 2-user personal app with daily-expiring tokens + RLS isolation. Documented tradeoff.
- No `api_key` column — it's app-level, stored in env vars

### Table: `mf_portfolio_snapshots`

```sql
CREATE TABLE public.mf_portfolio_snapshots (
    user_id       uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_data jsonb       NOT NULL,
    synced_at     timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_mf_portfolio_snapshots_updated_at
    BEFORE UPDATE ON public.mf_portfolio_snapshots
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: standard 4 policies with `auth.uid() = user_id`.

**`snapshot_data` JSONB schema:**
```json
{
  "holdings": [
    {
      "fund": "Axis Bluechip Fund",
      "tradingsymbol": "INF846K01DP8",
      "folio": "1234567890",
      "quantity": 100.123,
      "average_price": 35.67,
      "last_price": 40.12,
      "last_price_date": "2026-04-04",
      "pnl": 445.50
    }
  ],
  "sips": [
    {
      "sip_id": "abc123",
      "fund": "Axis Bluechip Fund",
      "tradingsymbol": "INF846K01DP8",
      "status": "ACTIVE",
      "frequency": "monthly",
      "instalment_amount": 5000,
      "completed_instalments": 24,
      "instalment_day": 5,
      "next_instalment": "2026-05-05"
    }
  ],
  "computed": {
    "total_invested": 1250000,
    "current_value": 1450000,
    "total_pnl": 200000,
    "pnl_pct": 16.0,
    "total_monthly_sip": 25000,
    "active_sip_count": 5
  }
}
```

## API Design

### Configuration (in `config.py`)

```python
kite_api_key: str = ""
kite_api_secret: str = ""
kite_redirect_url: str = "http://localhost:8002/api/kite/callback"
frontend_url: str = "http://localhost:5175"
```

### Endpoints

| Method | Path | Rate Limit | Auth | Purpose |
|---|---|---|---|---|
| GET | `/api/kite/login-url` | 10/min | Supabase JWT | Generate Kite login URL with signed state |
| GET | `/api/kite/callback` | 10/min | State JWT (no Supabase) | OAuth callback — exchange token, redirect to frontend |
| GET | `/api/kite/status` | 60/min | Supabase JWT | Connection status + last sync time |
| DELETE | `/api/kite/session` | 10/min | Supabase JWT | Disconnect Kite (delete session) |
| GET | `/api/kite/portfolio` | 30/min | Supabase JWT | Merged holdings + SIPs + computed fields |

**Response envelope:** Standard `{"data": ...}` / `{"data": ..., "message": ...}` pattern.

**Special: `/api/kite/callback`** — This is the only endpoint that does NOT use the standard `CurrentUser` dependency, because it's a browser redirect from Zerodha (no Supabase JWT). It validates the `state` JWT instead and extracts user_id from it.

### Error Handling

- **Token expired (Kite 403):** Return last snapshot with `is_stale: true` flag. Frontend shows "Session expired" banner.
- **No session exists:** Return `{"data": null, "connected": false}`.
- **Kite API error (500, rate limit):** Raise `DatabaseError("Kite API temporarily unavailable")`, fall back to snapshot.
- **Invalid state on callback:** Return 400 "Invalid or expired authorization".

### Pydantic Models (in `models.py`)

```python
class KiteHolding(BaseModel):
    fund: str
    tradingsymbol: str
    folio: str
    quantity: float
    average_price: float
    last_price: float
    last_price_date: str
    pnl: float
    invested: float       # computed: average_price * quantity
    current_value: float  # computed: last_price * quantity
    pnl_pct: float        # computed: (pnl / invested) * 100
    sip_amount: Optional[float] = None      # from merged SIP data
    sip_frequency: Optional[str] = None
    sip_next_date: Optional[str] = None

class KiteSIP(BaseModel):
    sip_id: str
    fund: str
    tradingsymbol: str
    status: str
    frequency: str
    instalment_amount: float
    completed_instalments: int
    instalment_day: int
    next_instalment: Optional[str] = None

class KitePortfolioResponse(BaseModel):
    holdings: list[KiteHolding]
    sips: list[KiteSIP]
    total_invested: float
    current_value: float
    total_pnl: float
    pnl_pct: float
    total_monthly_sip: float
    active_sip_count: int
    synced_at: str
    is_stale: bool = False

class KiteStatusResponse(BaseModel):
    connected: bool
    connected_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: bool = False
    last_sync: Optional[str] = None
```

## Service Layer: `kite_svc.py`

| Function | Purpose |
|---|---|
| `generate_login_url(user_id)` | Create Kite login URL with signed state JWT |
| `exchange_token(request_token, state)` | Validate state, exchange for access_token, store session |
| `get_session(user_id, access_token)` | Get current Kite session (or None) |
| `delete_session(user_id, access_token)` | Remove Kite session |
| `fetch_portfolio(user_id, access_token)` | Call Kite API (holdings + SIPs), merge, compute, save snapshot, return |
| `get_cached_portfolio(user_id, access_token)` | Return last snapshot (for offline/expired) |

**Kite client initialization:**
```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=settings.kite_api_key)
kite.set_access_token(session.access_token)
holdings = kite.mf_holdings()
sips = kite.mf_sips()
```

**Portfolio merge logic:** Match holdings to SIPs by `tradingsymbol` (ISIN). For each holding, if a matching active SIP exists, attach `sip_amount`, `sip_frequency`, `sip_next_date`.

## Frontend Design

### Navigation

New sidebar entry: **"MF Portfolio"** with `LineChart` icon, route `/mf-portfolio`, positioned after "Projects".

### Page Layout: `MFPortfolio.tsx`

```
+----------------------------------------------------------+
| MF Portfolio                                              |
| [Connected to Zerodha - Synced 5 min ago] [Refresh] [Disconnect] |
|  -- OR --                                                 |
| [Connect Zerodha] (if not connected)                      |
+----------------------------------------------------------+
| Summary Cards (6 cards)                                   |
| [Total Invested] [Current Value] [Total P&L (+%)]         |
| [Total Monthly SIP] [Active SIPs] [NAV Date]             |
+----------------------------------------------------------+
| Holdings Table (main content)                             |
| Fund Name | Invested | Current | P&L | P&L% | SIP/mo    |
| Axis Blue | 3,56,700 | 4,01,200| +44K | +12% | 5,000/mo  |
| PPFAS Fle | 7,50,000 | 8,23,000| +73K | +10% | 3,000/mo  |
| ... sorted by current value desc                          |
+----------------------------------------------------------+
| Active SIPs (collapsible)                                 |
| Fund | Amount | Frequency | Next Date | Done/Total       |
+----------------------------------------------------------+
```

### Components

| File | Purpose |
|---|---|
| `pages/MFPortfolio.tsx` | Page container, orchestrates auth + data display |
| `components/portfolio/KiteConnectionBanner.tsx` | Connect/disconnect/status banner |
| `components/portfolio/PortfolioSummaryCards.tsx` | 6 metric cards |
| `components/portfolio/HoldingsTable.tsx` | Fund holdings with merged SIP info |
| `components/portfolio/ActiveSIPs.tsx` | Collapsible SIP details section |
| `hooks/useKitePortfolio.ts` | React Query hooks for status + portfolio |

### State Management

```typescript
// Connection check on page load
const { data: status } = useKiteStatus();

// Portfolio data (only fetches when connected)
const { data: portfolio, isLoading } = useKitePortfolio({
  enabled: status?.connected && !status?.is_expired,
});
```

## Files to Create/Modify

### New files:
- `migrations/011_kite_sessions.sql` — Both tables, RLS, triggers
- `backend/app/services/kite_svc.py` — Kite Connect service layer
- `backend/app/routers/kite.py` — Kite auth + portfolio endpoints
- `frontend/src/pages/MFPortfolio.tsx` — Main page
- `frontend/src/components/portfolio/KiteConnectionBanner.tsx`
- `frontend/src/components/portfolio/PortfolioSummaryCards.tsx`
- `frontend/src/components/portfolio/HoldingsTable.tsx`
- `frontend/src/components/portfolio/ActiveSIPs.tsx`
- `frontend/src/hooks/useKitePortfolio.ts`

### Modified files:
- `backend/app/config.py` — Add 4 new settings (kite_api_key, kite_api_secret, kite_redirect_url, frontend_url)
- `backend/app/core/models.py` — Add Kite Pydantic models
- `backend/app/main.py` — Register kite router
- `frontend/src/lib/constants.ts` — Add "MF Portfolio" to NAV_ITEMS
- `frontend/src/layouts/Sidebar.tsx` — Add LineChart icon
- `frontend/src/App.tsx` — Add /mf-portfolio route
- `schema.sql` — Add both tables for reference
- `backend/requirements.txt` or `pyproject.toml` — Add `kiteconnect` dependency

## Dependencies

- `kiteconnect` Python package (`pip install kiteconnect`)
- PyJWT (already installed) — for signing state tokens

## Security Notes

- API secret stored in `.env` / Render env vars only — never in code or DB
- Access token plain text in DB — acceptable (daily expiry, RLS, 2 users). Documented tradeoff.
- State JWT prevents CSRF on OAuth callback
- Callback endpoint does NOT use standard auth dependency — validates state JWT instead
- All other endpoints use standard Supabase JWT auth
- Audit logging on connect, disconnect, and portfolio sync
- No trading/order placement — read-only access
