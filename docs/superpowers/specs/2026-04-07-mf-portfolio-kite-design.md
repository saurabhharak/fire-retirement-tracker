# MF Portfolio (Kite Connect Integration) — Design Spec

**Date:** 2026-04-07
**Status:** Approved
**Scope:** Live mutual fund portfolio tracking via Zerodha Kite Connect API — holdings, P&L, and active SIPs on a new "MF Portfolio" page. Read-only, no trading.

## Context

Saurabh invests in mutual funds through Zerodha Coin. The FIRE Tracker needs a live view of his MF portfolio — what he holds, what it's worth, P&L per fund, and which SIPs are running. The Kite Connect API (free personal tier) provides `mf_holdings()` and `mf_sips()` endpoints that return exactly this data. (`mf_orders()` is available but out of scope for v1.) The existing SIP Tracker page (manual monthly logging) stays as-is.

## Requirements

1. **Kite Connect OAuth** — "Connect Zerodha" button initiates browser-based login, exchanges token, stores session. Token expires daily — user re-authenticates when needed.
2. **Live Portfolio View** — Fetch MF holdings with current NAV and P&L. Show summary cards + fund-level table.
3. **Active SIPs** — Fetch SIP details (fund, amount, frequency, next date) and show alongside holdings.
4. **Offline Fallback** — Cache portfolio snapshot in Supabase. When token expires, show last cached data with a "stale" indicator.
5. **New page** — "MF Portfolio" in sidebar (adjacent to SIP Tracker for information grouping). Existing SIP Tracker unchanged.

## Authentication Flow

### OAuth with State Parameter (CSRF + User Identification + Replay Protection)

```
Frontend                     Backend                      Zerodha
   |                           |                            |
   |-- GET /kite/login-url --->|                            |
   |   (with Supabase JWT)     |-- generate state JWT ------|
   |                           |   (user_id + nonce + exp)  |
   |                           |-- store nonce in DB -------|
   |<-- {url: "https://kite..  |                            |
   |     &state=signed_jwt"} --|                            |
   |                           |                            |
   |-- browser redirect ------>|                     Zerodha login UI
   |                           |                            |
   |                           |<-- GET /kite/callback -----|
   |                           |    ?request_token=X&state=Y|
   |                           |                            |
   |                           |-- validate state JWT ------|
   |                           |-- verify nonce (one-time) -|
   |                           |-- delete nonce from DB ----|
   |                           |-- exchange token --------->|
   |                           |<-- access_token -----------|
   |                           |-- store in kite_sessions --|
   |                           |   (via service-role client)|
   |                           |                            |
   |<-- 302 redirect to -------|                            |
   |    FRONTEND_URL/mf-portfolio?connected=true            |
```

**State JWT contents:** `{ user_id: "uuid", nonce: "random_uuid", iss: "fire-tracker", aud: "kite-oauth-state", exp: now + 10min }` signed with `KITE_STATE_SECRET` (dedicated HMAC-SHA256 key, separate from `kite_api_secret`).

**Replay protection:** The `nonce` is stored in `kite_oauth_nonces` table on generation and deleted on first use. If the nonce doesn't exist or has been used, the callback rejects the request.

**User identification:** The `user_id` is extracted from the validated state JWT. No Supabase JWT is available on the callback (it's a browser redirect from Zerodha).

**Supabase write on callback:** Since no Supabase JWT exists during the callback, the `exchange_token` function uses a **service-role client** (`get_service_client()`) to upsert into `kite_sessions`. This bypasses RLS intentionally — the state JWT validation ensures we're writing for the correct user.

### Token Lifecycle

- Access token valid for one trading day (resets ~6 AM IST)
- `expires_at` set to next day 6:00 AM IST on storage
- Frontend checks `/kite/status` on page load — if expired, shows "Reconnect" prompt
- On Kite API 403/401, service returns cached snapshot with `is_stale: true`
- Expired sessions cleaned up: service deletes expired rows when detected

## Database Schema

### Table: `kite_sessions`

```sql
CREATE TABLE IF NOT EXISTS public.kite_sessions (
    user_id      uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    access_token text        NOT NULL CHECK (char_length(access_token) > 0),
    connected_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_kite_sessions_updated_at
    BEFORE UPDATE ON public.kite_sessions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: standard 4 policies (`select_own`, `insert_own`, `update_own`, `delete_own`) with `auth.uid() = user_id`.

**Note:** The OAuth callback uses a service-role client to bypass RLS for the upsert (since no Supabase JWT exists at callback time). All other operations (status, delete, portfolio) go through the standard RLS-scoped user client.

**Design decisions:**
- `user_id` as PK = one Kite session per Supabase user (wife needs her own Supabase login + Zerodha account)
- `access_token` stored as plain text — acceptable for a 2-user personal app with daily-expiring tokens + RLS isolation. Documented tradeoff. If needed later, encrypt with Fernet using `KITE_TOKEN_ENCRYPTION_KEY` env var.
- No `api_key` column — it's app-level, stored in env vars

### Table: `mf_portfolio_snapshots`

```sql
CREATE TABLE IF NOT EXISTS public.mf_portfolio_snapshots (
    user_id       uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    snapshot_data jsonb       NOT NULL,
    synced_at     timestamptz NOT NULL DEFAULT now(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_mf_portfolio_snapshots_updated_at
    BEFORE UPDATE ON public.mf_portfolio_snapshots
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

RLS: standard 4 policies with `auth.uid() = user_id`.

### Table: `kite_oauth_nonces` (replay protection)

```sql
CREATE TABLE IF NOT EXISTS public.kite_oauth_nonces (
    nonce      uuid        PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kite_oauth_nonces_expires
    ON public.kite_oauth_nonces(expires_at);
```

No RLS needed — only accessed via service-role client in the callback flow. Expired nonces cleaned up periodically.

**`snapshot_data` JSONB schema:**
```json
{
  "holdings": [
    {
      "fund": "Axis Bluechip Fund",
      "tradingsymbol": "INF846K01DP8",
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

Note: `folio` field intentionally excluded from holdings — semi-sensitive identifier with no UI value.

## API Design

### Configuration (in `config.py`)

```python
kite_api_key: str = ""
kite_api_secret: str = ""
kite_state_secret: str = ""          # Dedicated key for signing OAuth state JWTs
kite_redirect_url: str = "http://localhost:8002/api/kite/callback"
frontend_url: str = "http://localhost:5175"
```

`frontend_url` must match one of the `cors_origins` entries. In production, set to the Vercel URL.

### Supabase Client Addition

Add `get_service_client()` to `supabase_client.py`:
```python
@lru_cache
def get_service_client() -> Client:
    """Service-role client for operations that bypass RLS (e.g., OAuth callback)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
```

Requires new setting: `supabase_service_key: str = ""` in `config.py`.

### Endpoints

| Method | Path | Rate Limit | Auth | Purpose |
|---|---|---|---|---|
| GET | `/api/kite/login-url` | 5/min | Supabase JWT | Generate Kite login URL with signed state |
| GET | `/api/kite/callback` | 3/min | State JWT (no Supabase) | OAuth callback — exchange token, redirect to frontend |
| GET | `/api/kite/status` | 60/min | Supabase JWT | Connection status + last sync time |
| DELETE | `/api/kite/session` | 10/min | Supabase JWT | Disconnect Kite (delete session) |
| GET | `/api/kite/portfolio` | 30/min | Supabase JWT | Merged holdings + SIPs + computed fields |

**Response envelope:** Standard `{"data": ...}` / `{"data": ..., "message": ...}` pattern.

**Special: `/api/kite/callback`** — This is the only endpoint that does NOT use the standard `CurrentUser` dependency, because it's a browser redirect from Zerodha (no Supabase JWT). It validates the `state` JWT instead and extracts user_id from it. The redirect target is always hardcoded to `settings.frontend_url + "/mf-portfolio?connected=true"` — never accepts a redirect URL from the request.

### Error Handling

New exception class (in `exceptions.py`):
```python
class ExternalServiceError(FireTrackerError):
    """Raised when an external API (e.g., Kite Connect) fails."""
    pass
```

Registered handler returns HTTP 502:
```python
@app.exception_handler(ExternalServiceError)
async def external_service_handler(request, exc):
    return JSONResponse(status_code=502, content={"detail": exc.message})
```

Error flows:
- **Token expired (Kite 403):** Return last snapshot with `is_stale: true` flag. Frontend shows "Session expired" banner.
- **No session exists:** Return `{"data": null, "connected": false}`.
- **Kite API error (500, rate limit):** Raise `ExternalServiceError("Kite API temporarily unavailable")`, fall back to snapshot.
- **Invalid/replayed state on callback:** Return 400 "Invalid or expired authorization".

**Log sanitization:** Never log `request_token`, `access_token`, or `state` values. Log only `user_id`, error type, and generic messages.

### Pydantic Models (in `models.py`)

```python
class KiteHolding(BaseModel):
    """Single MF holding from Kite API with computed fields."""
    fund: str = Field(max_length=500)
    tradingsymbol: str = Field(max_length=50)
    quantity: float = Field(ge=0)
    average_price: float = Field(ge=0)
    last_price: float = Field(ge=0)
    last_price_date: str
    pnl: float
    invested: float = Field(ge=0)       # computed: average_price * quantity
    current_value: float = Field(ge=0)  # computed: last_price * quantity
    pnl_pct: float                      # computed: (pnl / invested) * 100
    sip_amount: Optional[float] = None      # from merged SIP data
    sip_frequency: Optional[str] = None
    sip_next_date: Optional[str] = None

class KiteSIP(BaseModel):
    """Active SIP from Kite API."""
    sip_id: str
    fund: str = Field(max_length=500)
    tradingsymbol: str = Field(max_length=50)
    status: Literal["ACTIVE", "PAUSED", "CANCELLED"]
    frequency: Literal["monthly", "weekly", "quarterly"]
    instalment_amount: float = Field(ge=0)
    completed_instalments: int = Field(ge=0)
    instalment_day: int = Field(ge=0, le=31)
    next_instalment: Optional[str] = None

class KitePortfolioResponse(BaseModel):
    """Full portfolio response with holdings, SIPs, and computed totals."""
    holdings: list[KiteHolding]
    sips: list[KiteSIP]
    total_invested: float = Field(ge=0)
    current_value: float = Field(ge=0)
    total_pnl: float
    pnl_pct: float
    total_monthly_sip: float = Field(ge=0)
    active_sip_count: int = Field(ge=0)
    synced_at: str
    is_stale: bool = False

class KiteStatusResponse(BaseModel):
    """Kite connection status."""
    connected: bool
    connected_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: bool = False
    last_sync: Optional[str] = None
```

## Service Layer: `kite_svc.py`

| Function | Purpose |
|---|---|
| `generate_login_url(user_id)` | Create Kite login URL with signed state JWT + store nonce |
| `exchange_token(request_token, state)` | Validate state + nonce (one-time), exchange for access_token, upsert session via service-role client |
| `get_session(user_id, access_token)` | Get current Kite session via user client (or None) |
| `delete_session(user_id, access_token)` | Remove Kite session via user client |
| `fetch_portfolio(user_id, access_token)` | Call Kite API (holdings + SIPs), merge, compute, save snapshot, return |
| `get_cached_portfolio(user_id, access_token)` | Return last snapshot from DB (for offline/expired) |
| `_cleanup_expired_nonces()` | Delete nonces where `expires_at < now()` (called opportunistically) |

**Kite client initialization:**
```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=settings.kite_api_key)
kite.set_access_token(session.access_token)
holdings = kite.mf_holdings()
sips = kite.mf_sips()
```

**Portfolio merge logic:** Match holdings to SIPs by `tradingsymbol` (ISIN). For each holding, if a matching active SIP exists, attach `sip_amount`, `sip_frequency`, `sip_next_date`. Validate Kite API response through `KiteHolding`/`KiteSIP` Pydantic models before saving to snapshot JSONB.

**Audit logging:** Call `log_audit()` on: `kite_connect`, `kite_disconnect`, `kite_portfolio_sync`.

## Frontend Design

### Navigation

New sidebar entry: **"MF Portfolio"** with `LineChart` icon, route `/mf-portfolio`, positioned before "SIP Tracker" (grouping MF-related pages together).

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
| `hooks/useKitePortfolio.ts` | Single React Query hook for status + portfolio (consistent with existing single-hook-per-feature pattern) |

### Hook Pattern

```typescript
export function useKitePortfolio() {
  const status = useQuery({ queryKey: ["kite-status"], ... });
  const portfolio = useQuery({
    queryKey: ["kite-portfolio"],
    enabled: status.data?.connected && !status.data?.is_expired,
    ...
  });

  return {
    status: status.data,
    statusLoading: status.isLoading,
    portfolio: portfolio.data,
    portfolioLoading: portfolio.isLoading,
    connect: () => { /* redirect to login URL */ },
    disconnect: useMutation({ ... }),
    refresh: () => portfolio.refetch(),
  };
}
```

## Files to Create/Modify

### New files:
- `migrations/011_kite_sessions.sql` — All 3 tables, RLS, triggers, indexes
- `backend/app/services/kite_svc.py` — Kite Connect service layer
- `backend/app/routers/kite.py` — Kite auth + portfolio endpoints
- `frontend/src/pages/MFPortfolio.tsx` — Main page
- `frontend/src/components/portfolio/KiteConnectionBanner.tsx`
- `frontend/src/components/portfolio/PortfolioSummaryCards.tsx`
- `frontend/src/components/portfolio/HoldingsTable.tsx`
- `frontend/src/components/portfolio/ActiveSIPs.tsx`
- `frontend/src/hooks/useKitePortfolio.ts`

### Modified files:
- `backend/app/config.py` — Add 6 new settings (kite_api_key, kite_api_secret, kite_state_secret, kite_redirect_url, frontend_url, supabase_service_key)
- `backend/app/services/supabase_client.py` — Add `get_service_client()`
- `backend/app/exceptions.py` — Add `ExternalServiceError`
- `backend/app/core/models.py` — Add Kite Pydantic models
- `backend/app/main.py` — Register kite router + ExternalServiceError handler
- `frontend/src/lib/constants.ts` — Add "MF Portfolio" to NAV_ITEMS
- `frontend/src/layouts/Sidebar.tsx` — Add LineChart icon
- `frontend/src/App.tsx` — Add /mf-portfolio route
- `schema.sql` — Add all 3 tables for reference

### Dependencies:
- `kiteconnect` Python package (`pip install kiteconnect`) — pin exact version
- PyJWT (already installed) — for signing state tokens

## Security Checklist

- [x] API secret in env vars only — never in code or DB
- [x] Dedicated `KITE_STATE_SECRET` for state JWTs (not reusing `kite_api_secret`)
- [x] One-time-use nonce prevents state JWT replay attacks
- [x] State JWT includes `iss`, `aud` claims for defense-in-depth
- [x] Callback redirect hardcoded to `settings.frontend_url` — no open redirect
- [x] Service-role client only used in callback — all other ops use RLS-scoped user client
- [x] `folio` stripped from API responses — no unnecessary sensitive data
- [x] Log sanitization — no tokens or secrets in logs
- [x] Rate limits: callback 3/min, login-url 5/min (tight for OAuth endpoints)
- [x] Audit logging on connect, disconnect, sync
- [x] No trading/order placement — read-only access
- [x] Access token plain text in DB — documented tradeoff (daily expiry, RLS, 2 users)
- [x] `ExternalServiceError` for Kite failures (not `DatabaseError`)
- [x] Pydantic validation on Kite API responses before storing as JSONB
