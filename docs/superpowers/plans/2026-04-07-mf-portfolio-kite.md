# MF Portfolio (Kite Connect) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live mutual fund portfolio tracking via Zerodha Kite Connect API — OAuth login, MF holdings with P&L, active SIPs, and cached snapshots for offline viewing.

**Architecture:** OAuth flow with signed state JWT + one-time nonce for CSRF/replay protection. Service-role Supabase client for callback upsert. Kite API calls via `kiteconnect` Python SDK. JSONB snapshot caching. React page with connection banner, summary cards, holdings table, and collapsible SIP section.

**Tech Stack:** FastAPI, Supabase PostgreSQL, kiteconnect SDK, PyJWT, React 19, TanStack React Query v5, TailwindCSS 4.2

**Spec:** `docs/superpowers/specs/2026-04-07-mf-portfolio-kite-design.md`

---

## File Map

### New files:
| File | Responsibility |
|---|---|
| `migrations/011_kite_sessions.sql` | Schema: 3 tables (kite_sessions, mf_portfolio_snapshots, kite_oauth_nonces) |
| `backend/app/services/kite_svc.py` | Kite Connect service: OAuth, session CRUD, portfolio fetch, snapshot |
| `backend/app/routers/kite.py` | Kite auth + portfolio API endpoints |
| `frontend/src/pages/MFPortfolio.tsx` | Main page component |
| `frontend/src/components/portfolio/KiteConnectionBanner.tsx` | Connect/disconnect/status |
| `frontend/src/components/portfolio/PortfolioSummaryCards.tsx` | 6 metric cards |
| `frontend/src/components/portfolio/HoldingsTable.tsx` | Fund holdings with SIP info |
| `frontend/src/components/portfolio/ActiveSIPs.tsx` | Collapsible SIP section |
| `frontend/src/hooks/useKitePortfolio.ts` | React Query hook for status + portfolio |

### Modified files:
| File | Change |
|---|---|
| `backend/app/config.py` | Add 6 settings (kite_*, frontend_url, supabase_service_key) |
| `backend/app/services/supabase_client.py` | Add `get_service_client()` |
| `backend/app/exceptions.py` | Add `ExternalServiceError` + handler |
| `backend/app/core/models.py` | Add 4 Kite Pydantic models |
| `backend/app/main.py` | Register kite router + ExternalServiceError handler |
| `backend/requirements.txt` | Add `kiteconnect` |
| `frontend/src/lib/constants.ts` | Add "MF Portfolio" to NAV_ITEMS |
| `frontend/src/layouts/Sidebar.tsx` | Add `LineChart` icon |
| `frontend/src/App.tsx` | Add `/mf-portfolio` route |
| `schema.sql` | Add 3 tables for reference |

---

### Task 1: Database Migration

**Files:**
- Create: `migrations/011_kite_sessions.sql`

- [ ] **Step 1: Write the migration**

Create `migrations/011_kite_sessions.sql`:

```sql
-- Migration 011: Kite Connect MF portfolio integration
-- Tables for OAuth sessions, portfolio snapshots, and OAuth nonces
-- Run in Supabase SQL Editor as a single transaction.

BEGIN;

-- ============================================================
-- 1. kite_sessions (one per user, stores daily access token)
-- ============================================================
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

ALTER TABLE public.kite_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.kite_sessions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.kite_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.kite_sessions
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.kite_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 2. mf_portfolio_snapshots (cached portfolio, one per user)
-- ============================================================
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

ALTER TABLE public.mf_portfolio_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own" ON public.mf_portfolio_snapshots
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "insert_own" ON public.mf_portfolio_snapshots
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own" ON public.mf_portfolio_snapshots
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own" ON public.mf_portfolio_snapshots
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 3. kite_oauth_nonces (replay protection, service-role only)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.kite_oauth_nonces (
    nonce      uuid        PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kite_oauth_nonces_expires
    ON public.kite_oauth_nonces(expires_at);

-- No RLS on nonces — only accessed via service-role client

COMMIT;
```

- [ ] **Step 2: Update schema.sql**

Append the 3 table definitions to schema.sql sections 9, 10, 11.

- [ ] **Step 3: Commit**

```bash
git add migrations/011_kite_sessions.sql schema.sql
git commit -m "feat: add Kite Connect schema migration (sessions, snapshots, nonces)"
```

---

### Task 2: Backend Infrastructure (Config + Exceptions + Supabase Client)

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/services/supabase_client.py`
- Modify: `backend/app/exceptions.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add Kite settings to config.py**

Append these fields to the `Settings` class in `backend/app/config.py`, after `gold_api_key_fallback`:

```python
    # Kite Connect (MF portfolio tracking)
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_state_secret: str = ""          # Dedicated key for signing OAuth state JWTs
    kite_redirect_url: str = "http://localhost:8002/api/kite/callback"
    frontend_url: str = "http://localhost:5175"
    supabase_service_key: str = ""       # Service-role key for OAuth callback bypass
```

- [ ] **Step 2: Add get_service_client to supabase_client.py**

Append to `backend/app/services/supabase_client.py`:

```python
@lru_cache
def get_service_client() -> Client:
    """Service-role client for operations that bypass RLS (e.g., OAuth callback).

    Use sparingly — only when no Supabase JWT is available (browser redirects).
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
```

- [ ] **Step 3: Add ExternalServiceError to exceptions.py**

Add to `backend/app/exceptions.py`, after the `AuthenticationError` class:

```python
class ExternalServiceError(FireTrackerError):
    """Raised when an external API (e.g., Kite Connect) fails."""
    pass
```

Add to the `register_exception_handlers` function:

```python
    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request: Request, exc: ExternalServiceError):
        return JSONResponse(status_code=502, content={"detail": exc.message})
```

- [ ] **Step 4: Add kiteconnect to requirements.txt**

Append to `backend/requirements.txt`:

```
kiteconnect>=5.0.0
```

- [ ] **Step 5: Install dependency**

Run: `cd backend && pip install kiteconnect`

- [ ] **Step 6: Add env vars to .env**

Append to `backend/.env`:

```
KITE_API_KEY=your_kite_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_STATE_SECRET=generate_a_random_32_char_string
KITE_REDIRECT_URL=http://localhost:8002/api/kite/callback
FRONTEND_URL=http://localhost:5175
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

- [ ] **Step 7: Verify imports work**

Run: `cd backend && python -c "from app.config import get_settings; from app.exceptions import ExternalServiceError; from app.services.supabase_client import get_service_client; from kiteconnect import KiteConnect; print('All imports OK')"`

Expected: `All imports OK`

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/services/supabase_client.py backend/app/exceptions.py backend/requirements.txt
git commit -m "feat: add Kite Connect infrastructure (config, exceptions, service client, deps)"
```

---

### Task 3: Pydantic Models

**Files:**
- Modify: `backend/app/core/models.py`

- [ ] **Step 1: Add Kite models**

Append to the end of `backend/app/core/models.py`:

```python
# ---------------------------------------------------------------------------
# Kite Connect MF Portfolio Models
# ---------------------------------------------------------------------------

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
    sip_amount: Optional[float] = None
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

- [ ] **Step 2: Verify models import**

Run: `cd backend && python -c "from app.core.models import KiteHolding, KiteSIP, KitePortfolioResponse, KiteStatusResponse; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/models.py
git commit -m "feat: add Kite Connect Pydantic models"
```

---

### Task 4: Kite Service Layer

**Files:**
- Create: `backend/app/services/kite_svc.py`

- [ ] **Step 1: Write the service**

Create `backend/app/services/kite_svc.py`:

```python
"""Kite Connect service: OAuth, session management, portfolio fetching."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from kiteconnect import KiteConnect

from app.config import get_settings
from app.core.models import KiteHolding, KiteSIP
from app.exceptions import DatabaseError, DataNotFoundError, ExternalServiceError
from app.services.supabase_client import get_service_client, get_user_client

logger = logging.getLogger(__name__)

# IST offset for token expiry calculation
IST = timezone(timedelta(hours=5, minutes=30))


def generate_login_url(user_id: str) -> str:
    """Create Kite login URL with signed state JWT + store nonce."""
    settings = get_settings()
    nonce = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Store nonce for one-time use verification
    try:
        client = get_service_client()
        client.table("kite_oauth_nonces").insert({
            "nonce": nonce,
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
        }).execute()
    except Exception as e:
        logger.error("Could not store OAuth nonce for user %s: %s", user_id, type(e).__name__)
        raise DatabaseError("Could not initiate Kite login") from e

    # Sign state JWT with dedicated secret
    state = jwt.encode(
        {
            "user_id": user_id,
            "nonce": nonce,
            "iss": "fire-tracker",
            "aud": "kite-oauth-state",
            "exp": expires_at,
        },
        settings.kite_state_secret,
        algorithm="HS256",
    )

    login_url = (
        f"https://kite.zerodha.com/connect/login"
        f"?v=3&api_key={settings.kite_api_key}&state={state}"
    )

    # Clean up expired nonces opportunistically
    _cleanup_expired_nonces()

    return login_url


def exchange_token(request_token: str, state: str) -> str:
    """Validate state + nonce, exchange for access_token, store session.

    Returns the user_id from the state JWT.
    Uses service-role client (no Supabase JWT available on callback).
    """
    settings = get_settings()

    # Validate state JWT
    try:
        payload = jwt.decode(
            state,
            settings.kite_state_secret,
            algorithms=["HS256"],
            audience="kite-oauth-state",
            issuer="fire-tracker",
        )
    except jwt.ExpiredSignatureError:
        raise ExternalServiceError("Authorization expired. Please try again.")
    except jwt.InvalidTokenError:
        raise ExternalServiceError("Invalid authorization state.")

    user_id = payload.get("user_id")
    nonce = payload.get("nonce")
    if not user_id or not nonce:
        raise ExternalServiceError("Invalid authorization state.")

    # Verify nonce is unused (one-time use)
    client = get_service_client()
    try:
        nonce_result = (
            client.table("kite_oauth_nonces")
            .select("nonce")
            .eq("nonce", nonce)
            .execute()
        )
        if not nonce_result.data:
            raise ExternalServiceError("Authorization already used or expired.")

        # Delete nonce (consume it)
        client.table("kite_oauth_nonces").delete().eq("nonce", nonce).execute()
    except ExternalServiceError:
        raise
    except Exception as e:
        logger.error("Nonce verification failed for user %s: %s", user_id, type(e).__name__)
        raise DatabaseError("Authorization verification failed.") from e

    # Exchange request_token for access_token via Kite API
    try:
        kite = KiteConnect(api_key=settings.kite_api_key)
        data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
        access_token = data["access_token"]
    except Exception as e:
        logger.error("Kite token exchange failed for user %s: %s", user_id, type(e).__name__)
        raise ExternalServiceError("Could not connect to Zerodha. Please try again.")

    # Calculate expiry (next day 6 AM IST)
    now_ist = datetime.now(IST)
    if now_ist.hour >= 6:
        expires_date = now_ist.date() + timedelta(days=1)
    else:
        expires_date = now_ist.date()
    expires_at = datetime(expires_date.year, expires_date.month, expires_date.day, 6, 0, tzinfo=IST)

    # Upsert session via service-role client (bypasses RLS)
    try:
        client.table("kite_sessions").upsert({
            "user_id": user_id,
            "access_token": access_token,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
        }).execute()
    except Exception as e:
        logger.error("Could not store Kite session for user %s: %s", user_id, type(e).__name__)
        raise DatabaseError("Could not save Kite connection.") from e

    return user_id


def get_session(user_id: str, access_token: str) -> Optional[dict]:
    """Get current Kite session for the user."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("kite_sessions")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not load Kite session for user %s: %s", user_id, type(e).__name__)
        return None


def delete_session(user_id: str, access_token: str) -> None:
    """Remove Kite session (disconnect)."""
    try:
        client = get_user_client(access_token)
        client.table("kite_sessions").delete().eq("user_id", user_id).execute()
    except Exception as e:
        logger.error("Could not delete Kite session for user %s: %s", user_id, type(e).__name__)
        raise DatabaseError("Could not disconnect Kite.") from e


def fetch_portfolio(user_id: str, access_token: str) -> dict:
    """Fetch live portfolio from Kite API, merge holdings + SIPs, save snapshot."""
    settings = get_settings()
    session = get_session(user_id, access_token)
    if not session:
        raise DataNotFoundError("Kite not connected")

    # Check if session is expired
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at.astimezone(timezone.utc):
        # Return cached snapshot with stale flag
        return _get_stale_portfolio(user_id, access_token)

    # Call Kite API
    try:
        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(session["access_token"])
        raw_holdings = kite.mf_holdings()
        raw_sips = kite.mf_sips()
    except Exception as e:
        logger.error("Kite API failed for user %s: %s", user_id, type(e).__name__)
        # Fall back to cached snapshot
        return _get_stale_portfolio(user_id, access_token)

    # Build SIP lookup by tradingsymbol
    sip_lookup: dict[str, dict] = {}
    active_sips = []
    total_monthly_sip = 0.0

    for sip in raw_sips:
        if sip.get("status") == "ACTIVE":
            sip_lookup[sip["tradingsymbol"]] = sip
            amt = float(sip.get("instalment_amount", 0))
            freq = sip.get("frequency", "monthly")
            # Normalize to monthly
            if freq == "weekly":
                total_monthly_sip += amt * 4
            elif freq == "quarterly":
                total_monthly_sip += amt / 3
            else:
                total_monthly_sip += amt

        active_sips.append({
            "sip_id": str(sip.get("sip_id", "")),
            "fund": sip.get("fund", ""),
            "tradingsymbol": sip.get("tradingsymbol", ""),
            "status": sip.get("status", "ACTIVE"),
            "frequency": sip.get("frequency", "monthly"),
            "instalment_amount": float(sip.get("instalment_amount", 0)),
            "completed_instalments": int(sip.get("completed_instalments", 0)),
            "instalment_day": int(sip.get("instalment_day", 0)),
            "next_instalment": sip.get("next_instalment"),
        })

    # Process holdings + merge SIP data
    holdings = []
    total_invested = 0.0
    total_current = 0.0
    total_pnl = 0.0

    for h in raw_holdings:
        qty = float(h.get("quantity", 0))
        avg = float(h.get("average_price", 0))
        last = float(h.get("last_price", 0))
        pnl = float(h.get("pnl", 0))
        invested = round(avg * qty, 2)
        current_value = round(last * qty, 2)
        pnl_pct = round((pnl / invested) * 100, 2) if invested > 0 else 0.0

        total_invested += invested
        total_current += current_value
        total_pnl += pnl

        # Merge SIP info
        ts = h.get("tradingsymbol", "")
        sip = sip_lookup.get(ts)

        holdings.append({
            "fund": h.get("fund", ""),
            "tradingsymbol": ts,
            "quantity": qty,
            "average_price": avg,
            "last_price": last,
            "last_price_date": h.get("last_price_date", ""),
            "pnl": pnl,
            "invested": invested,
            "current_value": current_value,
            "pnl_pct": pnl_pct,
            "sip_amount": float(sip["instalment_amount"]) if sip else None,
            "sip_frequency": sip.get("frequency") if sip else None,
            "sip_next_date": sip.get("next_instalment") if sip else None,
        })

    # Sort by current value descending
    holdings.sort(key=lambda x: x["current_value"], reverse=True)

    overall_pnl_pct = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0.0
    synced_at = datetime.now(timezone.utc).isoformat()

    # Validate through Pydantic models before saving to JSONB
    validated_holdings = [KiteHolding(**h).model_dump() for h in holdings]
    validated_sips = [KiteSIP(**s).model_dump() for s in active_sips]

    portfolio = {
        "holdings": validated_holdings,
        "sips": validated_sips,
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_pct": overall_pnl_pct,
        "total_monthly_sip": round(total_monthly_sip, 2),
        "active_sip_count": len([s for s in active_sips if s["status"] == "ACTIVE"]),
        "synced_at": synced_at,
        "is_stale": False,
    }

    # Save snapshot
    try:
        client = get_user_client(access_token)
        client.table("mf_portfolio_snapshots").upsert({
            "user_id": user_id,
            "snapshot_data": portfolio,
            "synced_at": synced_at,
        }).execute()
    except Exception as e:
        logger.warning("Could not save portfolio snapshot for user %s: %s", user_id, type(e).__name__)

    return portfolio


def get_cached_portfolio(user_id: str, access_token: str) -> Optional[dict]:
    """Return last snapshot for offline/expired viewing."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("mf_portfolio_snapshots")
            .select("snapshot_data, synced_at")
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            snapshot = response.data[0]["snapshot_data"]
            snapshot["is_stale"] = True
            snapshot["synced_at"] = response.data[0]["synced_at"]
            return snapshot
        return None
    except Exception as e:
        logger.error("Could not load cached portfolio for user %s: %s", user_id, type(e).__name__)
        return None


def _get_stale_portfolio(user_id: str, access_token: str) -> dict:
    """Get cached portfolio with stale flag, or raise error."""
    cached = get_cached_portfolio(user_id, access_token)
    if cached:
        return cached
    raise ExternalServiceError("Kite session expired. Please reconnect to Zerodha.")


def _cleanup_expired_nonces() -> None:
    """Delete expired OAuth nonces (opportunistic cleanup)."""
    try:
        client = get_service_client()
        client.table("kite_oauth_nonces").delete().lt(
            "expires_at", datetime.now(timezone.utc).isoformat()
        ).execute()
    except Exception:
        pass  # Non-critical cleanup
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.services.kite_svc import generate_login_url, exchange_token, fetch_portfolio; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/kite_svc.py
git commit -m "feat: add Kite Connect service layer (OAuth, portfolio, snapshots)"
```

---

### Task 5: Kite Router + Register in main.py

**Files:**
- Create: `backend/app/routers/kite.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the router**

Create `backend/app/routers/kite.py`:

```python
"""Kite Connect API routes: OAuth, session management, portfolio."""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from fastapi.responses import JSONResponse

from app.config import get_settings
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import kite_svc
from app.services.audit_svc import log_audit
from app.services.supabase_client import get_service_client

router = APIRouter(tags=["kite"])


@router.get("/kite/login-url")
@limiter.limit("5/minute")
async def get_login_url(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    url = kite_svc.generate_login_url(user.id)
    return {"data": {"url": url}}


@router.get("/kite/callback")
@limiter.limit("3/minute")
async def kite_callback(
    request: Request,
    request_token: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """OAuth callback from Zerodha. No Supabase auth — validates state JWT."""
    settings = get_settings()
    try:
        user_id = kite_svc.exchange_token(request_token, state)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid or expired authorization"})
    # Audit via service-role (no Supabase JWT available on callback)
    try:
        get_service_client().table("audit_log").insert(
            {"user_id": user_id, "action": "kite_connect", "details": {"method": "oauth"}}
        ).execute()
    except Exception:
        pass  # Non-blocking
    return RedirectResponse(
        url=f"{settings.frontend_url}/mf-portfolio?connected=true",
        status_code=302,
    )


@router.get("/kite/status")
@limiter.limit("60/minute")
async def kite_status(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    from datetime import datetime, timezone
    session = kite_svc.get_session(user.id, user.access_token)
    if not session:
        return {"data": {"connected": False, "is_expired": False}}

    expires_at = datetime.fromisoformat(session["expires_at"])
    is_expired = datetime.now(timezone.utc) > expires_at.astimezone(timezone.utc)

    # Get last sync time from snapshot
    cached = kite_svc.get_cached_portfolio(user.id, user.access_token)
    last_sync = cached.get("synced_at") if cached else None

    return {
        "data": {
            "connected": True,
            "connected_at": session.get("connected_at"),
            "expires_at": session.get("expires_at"),
            "is_expired": is_expired,
            "last_sync": last_sync,
        }
    }


@router.delete("/kite/session")
@limiter.limit("10/minute")
async def disconnect_kite(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    kite_svc.delete_session(user.id, user.access_token)
    log_audit(user.id, "kite_disconnect", {}, user.access_token)
    return {"message": "Kite disconnected"}


@router.get("/kite/portfolio")
@limiter.limit("30/minute")
async def get_portfolio(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    portfolio = kite_svc.fetch_portfolio(user.id, user.access_token)
    if not portfolio.get("is_stale"):
        log_audit(user.id, "kite_portfolio_sync", {}, user.access_token)
    return {"data": portfolio}
```

- [ ] **Step 2: Register router in main.py**

In `backend/app/main.py`, update the import line:

```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals, projects, project_expenses, kite
```

Add after project_expenses router:

```python
app.include_router(kite.router, prefix="/api")
```

- [ ] **Step 3: Verify server loads**

Run: `cd backend && python -c "from app.main import app; print('App loaded, routes:', len(app.routes))"`

Expected: prints route count without errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/kite.py backend/app/main.py
git commit -m "feat: add Kite Connect router (OAuth, status, portfolio, disconnect)"
```

---

### Task 6: Frontend Hook

**Files:**
- Create: `frontend/src/hooks/useKitePortfolio.ts`

- [ ] **Step 1: Write the hook**

Create `frontend/src/hooks/useKitePortfolio.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface KiteHolding {
  fund: string;
  tradingsymbol: string;
  quantity: number;
  average_price: number;
  last_price: number;
  last_price_date: string;
  pnl: number;
  invested: number;
  current_value: number;
  pnl_pct: number;
  sip_amount: number | null;
  sip_frequency: string | null;
  sip_next_date: string | null;
}

export interface KiteSIP {
  sip_id: string;
  fund: string;
  tradingsymbol: string;
  status: "ACTIVE" | "PAUSED" | "CANCELLED";
  frequency: "monthly" | "weekly" | "quarterly";
  instalment_amount: number;
  completed_instalments: number;
  instalment_day: number;
  next_instalment: string | null;
}

export interface KitePortfolio {
  holdings: KiteHolding[];
  sips: KiteSIP[];
  total_invested: number;
  current_value: number;
  total_pnl: number;
  pnl_pct: number;
  total_monthly_sip: number;
  active_sip_count: number;
  synced_at: string;
  is_stale: boolean;
}

export interface KiteStatus {
  connected: boolean;
  connected_at?: string;
  expires_at?: string;
  is_expired: boolean;
  last_sync?: string;
}

export function useKitePortfolio() {
  const queryClient = useQueryClient();

  const status = useQuery({
    queryKey: ["kite-status"],
    queryFn: () =>
      api.get<{ data: KiteStatus }>("/api/kite/status").then((r) => r.data),
  });

  const portfolio = useQuery({
    queryKey: ["kite-portfolio"],
    queryFn: () =>
      api.get<{ data: KitePortfolio }>("/api/kite/portfolio").then((r) => r.data),
    enabled: !!status.data?.connected && !status.data?.is_expired,
  });

  const connect = async () => {
    const res = await api.get<{ data: { url: string } }>("/api/kite/login-url");
    window.location.href = res.data.url;
  };

  const disconnect = useMutation({
    mutationFn: () => api.delete("/api/kite/session"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kite-status"] });
      queryClient.invalidateQueries({ queryKey: ["kite-portfolio"] });
    },
  });

  return {
    status: status.data,
    statusLoading: status.isLoading,
    portfolio: portfolio.data,
    portfolioLoading: portfolio.isLoading,
    connect,
    disconnect: disconnect.mutateAsync,
    refresh: () => {
      queryClient.invalidateQueries({ queryKey: ["kite-portfolio"] });
    },
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useKitePortfolio.ts
git commit -m "feat: add useKitePortfolio React Query hook"
```

---

### Task 7: Frontend Components

**Files:**
- Create: `frontend/src/components/portfolio/KiteConnectionBanner.tsx`
- Create: `frontend/src/components/portfolio/PortfolioSummaryCards.tsx`
- Create: `frontend/src/components/portfolio/HoldingsTable.tsx`
- Create: `frontend/src/components/portfolio/ActiveSIPs.tsx`

- [ ] **Step 1: Create all 4 components**

Create `frontend/src/components/portfolio/KiteConnectionBanner.tsx`:

```tsx
import { RefreshCw, LogOut, Link } from "lucide-react";
import type { KiteStatus } from "../../hooks/useKitePortfolio";

interface Props {
  status: KiteStatus | undefined;
  isLoading: boolean;
  onConnect: () => void;
  onDisconnect: () => Promise<unknown>;
  onRefresh: () => void;
  isStale?: boolean;
}

export function KiteConnectionBanner({ status, isLoading, onConnect, onDisconnect, onRefresh, isStale }: Props) {
  if (isLoading) {
    return (
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6 animate-pulse h-14" />
    );
  }

  if (!status?.connected) {
    return (
      <div className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 mb-6 flex items-center justify-between">
        <p className="text-[#E8ECF1]/60 text-sm">Connect your Zerodha account to view live MF portfolio</p>
        <button
          onClick={onConnect}
          className="flex items-center gap-2 bg-[#00895E] hover:bg-[#00895E]/80 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          <Link size={16} />
          Connect Zerodha
        </button>
      </div>
    );
  }

  const syncText = status.last_sync
    ? `Synced ${new Date(status.last_sync).toLocaleTimeString()}`
    : "Not synced yet";

  return (
    <div className={`rounded-xl p-4 border mb-6 flex items-center justify-between ${
      status.is_expired || isStale
        ? "bg-[#3D2E13] border-[#E5A100]/30"
        : "bg-[#132E3D] border-[#1A3A5C]/30"
    }`}>
      <div>
        <p className="text-sm text-[#E8ECF1]">
          {status.is_expired
            ? "Zerodha session expired"
            : isStale
            ? "Showing cached data"
            : "Connected to Zerodha"}
          {" "}<span className="text-[#E8ECF1]/40">— {syncText}</span>
        </p>
      </div>
      <div className="flex items-center gap-2">
        {status.is_expired ? (
          <button
            onClick={onConnect}
            className="flex items-center gap-1 bg-[#D4A843] hover:bg-[#D4A843]/80 text-[#0D1B2A] rounded px-3 py-1.5 text-sm font-medium transition-colors"
          >
            Reconnect
          </button>
        ) : (
          <button
            onClick={onRefresh}
            className="flex items-center gap-1 text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors p-1.5 rounded hover:bg-[#1A3A5C]/30"
          >
            <RefreshCw size={16} />
          </button>
        )}
        <button
          onClick={() => onDisconnect()}
          className="flex items-center gap-1 text-[#E8ECF1]/40 hover:text-[#E5A100] transition-colors p-1.5 rounded hover:bg-[#1A3A5C]/30"
          title="Disconnect Zerodha"
        >
          <LogOut size={16} />
        </button>
      </div>
    </div>
  );
}
```

Create `frontend/src/components/portfolio/PortfolioSummaryCards.tsx`:

```tsx
import { MetricCard } from "../MetricCard";
import type { KitePortfolio } from "../../hooks/useKitePortfolio";

interface Props {
  portfolio: KitePortfolio | undefined;
  isLoading: boolean;
}

export function PortfolioSummaryCards({ portfolio, isLoading }: Props) {
  if (isLoading || !portfolio) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-[#132E3D] rounded-xl p-4 border border-[#1A3A5C]/30 animate-pulse h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      <MetricCard label="Total Invested" value={portfolio.total_invested} color="default" />
      <MetricCard label="Current Value" value={portfolio.current_value} color="gold" />
      <MetricCard
        label="Total P&L"
        value={portfolio.total_pnl}
        suffix={` (${portfolio.pnl_pct >= 0 ? "+" : ""}${portfolio.pnl_pct.toFixed(1)}%)`}
        color={portfolio.total_pnl >= 0 ? "success" : "warning"}
      />
      <MetricCard label="Monthly SIP" value={portfolio.total_monthly_sip} color="default" />
      <MetricCard label="Active SIPs" value={portfolio.active_sip_count} prefix="" color="default" />
      <MetricCard
        label="NAV Date"
        value={0}
        prefix=""
        suffix={portfolio.holdings[0]?.last_price_date || "N/A"}
        color="default"
      />
    </div>
  );
}
```

Create `frontend/src/components/portfolio/HoldingsTable.tsx`:

```tsx
import { formatIndian } from "../../lib/formatIndian";
import type { KiteHolding } from "../../hooks/useKitePortfolio";

interface Props {
  holdings: KiteHolding[];
}

export function HoldingsTable({ holdings }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30 mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
            <th className="px-3 py-2">Fund</th>
            <th className="px-3 py-2 text-right">Invested</th>
            <th className="px-3 py-2 text-right">Current</th>
            <th className="px-3 py-2 text-right">P&L</th>
            <th className="px-3 py-2 text-right">P&L %</th>
            <th className="px-3 py-2 text-right">SIP/mo</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.tradingsymbol} className="border-t border-[#1A3A5C]/20 hover:bg-[#132E3D]/50 text-[#E8ECF1]">
              <td className="px-3 py-2">
                <div className="max-w-[250px]">
                  <p className="truncate font-medium">{h.fund}</p>
                  <p className="text-xs text-[#E8ECF1]/40">{h.quantity.toFixed(3)} units</p>
                </div>
              </td>
              <td className="px-3 py-2 text-right">{`\u20B9${formatIndian(h.invested)}`}</td>
              <td className="px-3 py-2 text-right font-medium">{`\u20B9${formatIndian(h.current_value)}`}</td>
              <td className={`px-3 py-2 text-right ${h.pnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}>
                {h.pnl >= 0 ? "+" : ""}{`\u20B9${formatIndian(Math.abs(h.pnl))}`}
              </td>
              <td className={`px-3 py-2 text-right ${h.pnl_pct >= 0 ? "text-[#00895E]" : "text-[#E5A100]"}`}>
                {h.pnl_pct >= 0 ? "+" : ""}{h.pnl_pct.toFixed(1)}%
              </td>
              <td className="px-3 py-2 text-right text-[#E8ECF1]/60">
                {h.sip_amount ? `\u20B9${formatIndian(h.sip_amount)}` : "\u2014"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {holdings.length === 0 && (
        <p className="text-center text-[#E8ECF1]/40 py-8">No holdings found</p>
      )}
    </div>
  );
}
```

Create `frontend/src/components/portfolio/ActiveSIPs.tsx`:

```tsx
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { formatIndian } from "../../lib/formatIndian";
import type { KiteSIP } from "../../hooks/useKitePortfolio";

interface Props {
  sips: KiteSIP[];
}

export function ActiveSIPs({ sips }: Props) {
  const [open, setOpen] = useState(false);
  const activeSips = sips.filter((s) => s.status === "ACTIVE");

  if (activeSips.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-[#E8ECF1]/60 hover:text-[#E8ECF1] transition-colors mb-3"
      >
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        {open ? "Hide" : "Show"} Active SIPs ({activeSips.length})
      </button>

      {open && (
        <div className="overflow-x-auto rounded-xl border border-[#1A3A5C]/30">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#132E3D] text-[#E8ECF1]/60 text-left">
                <th className="px-3 py-2">Fund</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2">Frequency</th>
                <th className="px-3 py-2">Next Date</th>
                <th className="px-3 py-2 text-right">Instalments Done</th>
              </tr>
            </thead>
            <tbody>
              {activeSips.map((s) => (
                <tr key={s.sip_id} className="border-t border-[#1A3A5C]/20 text-[#E8ECF1]">
                  <td className="px-3 py-2 max-w-[250px] truncate">{s.fund}</td>
                  <td className="px-3 py-2 text-right font-medium">{`\u20B9${formatIndian(s.instalment_amount)}`}</td>
                  <td className="px-3 py-2">
                    <span className="bg-[#1A3A5C]/40 px-2 py-0.5 rounded text-xs capitalize">{s.frequency}</span>
                  </td>
                  <td className="px-3 py-2 text-[#E8ECF1]/60">{s.next_instalment || "\u2014"}</td>
                  <td className="px-3 py-2 text-right text-[#E8ECF1]/60">{s.completed_instalments}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/portfolio/
git commit -m "feat: add MF Portfolio UI components (banner, cards, table, SIPs)"
```

---

### Task 8: MF Portfolio Page + Navigation + Routing

**Files:**
- Create: `frontend/src/pages/MFPortfolio.tsx`
- Modify: `frontend/src/lib/constants.ts`
- Modify: `frontend/src/layouts/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the page**

Create `frontend/src/pages/MFPortfolio.tsx`:

```tsx
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { LoadingState } from "../components/LoadingState";
import { KiteConnectionBanner } from "../components/portfolio/KiteConnectionBanner";
import { PortfolioSummaryCards } from "../components/portfolio/PortfolioSummaryCards";
import { HoldingsTable } from "../components/portfolio/HoldingsTable";
import { ActiveSIPs } from "../components/portfolio/ActiveSIPs";
import { useKitePortfolio } from "../hooks/useKitePortfolio";

export default function MFPortfolio() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { status, statusLoading, portfolio, portfolioLoading, connect, disconnect, refresh } =
    useKitePortfolio();

  // Clear ?connected=true from URL after OAuth redirect
  useEffect(() => {
    if (searchParams.get("connected") === "true") {
      setSearchParams({}, { replace: true });
      refresh();
    }
  }, [searchParams, setSearchParams, refresh]);

  return (
    <div>
      <PageHeader title="MF Portfolio" subtitle="Live mutual fund holdings and SIPs from Zerodha Coin" />

      <KiteConnectionBanner
        status={status}
        isLoading={statusLoading}
        onConnect={connect}
        onDisconnect={disconnect}
        onRefresh={refresh}
        isStale={portfolio?.is_stale}
      />

      {status?.connected && (
        <>
          {portfolioLoading ? (
            <LoadingState message="Fetching portfolio from Zerodha..." />
          ) : portfolio ? (
            <>
              <PortfolioSummaryCards portfolio={portfolio} isLoading={false} />
              <HoldingsTable holdings={portfolio.holdings} />
              <ActiveSIPs sips={portfolio.sips} />
            </>
          ) : null}
        </>
      )}

      {!status?.connected && !statusLoading && (
        <div className="text-center py-16">
          <p className="text-[#E8ECF1]/40 text-lg mb-2">No portfolio data</p>
          <p className="text-[#E8ECF1]/30 text-sm">Connect your Zerodha account to see your MF holdings and SIPs</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add to NAV_ITEMS**

In `frontend/src/lib/constants.ts`, add the MF Portfolio entry BEFORE "SIP Tracker":

```typescript
{ path: "/mf-portfolio", label: "MF Portfolio", icon: "LineChart" },
```

- [ ] **Step 3: Add LineChart icon to Sidebar**

In `frontend/src/layouts/Sidebar.tsx`, add `LineChart` to the lucide-react import and to the `iconMap` object.

- [ ] **Step 4: Add route to App.tsx**

Add lazy import:
```typescript
const MFPortfolio = lazy(() => import("./pages/MFPortfolio"));
```

Add route before sip-tracker:
```typescript
<Route
  path="/mf-portfolio"
  element={
    <ProtectedRoute>
      <MFPortfolio />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/MFPortfolio.tsx frontend/src/lib/constants.ts frontend/src/layouts/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat: add MF Portfolio page with navigation and routing"
```

---

### Task 9: End-to-End Verification

- [ ] **Step 1: Run migration 011 in Supabase SQL Editor**

Copy `migrations/011_kite_sessions.sql` to Supabase SQL Editor and execute.

- [ ] **Step 2: Add env vars**

Add to `backend/.env`:
- `KITE_API_KEY` (already known: `lbljrdla3du1kcgz`)
- `KITE_API_SECRET` (from Kite developer console)
- `KITE_STATE_SECRET` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `SUPABASE_SERVICE_KEY` (from Supabase Dashboard > Settings > API > service_role key)

- [ ] **Step 3: Start backend**

Run: `cd backend && uvicorn app.main:app --reload --port 8002`

Verify: `curl http://localhost:8002/api/health` returns `{"status":"ok"}`

- [ ] **Step 4: Start frontend and test**

Run: `cd frontend && npm run dev`

Navigate to `/mf-portfolio`:
- Should see "Connect Zerodha" banner
- Click "Connect Zerodha" — should redirect to Zerodha login
- After login, should redirect back with holdings data

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: MF Portfolio (Kite Connect) complete - OAuth, portfolio, SIPs"
```
