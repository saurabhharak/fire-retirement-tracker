# Gold Portfolio Tracker -- Technical Architecture

**Author:** Architect Agent  
**Date:** 2026-04-02  
**Status:** Ready for implementation  
**Spec:** `specs/gold-portfolio-tracker.md` (all open questions resolved)

---

## 1. Database Layer

### 1.1 Migration File

**File:** `migrations/007_gold_portfolio.sql`

This migration follows the exact pattern established by `005_expense_month_year.sql` and `006_payment_method.sql`: wrapped in `BEGIN;` / `COMMIT;`, using `DO $$` blocks for idempotent DDL, and `CREATE INDEX IF NOT EXISTS`.

```sql
BEGIN;

-- ---------------------------------------------------------------------------
-- 1. gold_purchases table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gold_purchases (
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

-- Index: query pattern is always (user_id, is_active)
CREATE INDEX IF NOT EXISTS idx_gold_purchases_user_active
  ON public.gold_purchases(user_id, is_active);

-- Reuse the existing set_updated_at() trigger function from schema.sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_gold_purchases_updated_at'
  ) THEN
    CREATE TRIGGER trg_gold_purchases_updated_at
        BEFORE UPDATE ON public.gold_purchases
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 2. gold_rate_cache table (global, no user_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gold_rate_cache (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_24k        numeric     NOT NULL CHECK (rate_24k > 0),
    rate_22k        numeric     NOT NULL CHECK (rate_22k > 0),
    rate_18k        numeric     NOT NULL CHECK (rate_18k > 0),
    currency        text        NOT NULL DEFAULT 'INR',
    source          text        NOT NULL,
    fetched_at      timestamptz NOT NULL DEFAULT now()
);

-- Index: always query latest row by fetched_at
CREATE INDEX IF NOT EXISTS idx_gold_rate_cache_fetched_at
  ON public.gold_rate_cache(fetched_at DESC);

-- ---------------------------------------------------------------------------
-- 3. RLS for gold_purchases
-- ---------------------------------------------------------------------------
ALTER TABLE public.gold_purchases ENABLE ROW LEVEL SECURITY;

-- Idempotent policy creation using DO blocks
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'gold_purchases' AND policyname = 'select_own'
  ) THEN
    CREATE POLICY "select_own" ON public.gold_purchases
        FOR SELECT USING (auth.uid() = user_id);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'gold_purchases' AND policyname = 'insert_own'
  ) THEN
    CREATE POLICY "insert_own" ON public.gold_purchases
        FOR INSERT WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'gold_purchases' AND policyname = 'update_own'
  ) THEN
    CREATE POLICY "update_own" ON public.gold_purchases
        FOR UPDATE USING (auth.uid() = user_id)
                  WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'gold_purchases' AND policyname = 'delete_own'
  ) THEN
    CREATE POLICY "delete_own" ON public.gold_purchases
        FOR DELETE USING (auth.uid() = user_id);
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 4. gold_rate_cache: NO RLS (global table, backend-only access)
-- ---------------------------------------------------------------------------
-- gold_rate_cache does not need RLS. The backend accesses it via the
-- service role key (anon client). The frontend never reads this table
-- directly -- it goes through /api/gold-rate.

COMMIT;
```

### 1.2 Generated Column Fallback

Supabase uses PostgreSQL 15+, which supports `GENERATED ALWAYS AS ... STORED`. If for any reason the migration fails on `total_cost`, the fallback is:

1. Replace the generated column line with: `total_cost numeric NOT NULL CHECK (total_cost > 0),`
2. Compute `total_cost = weight_grams * price_per_gram` in the Python service layer before INSERT.
3. Add a CHECK constraint: `CHECK (total_cost = weight_grams * price_per_gram)` to keep data integrity.

### 1.3 Important Note: gold_rate_cache Access

The `gold_rate_cache` table is global (no `user_id`). The backend must use the **anon client** (`get_anon_client()`) to read/write this table, NOT the user-scoped client. This is because:
- No RLS policies exist on this table.
- The user's JWT-scoped client cannot access tables without RLS policies allowing it.
- The anon key has read/write access to tables without RLS in the default Supabase config.

If Supabase's anon key does not have write access, an alternative is to use a service role key. Add `supabase_service_role_key` to `Settings` in `config.py` and create a `get_service_client()` in `supabase_client.py`.

---

## 2. Backend Layer

### 2.1 Config Changes

**File:** `backend/app/config.py`

Add two optional API key fields to the `Settings` class:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str = ""
    environment: str = "production"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Gold rate API keys (optional -- graceful degradation if missing)
    gold_api_key: str = ""           # Metals.dev API key
    gold_api_key_fallback: str = ""  # GoldAPI.io fallback key

    # ... existing validators and properties ...
```

These map to env vars `GOLD_API_KEY` and `GOLD_API_KEY_FALLBACK` in `.env`.

### 2.2 Pydantic Models

**File:** `backend/app/core/models.py`

Add these models after the existing `FixedExpenseUpdate` class. Follows the exact same conventions: `BaseModel`, `Field` constraints, `Literal` for enums, `Optional` for partial updates.

```python
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field

# --- Gold Portfolio Models ---

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

**Notes:**
- `total_cost` is NOT in the create/update models. It is a generated column in PostgreSQL. The API response will include it (returned by Supabase SELECT).
- `is_active` is NOT in `GoldPurchase` (defaults to `true` in DB). It is NOT in `GoldPurchaseUpdate` either -- soft-delete is a dedicated endpoint.
- `purchase_date` uses `date` type (not `str`), matching the `IncomeEntry` pattern for date handling.

### 2.3 Service Layer

**File:** `backend/app/services/gold_svc.py` (new file)

This file follows the exact pattern of `expenses_svc.py`: module-level functions, `get_user_client(access_token)` for RLS-scoped queries, structured exception handling with `DatabaseError`, and `logger` for error logging.

```python
"""Gold portfolio CRUD and rate fetching service."""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from app.config import get_settings
from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_anon_client, get_user_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TROY_OZ_TO_GRAMS = 31.1035
PURITY_FACTORS = {"24K": 1.0, "22K": 22 / 24, "18K": 18 / 24}

# ---------------------------------------------------------------------------
# In-memory gold rate cache
# ---------------------------------------------------------------------------
_rate_cache: dict = {}       # keys: rate_24k, rate_22k, rate_18k, source, fetched_at
_rate_cache_ts: float = 0.0  # epoch timestamp of last cache fill
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


# ===================================================================
# CRUD: Gold Purchases
# ===================================================================

def load_gold_purchases(
    user_id: str,
    access_token: str,
    active_only: bool = True,
) -> list[dict]:
    """Fetch all gold purchases for the authenticated user.

    Returns rows ordered by purchase_date DESC (most recent first).
    """
    try:
        client = get_user_client(access_token)
        query = client.table("gold_purchases").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("purchase_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load gold purchases: %s", e)
        raise DatabaseError("Could not load gold purchases") from e


def save_gold_purchase(
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Insert a new gold purchase. total_cost is a generated column."""
    try:
        client = get_user_client(access_token)
        # Remove total_cost if present -- it is a generated column
        data.pop("total_cost", None)
        payload = {**data, "user_id": user_id}
        # Convert date to ISO string for JSON serialization
        if "purchase_date" in payload and hasattr(payload["purchase_date"], "isoformat"):
            payload["purchase_date"] = payload["purchase_date"].isoformat()
        response = client.table("gold_purchases").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save gold purchase: %s", e)
        raise DatabaseError("Could not save gold purchase") from e


def update_gold_purchase(
    purchase_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Partial update of a gold purchase. Rejects updates on deactivated rows."""
    try:
        client = get_user_client(access_token)
        # Remove total_cost if present -- it is a generated column
        data.pop("total_cost", None)
        # Convert date to ISO string if present
        if "purchase_date" in data and hasattr(data["purchase_date"], "isoformat"):
            data["purchase_date"] = data["purchase_date"].isoformat()
        response = (
            client.table("gold_purchases")
            .update(data)
            .eq("id", purchase_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Gold purchase not found or already deactivated")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update gold purchase: %s", e)
        raise DatabaseError("Could not update gold purchase") from e


def deactivate_gold_purchase(
    purchase_id: str,
    user_id: str,
    access_token: str,
) -> Optional[dict]:
    """Soft-delete a gold purchase by setting is_active=false."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("gold_purchases")
            .update({"is_active": False})
            .eq("id", purchase_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Gold purchase not found or already deactivated")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not deactivate gold purchase: %s", e)
        raise DatabaseError("Could not deactivate gold purchase") from e


# ===================================================================
# Gold Rate Fetching + Caching
# ===================================================================

def _toz_to_gram(price_per_toz: float) -> float:
    """Convert price per troy ounce to price per gram."""
    return price_per_toz / TROY_OZ_TO_GRAMS


def _compute_purity_rates(rate_24k_per_gram: float) -> dict:
    """Derive 22K and 18K rates from 24K rate using standard purity ratios."""
    return {
        "rate_24k": round(rate_24k_per_gram, 2),
        "rate_22k": round(rate_24k_per_gram * PURITY_FACTORS["22K"], 2),
        "rate_18k": round(rate_24k_per_gram * PURITY_FACTORS["18K"], 2),
    }


def _fetch_from_metals_dev() -> Optional[dict]:
    """Call Metals.dev spot API. Returns rate dict or None on failure."""
    settings = get_settings()
    if not settings.gold_api_key:
        logger.warning("GOLD_API_KEY not configured, skipping Metals.dev")
        return None

    try:
        url = "https://api.metals.dev/v1/metal/spot"
        params = {
            "api_key": settings.gold_api_key,
            "metal": "gold",
            "currency": "INR",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()

        if body.get("status") != "success" or body.get("currency") != "INR":
            logger.error("Metals.dev unexpected response: %s", body)
            return None

        price_per_toz = float(body["price"])
        rate_24k = _toz_to_gram(price_per_toz)
        rates = _compute_purity_rates(rate_24k)
        rates["source"] = "metals.dev"
        rates["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return rates
    except Exception as e:
        logger.error("Metals.dev API call failed: %s", e)
        return None


def _fetch_from_goldapi() -> Optional[dict]:
    """Call GoldAPI.io fallback. Returns rate dict or None on failure."""
    settings = get_settings()
    if not settings.gold_api_key_fallback:
        logger.warning("GOLD_API_KEY_FALLBACK not configured, skipping GoldAPI.io")
        return None

    try:
        url = "https://www.goldapi.io/api/XAU/INR"
        headers = {"x-access-token": settings.gold_api_key_fallback}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        body = resp.json()

        # GoldAPI.io provides per-gram rates directly
        rate_24k = float(body.get("price_gram_24k", 0))
        if rate_24k <= 0:
            logger.error("GoldAPI.io returned invalid rate: %s", body)
            return None

        rates = {
            "rate_24k": round(rate_24k, 2),
            "rate_22k": round(float(body.get("price_gram_22k", rate_24k * PURITY_FACTORS["22K"])), 2),
            "rate_18k": round(float(body.get("price_gram_18k", rate_24k * PURITY_FACTORS["18K"])), 2),
            "source": "goldapi.io",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        return rates
    except Exception as e:
        logger.error("GoldAPI.io API call failed: %s", e)
        return None


def _get_db_cached_rate() -> Optional[dict]:
    """Read the latest gold rate from the gold_rate_cache table.

    Uses the anon client (no RLS on this table).
    """
    try:
        client = get_anon_client()
        response = (
            client.table("gold_rate_cache")
            .select("*")
            .eq("currency", "INR")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            row = response.data[0]
            return {
                "rate_24k": float(row["rate_24k"]),
                "rate_22k": float(row["rate_22k"]),
                "rate_18k": float(row["rate_18k"]),
                "currency": row["currency"],
                "source": row["source"],
                "fetched_at": row["fetched_at"],
            }
        return None
    except Exception as e:
        logger.error("Could not read gold rate cache: %s", e)
        return None


def _save_db_cached_rate(rates: dict) -> None:
    """Persist a fresh gold rate into the gold_rate_cache table.

    Uses the anon client (no RLS on this table).
    """
    try:
        client = get_anon_client()
        client.table("gold_rate_cache").insert({
            "rate_24k": rates["rate_24k"],
            "rate_22k": rates["rate_22k"],
            "rate_18k": rates["rate_18k"],
            "currency": "INR",
            "source": rates["source"],
            "fetched_at": rates["fetched_at"],
        }).execute()
    except Exception as e:
        logger.warning("Could not persist gold rate to cache (non-blocking): %s", e)


def _is_rate_stale(fetched_at_str: str, threshold_hours: int = 6) -> bool:
    """Check if a cached rate is older than the threshold."""
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age_seconds > threshold_hours * 3600
    except Exception:
        return True


def fetch_gold_rate() -> Optional[dict]:
    """3-tier cache: in-memory -> DB cache -> external API.

    Returns a dict with keys:
        rate_24k, rate_22k, rate_18k, currency, source, fetched_at, is_stale

    Returns None only if absolutely no rate is available (no cache, no API).
    """
    global _rate_cache, _rate_cache_ts

    # --- Tier 1: In-memory cache (15 min TTL) ---
    if _rate_cache and (time.time() - _rate_cache_ts) < CACHE_TTL_SECONDS:
        return {
            **_rate_cache,
            "currency": "INR",
            "is_stale": _is_rate_stale(_rate_cache["fetched_at"]),
        }

    # --- Tier 2: DB cache ---
    db_rate = _get_db_cached_rate()
    if db_rate:
        # Check if DB cache is fresh enough (< 1 hour) to skip API call
        if not _is_rate_stale(db_rate["fetched_at"], threshold_hours=1):
            # Refresh in-memory cache from DB
            _rate_cache = db_rate
            _rate_cache_ts = time.time()
            return {**db_rate, "is_stale": False}

    # --- Tier 3: External API call ---
    # Try primary: Metals.dev
    rates = _fetch_from_metals_dev()

    # Try fallback: GoldAPI.io
    if rates is None:
        rates = _fetch_from_goldapi()

    if rates is not None:
        # Success -- update both caches
        rates["currency"] = "INR"
        _rate_cache = rates
        _rate_cache_ts = time.time()
        _save_db_cached_rate(rates)
        return {**rates, "is_stale": False}

    # --- Fallback: Return stale DB cache ---
    if db_rate:
        _rate_cache = db_rate
        _rate_cache_ts = time.time()
        return {**db_rate, "is_stale": True}

    # --- No rate available at all ---
    return None


# ===================================================================
# Portfolio Summary (computed)
# ===================================================================

def compute_portfolio_summary(
    user_id: str,
    access_token: str,
) -> Optional[dict]:
    """Aggregate gold holdings against the live rate.

    Returns total weight, cost, current value, P&L, breakdowns by owner
    and purity, and the rate used for computation.
    """
    purchases = load_gold_purchases(user_id, access_token, active_only=True)
    rate = fetch_gold_rate()

    if not purchases:
        return {
            "total_weight_grams": 0,
            "total_cost": 0,
            "current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "by_owner": [],
            "by_purity": [],
            "rate_used": rate,
        }

    # Rate lookup by purity
    if rate:
        rate_map = {
            "24K": rate["rate_24k"],
            "22K": rate["rate_22k"],
            "18K": rate["rate_18k"],
        }
    else:
        rate_map = {"24K": 0, "22K": 0, "18K": 0}

    total_weight = 0.0
    total_cost = 0.0
    total_value = 0.0

    # Accumulators for breakdowns
    owner_agg: dict[str, dict] = {}   # owner -> {weight, cost, value}
    purity_agg: dict[str, dict] = {}  # purity -> {weight, cost, value}

    for p in purchases:
        w = float(p["weight_grams"])
        c = float(p["total_cost"])
        purity = p["purity"]
        owner = p["owner"]
        current_rate = rate_map.get(purity, 0)
        v = w * current_rate

        total_weight += w
        total_cost += c
        total_value += v

        # Owner breakdown
        if owner not in owner_agg:
            owner_agg[owner] = {"weight_grams": 0, "cost": 0, "value": 0}
        owner_agg[owner]["weight_grams"] += w
        owner_agg[owner]["cost"] += c
        owner_agg[owner]["value"] += v

        # Purity breakdown
        if purity not in purity_agg:
            purity_agg[purity] = {"weight_grams": 0, "cost": 0, "value": 0}
        purity_agg[purity]["weight_grams"] += w
        purity_agg[purity]["cost"] += c
        purity_agg[purity]["value"] += v

    total_pnl = total_value - total_cost
    total_pnl_pct = round((total_pnl / total_cost * 100), 2) if total_cost > 0 else 0

    by_owner = [
        {
            "owner": k,
            "weight_grams": round(v["weight_grams"], 3),
            "cost": round(v["cost"], 2),
            "value": round(v["value"], 2),
            "pnl": round(v["value"] - v["cost"], 2),
        }
        for k, v in owner_agg.items()
    ]

    by_purity = [
        {
            "purity": k,
            "weight_grams": round(v["weight_grams"], 3),
            "cost": round(v["cost"], 2),
            "value": round(v["value"], 2),
        }
        for k, v in purity_agg.items()
    ]

    return {
        "total_weight_grams": round(total_weight, 3),
        "total_cost": round(total_cost, 2),
        "current_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "by_owner": by_owner,
        "by_purity": by_purity,
        "rate_used": rate,
    }
```

### 2.4 Router

**File:** `backend/app/routers/gold.py` (new file)

Follows the exact pattern of `expenses.py`: `APIRouter` with tags, `@limiter.limit` decorators, `CurrentUser` dependency, delegating to service functions.

```python
"""Gold portfolio API routes."""
from fastapi import APIRouter, Depends, Query, Request
from app.core.models import GoldPurchase, GoldPurchaseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import gold_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["gold"])


@router.get("/gold-purchases")
@limiter.limit("60/minute")
async def list_gold_purchases(
    request: Request,
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = gold_svc.load_gold_purchases(
        user.id, user.access_token, active_only=active,
    )
    return {"data": entries}


@router.post("/gold-purchases")
@limiter.limit("30/minute")
async def create_gold_purchase(
    request: Request,
    data: GoldPurchase,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = gold_svc.save_gold_purchase(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(user.id, "create_gold_purchase", {"purchase_id": result.get("id") if result else None}, user.access_token)
    return {"data": result, "message": "Gold purchase added"}


@router.patch("/gold-purchases/{purchase_id}")
@limiter.limit("30/minute")
async def update_gold_purchase(
    request: Request,
    purchase_id: str,
    data: GoldPurchaseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = gold_svc.update_gold_purchase(
        purchase_id, user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_gold_purchase", {"purchase_id": purchase_id}, user.access_token)
    return {"data": result, "message": "Gold purchase updated"}


@router.delete("/gold-purchases/{purchase_id}")
@limiter.limit("10/minute")
async def deactivate_gold_purchase(
    request: Request,
    purchase_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    gold_svc.deactivate_gold_purchase(purchase_id, user.id, user.access_token)
    log_audit(user.id, "deactivate_gold_purchase", {"purchase_id": purchase_id}, user.access_token)
    return {"message": "Gold purchase deactivated"}


@router.get("/gold-rate")
@limiter.limit("60/minute")
async def get_gold_rate(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    rate = gold_svc.fetch_gold_rate()
    if rate is None:
        return {"data": None, "message": "Gold rate unavailable"}
    return {"data": rate}


@router.get("/gold-portfolio/summary")
@limiter.limit("30/minute")
async def get_portfolio_summary(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = gold_svc.compute_portfolio_summary(user.id, user.access_token)
    return {"data": summary}
```

### 2.5 Router Registration in main.py

**File:** `backend/app/main.py`

Add the gold router import and registration alongside existing routers:

```python
# Routers
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, gold

app.include_router(fire_inputs.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(gold.router, prefix="/api")       # <-- NEW
app.include_router(sip_log.router, prefix="/api")
app.include_router(projections.router, prefix="/api")
app.include_router(export.router, prefix="/api")
```

### 2.6 Backend Dependency: `requests` library

The gold rate fetching uses `requests` for HTTP calls to external APIs. Verify it is in `requirements.txt`. If not, add `requests>=2.31.0`.

---

## 3. Frontend Layer

### 3.1 TypeScript Interfaces

**File:** `frontend/src/hooks/useGoldPurchases.ts` (interfaces at top of file)

```typescript
export type GoldPurity = "24K" | "22K" | "18K";
export type GoldOwner = "you" | "wife" | "household";

export interface GoldPurchaseEntry {
  id?: string;
  purchase_date: string;   // ISO date string "YYYY-MM-DD"
  weight_grams: number;
  price_per_gram: number;
  total_cost: number;       // generated column from DB
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface GoldPurchaseCreate {
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
}

export interface GoldPurchaseUpdate {
  purchase_date?: string;
  weight_grams?: number;
  price_per_gram?: number;
  purity?: GoldPurity;
  owner?: GoldOwner;
  notes?: string;
}
```

**File:** `frontend/src/hooks/useGoldRate.ts` (interfaces at top of file)

```typescript
export interface GoldRate {
  rate_24k: number;
  rate_22k: number;
  rate_18k: number;
  currency: string;
  source: string;
  fetched_at: string;  // ISO datetime string
  is_stale: boolean;
}
```

**File:** Types for the portfolio summary (used in the page component)

```typescript
export interface GoldOwnerBreakdown {
  owner: GoldOwner;
  weight_grams: number;
  cost: number;
  value: number;
  pnl: number;
}

export interface GoldPurityBreakdown {
  purity: GoldPurity;
  weight_grams: number;
  cost: number;
  value: number;
}

export interface GoldPortfolioSummary {
  total_weight_grams: number;
  total_cost: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  by_owner: GoldOwnerBreakdown[];
  by_purity: GoldPurityBreakdown[];
  rate_used: GoldRate | null;
}
```

### 3.2 Hook: useGoldPurchases.ts

**File:** `frontend/src/hooks/useGoldPurchases.ts`

Follows the exact pattern of `useExpenses.ts`: React Query `useQuery` + `useMutation`, query key array, `invalidateQueries` on mutation success.

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type GoldPurity = "24K" | "22K" | "18K";
export type GoldOwner = "you" | "wife" | "household";

export interface GoldPurchaseEntry {
  id?: string;
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  total_cost: number;
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface GoldPurchaseCreate {
  purchase_date: string;
  weight_grams: number;
  price_per_gram: number;
  purity: GoldPurity;
  owner: GoldOwner;
  notes?: string;
}

export interface GoldPurchaseUpdate {
  purchase_date?: string;
  weight_grams?: number;
  price_per_gram?: number;
  purity?: GoldPurity;
  owner?: GoldOwner;
  notes?: string;
}

export function useGoldPurchases(filters: { active?: boolean } = {}) {
  const queryClient = useQueryClient();
  const active = filters.active ?? true;

  const query = useQuery({
    queryKey: ["gold-purchases", { active }],
    queryFn: () =>
      api
        .get<{ data: GoldPurchaseEntry[] }>(`/api/gold-purchases?active=${active}`)
        .then((r) => r.data),
  });

  const save = useMutation({
    mutationFn: (data: GoldPurchaseCreate) =>
      api.post("/api/gold-purchases", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] }),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoldPurchaseUpdate }) =>
      api.patch(`/api/gold-purchases/${id}`, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] }),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/api/gold-purchases/${id}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["gold-purchases"] }),
  });

  return {
    entries: query.data || [],
    isLoading: query.isLoading,
    save: save.mutateAsync,
    update: update.mutateAsync,
    deactivate: deactivate.mutateAsync,
  };
}
```

### 3.3 Hook: useGoldRate.ts

**File:** `frontend/src/hooks/useGoldRate.ts`

This hook auto-refetches every 15 minutes. Follows the React Query pattern but with `refetchInterval` for polling.

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export interface GoldRate {
  rate_24k: number;
  rate_22k: number;
  rate_18k: number;
  currency: string;
  source: string;
  fetched_at: string;
  is_stale: boolean;
}

export function useGoldRate() {
  const query = useQuery({
    queryKey: ["gold-rate"],
    queryFn: () =>
      api
        .get<{ data: GoldRate | null }>("/api/gold-rate")
        .then((r) => r.data),
    staleTime: 15 * 60 * 1000,       // 15 minutes
    refetchInterval: 15 * 60 * 1000,  // auto-refetch every 15 min
  });

  return {
    rate: query.data ?? null,
    isLoading: query.isLoading,
    isStale: query.data?.is_stale ?? false,
  };
}
```

### 3.4 Hook: useGoldSummary.ts

**File:** `frontend/src/hooks/useGoldSummary.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { GoldRate } from "./useGoldRate";

export interface GoldOwnerBreakdown {
  owner: "you" | "wife" | "household";
  weight_grams: number;
  cost: number;
  value: number;
  pnl: number;
}

export interface GoldPurityBreakdown {
  purity: "24K" | "22K" | "18K";
  weight_grams: number;
  cost: number;
  value: number;
}

export interface GoldPortfolioSummary {
  total_weight_grams: number;
  total_cost: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  by_owner: GoldOwnerBreakdown[];
  by_purity: GoldPurityBreakdown[];
  rate_used: GoldRate | null;
}

export function useGoldSummary() {
  const query = useQuery({
    queryKey: ["gold-portfolio-summary"],
    queryFn: () =>
      api
        .get<{ data: GoldPortfolioSummary }>("/api/gold-portfolio/summary")
        .then((r) => r.data),
    staleTime: 15 * 60 * 1000,  // same as gold rate TTL
  });

  return {
    summary: query.data ?? null,
    isLoading: query.isLoading,
  };
}
```

### 3.5 Component Tree

```
frontend/src/pages/GoldPortfolio.tsx
  |-- PageHeader (existing)
  |-- MetricCard x4 (existing, grid layout)
  |-- frontend/src/components/gold/GoldRateBar.tsx
  |-- Owner filter (inline, same pattern as IncomeExpenses)
  |-- frontend/src/components/gold/GoldPurchaseForm.tsx
  |-- frontend/src/components/gold/GoldHoldingsTable.tsx
```

#### 3.5.1 GoldPortfolio.tsx (Page)

**File:** `frontend/src/pages/GoldPortfolio.tsx`

```typescript
import { useState } from "react";
import { useGoldPurchases } from "../hooks/useGoldPurchases";
import { useGoldRate } from "../hooks/useGoldRate";
import { useGoldSummary } from "../hooks/useGoldSummary";
import { PageHeader } from "../components/PageHeader";
import { MetricCard } from "../components/MetricCard";
import { LoadingState } from "../components/LoadingState";
import { EmptyState } from "../components/EmptyState";
import { GoldRateBar } from "../components/gold/GoldRateBar";
import { GoldPurchaseForm } from "../components/gold/GoldPurchaseForm";
import { GoldHoldingsTable } from "../components/gold/GoldHoldingsTable";
import type { GoldOwner } from "../hooks/useGoldPurchases";

const OWNER_FILTERS: { label: string; value: GoldOwner | "all" }[] = [
  { label: "All", value: "all" },
  { label: "You", value: "you" },
  { label: "Wife", value: "wife" },
  { label: "Household", value: "household" },
];

export default function GoldPortfolio() {
  const [ownerFilter, setOwnerFilter] = useState<GoldOwner | "all">("all");
  const { entries, isLoading, save, deactivate } = useGoldPurchases();
  const { rate, isLoading: rateLoading, isStale } = useGoldRate();
  const { summary, isLoading: summaryLoading } = useGoldSummary();

  if (isLoading || rateLoading || summaryLoading) {
    return <LoadingState message="Loading gold portfolio..." />;
  }

  const filtered =
    ownerFilter === "all"
      ? entries
      : entries.filter((e) => e.owner === ownerFilter);

  const totalWeight = summary?.total_weight_grams ?? 0;
  const totalCost = summary?.total_cost ?? 0;
  const currentValue = summary?.current_value ?? 0;
  const totalPnlPct = summary?.total_pnl_pct ?? 0;

  return (
    <div>
      <PageHeader
        title="Gold Portfolio"
        subtitle="Track your physical gold holdings"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Total Weight"
          value={totalWeight}
          prefix=""
          suffix=" grams"
          color="gold"
        />
        <MetricCard
          label="Total Invested"
          value={totalCost}
          color="default"
        />
        <MetricCard
          label="Current Value"
          value={currentValue}
          color="gold"
        />
        <MetricCard
          label="P&L"
          value={totalPnlPct}
          prefix=""
          suffix="%"
          color={totalPnlPct >= 0 ? "success" : "warning"}
          delta={summary?.total_pnl ?? 0}
          deltaLabel="total P&L"
        />
      </div>

      {/* Live Gold Rate Bar */}
      <GoldRateBar rate={rate} isStale={isStale} />

      {/* Owner Filter */}
      <div className="flex gap-2 mb-4">
        {OWNER_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setOwnerFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              ownerFilter === f.value
                ? "bg-[#00895E] text-white"
                : "bg-[#132E3D] text-[#E8ECF1]/60 hover:text-[#E8ECF1] border border-[#1A3A5C]/30"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Quick-Add Form */}
      <GoldPurchaseForm onSave={save} />

      {/* Holdings Table */}
      {entries.length === 0 ? (
        <EmptyState message="No gold purchases yet. Use the form above to start tracking." />
      ) : (
        <GoldHoldingsTable
          purchases={filtered}
          rate={rate}
          onDeactivate={deactivate}
        />
      )}
    </div>
  );
}
```

#### 3.5.2 GoldRateBar.tsx

**File:** `frontend/src/components/gold/GoldRateBar.tsx`

```typescript
import type { GoldRate } from "../../hooks/useGoldRate";
import { formatRupees } from "../../lib/formatIndian";

interface GoldRateBarProps {
  rate: GoldRate | null;
  isStale: boolean;
}

export function GoldRateBar({ rate, isStale }: GoldRateBarProps) {
  if (!rate) {
    return (
      <div className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#E5A100]/30 text-center">
        <span className="text-[#E5A100] text-sm">
          Gold rate unavailable. P&L values will show "--".
        </span>
      </div>
    );
  }

  const updatedAt = new Date(rate.fetched_at).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-6">
          <div>
            <span className="text-xs text-[#E8ECF1]/40 block">24K</span>
            <span className="text-sm font-bold text-[#D4A843]">
              {formatRupees(rate.rate_24k)}/g
            </span>
          </div>
          <div>
            <span className="text-xs text-[#E8ECF1]/40 block">22K</span>
            <span className="text-sm font-bold text-[#D4A843]/80">
              {formatRupees(rate.rate_22k)}/g
            </span>
          </div>
          <div>
            <span className="text-xs text-[#E8ECF1]/40 block">18K</span>
            <span className="text-sm font-bold text-[#E8ECF1]/60">
              {formatRupees(rate.rate_18k)}/g
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#E8ECF1]/40">
          <span>Source: {rate.source}</span>
          <span>Updated: {updatedAt}</span>
          {isStale && (
            <span className="px-2 py-0.5 bg-[#E5A100]/20 text-[#E5A100] rounded-full font-medium">
              Rate may be outdated
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
```

#### 3.5.3 GoldPurchaseForm.tsx

**File:** `frontend/src/components/gold/GoldPurchaseForm.tsx`

Follows the exact pattern of `ExpenseQuickAdd.tsx`: form state object, validation, submit handler, grid layout with `inputCls` and `btnPrimary` styles.

```typescript
import { useState } from "react";
import type { GoldPurchaseCreate, GoldPurity, GoldOwner } from "../../hooks/useGoldPurchases";
import { inputCls, btnPrimary } from "../../lib/styles";

interface GoldPurchaseFormProps {
  onSave: (data: GoldPurchaseCreate) => Promise<unknown>;
}

interface FormState {
  purchase_date: string;
  weight_grams: number | "";
  price_per_gram: number | "";
  purity: GoldPurity;
  owner: GoldOwner;
  notes: string;
}

export function GoldPurchaseForm({ onSave }: GoldPurchaseFormProps) {
  const today = new Date().toISOString().split("T")[0];

  const [form, setForm] = useState<FormState>({
    purchase_date: today,
    weight_grams: "",
    price_per_gram: "",
    purity: "24K",
    owner: "you",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const weight = Number(form.weight_grams);
    const price = Number(form.price_per_gram);

    if (!weight || weight <= 0) {
      setError("Weight must be greater than 0");
      return;
    }
    if (!price || price <= 0) {
      setError("Price per gram must be greater than 0");
      return;
    }
    if (!form.purchase_date) {
      setError("Please select a purchase date");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        purchase_date: form.purchase_date,
        weight_grams: weight,
        price_per_gram: price,
        purity: form.purity,
        owner: form.owner,
        notes: form.notes,
      });
      // Reset form
      setForm({
        purchase_date: today,
        weight_grams: "",
        price_per_gram: "",
        purity: "24K",
        owner: "you",
        notes: "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save purchase");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-[#132E3D] rounded-xl p-4 mb-4 border border-[#1A3A5C]/30"
    >
      <h3 className="text-sm font-medium text-[#E8ECF1]/80 mb-3">
        Add Gold Purchase
      </h3>
      {error && (
        <div className="mb-3 px-4 py-2 bg-[#E5A100]/10 border border-[#E5A100]/30 rounded-lg text-[#E5A100] text-sm">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-3 items-end">
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Date</label>
          <input
            type="date"
            value={form.purchase_date}
            onChange={(e) => setForm({ ...form, purchase_date: e.target.value })}
            min="2000-01-01"
            required
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">
            Weight (g)
            <span className="ml-1 text-[#E8ECF1]/30" title="1 tola = 11.664 grams">?</span>
          </label>
          <input
            type="number"
            placeholder="e.g. 10"
            value={form.weight_grams}
            onChange={(e) =>
              setForm({ ...form, weight_grams: e.target.value === "" ? "" : Number(e.target.value) })
            }
            step="0.001"
            min="0.001"
            required
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Price/g</label>
          <input
            type="number"
            placeholder="e.g. 13500"
            value={form.price_per_gram}
            onChange={(e) =>
              setForm({ ...form, price_per_gram: e.target.value === "" ? "" : Number(e.target.value) })
            }
            step="0.01"
            min="0.01"
            required
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Purity</label>
          <select
            value={form.purity}
            onChange={(e) => setForm({ ...form, purity: e.target.value as GoldPurity })}
            className={inputCls}
          >
            <option value="24K">24K</option>
            <option value="22K">22K</option>
            <option value="18K">18K</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Owner</label>
          <select
            value={form.owner}
            onChange={(e) => setForm({ ...form, owner: e.target.value as GoldOwner })}
            className={inputCls}
          >
            <option value="you">You</option>
            <option value="wife">Wife</option>
            <option value="household">Household</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-[#E8ECF1]/60 mb-1">Notes</label>
          <input
            type="text"
            placeholder="Optional"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            maxLength={500}
            className={inputCls}
          />
        </div>
        <button type="submit" disabled={saving} className={btnPrimary}>
          {saving ? "Saving..." : "Add"}
        </button>
      </div>
    </form>
  );
}
```

#### 3.5.4 GoldHoldingsTable.tsx

**File:** `frontend/src/components/gold/GoldHoldingsTable.tsx`

Follows the exact pattern of `ExpenseTable.tsx`: table with headers, row rendering, owner badges, action buttons, running totals row.

```typescript
import type { GoldPurchaseEntry, GoldPurity } from "../../hooks/useGoldPurchases";
import type { GoldRate } from "../../hooks/useGoldRate";
import { formatRupees } from "../../lib/formatIndian";

interface GoldHoldingsTableProps {
  purchases: GoldPurchaseEntry[];
  rate: GoldRate | null;
  onDeactivate: (id: string) => Promise<unknown>;
}

const PURITY_RATES: Record<string, keyof GoldRate> = {
  "24K": "rate_24k",
  "22K": "rate_22k",
  "18K": "rate_18k",
};

function ownerBadge(owner?: string) {
  const cls =
    owner === "you"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : owner === "wife"
        ? "bg-[#E07A5F]/20 text-[#E07A5F]"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  const label =
    owner === "you" ? "You" : owner === "wife" ? "Wife" : "Household";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function purityBadge(purity: GoldPurity) {
  const cls =
    purity === "24K"
      ? "bg-[#D4A843]/20 text-[#D4A843]"
      : purity === "22K"
        ? "bg-[#D4A843]/10 text-[#D4A843]/70"
        : "bg-[#6B7280]/20 text-[#6B7280]";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {purity}
    </span>
  );
}

function getCurrentValue(
  weight: number,
  purity: GoldPurity,
  rate: GoldRate | null,
): number | null {
  if (!rate) return null;
  const rateKey = PURITY_RATES[purity];
  const ratePerGram = rate[rateKey] as number;
  return weight * ratePerGram;
}

export function GoldHoldingsTable({
  purchases,
  rate,
  onDeactivate,
}: GoldHoldingsTableProps) {
  if (purchases.length === 0) {
    return (
      <div className="text-center py-8 text-[#E8ECF1]/40 text-sm">
        No gold purchases match the current filter.
      </div>
    );
  }

  // Running totals
  let totalWeight = 0;
  let totalCost = 0;
  let totalValue = 0;

  const rows = purchases.map((p) => {
    const currentValue = getCurrentValue(p.weight_grams, p.purity, rate);
    const pnl = currentValue !== null ? currentValue - p.total_cost : null;
    const pnlPct =
      pnl !== null && p.total_cost > 0
        ? ((pnl / p.total_cost) * 100).toFixed(1)
        : null;

    totalWeight += p.weight_grams;
    totalCost += p.total_cost;
    if (currentValue !== null) totalValue += currentValue;

    return { ...p, currentValue, pnl, pnlPct };
  });

  const totalPnl = totalValue - totalCost;

  return (
    <div className="bg-[#132E3D] rounded-xl border border-[#1A3A5C]/30 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[#E8ECF1]/40 text-xs uppercase tracking-wider border-b border-[#1A3A5C]/30">
              <th className="text-left py-3 px-2">Date</th>
              <th className="text-left py-3 px-2">Owner</th>
              <th className="text-left py-3 px-2">Purity</th>
              <th className="text-right py-3 px-2">Weight (g)</th>
              <th className="text-right py-3 px-2">Price/g</th>
              <th className="text-right py-3 px-2">Cost</th>
              <th className="text-right py-3 px-2">Value</th>
              <th className="text-right py-3 px-2">P&L</th>
              <th className="text-right py-3 px-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const pnlColor =
                row.pnl === null
                  ? "text-[#E8ECF1]/40"
                  : row.pnl >= 0
                    ? "text-[#00895E]"
                    : "text-[#E5A100]";

              return (
                <tr
                  key={row.id ?? row.purchase_date}
                  className="border-b border-[#1A3A5C]/20 hover:bg-[#1A3A5C]/10 transition-colors"
                >
                  <td className="py-3 px-2 text-[#E8ECF1]">{row.purchase_date}</td>
                  <td className="py-3 px-2">{ownerBadge(row.owner)}</td>
                  <td className="py-3 px-2">{purityBadge(row.purity)}</td>
                  <td className="py-3 px-2 text-right text-[#E8ECF1]">
                    {row.weight_grams.toFixed(3)}
                  </td>
                  <td className="py-3 px-2 text-right text-[#E8ECF1]/60">
                    {formatRupees(row.price_per_gram)}
                  </td>
                  <td className="py-3 px-2 text-right text-[#E8ECF1]">
                    {formatRupees(row.total_cost)}
                  </td>
                  <td className="py-3 px-2 text-right text-[#D4A843]">
                    {row.currentValue !== null ? formatRupees(row.currentValue) : "--"}
                  </td>
                  <td className={`py-3 px-2 text-right font-medium ${pnlColor}`}>
                    {row.pnl !== null
                      ? `${row.pnl >= 0 ? "+" : ""}${formatRupees(row.pnl)} (${row.pnlPct}%)`
                      : "--"}
                  </td>
                  <td className="py-3 px-2 text-right">
                    <button
                      onClick={() => row.id && onDeactivate(row.id)}
                      disabled={!row.id}
                      className="text-[#E5A100] hover:text-[#E5A100]/80 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              );
            })}
            {/* Running Totals Row */}
            <tr className="border-t-2 border-[#D4A843]/30 bg-[#0D1B2A]/40">
              <td colSpan={3} className="px-2 py-3 font-bold text-[#D4A843]">
                Running Total
              </td>
              <td className="px-2 py-3 text-right font-bold text-[#D4A843]">
                {totalWeight.toFixed(3)}
              </td>
              <td className="px-2 py-3" />
              <td className="px-2 py-3 text-right font-bold text-[#D4A843]">
                {formatRupees(totalCost)}
              </td>
              <td className="px-2 py-3 text-right font-bold text-[#D4A843]">
                {rate ? formatRupees(totalValue) : "--"}
              </td>
              <td
                className={`px-2 py-3 text-right font-bold ${
                  totalPnl >= 0 ? "text-[#00895E]" : "text-[#E5A100]"
                }`}
              >
                {rate ? `${totalPnl >= 0 ? "+" : ""}${formatRupees(totalPnl)}` : "--"}
              </td>
              <td className="px-2 py-3" />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### 3.6 Navigation Changes

#### 3.6.1 constants.ts

**File:** `frontend/src/lib/constants.ts`

Add the Gold Portfolio entry after Income & Expenses:

```typescript
export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "LayoutDashboard" },
  { path: "/income-expenses", label: "Income & Expenses", icon: "Coins" },
  { path: "/gold-portfolio", label: "Gold Portfolio", icon: "Gem" },   // <-- NEW
  { path: "/fire-settings", label: "FIRE Settings", icon: "Settings" },
  { path: "/fund-allocation", label: "Fund Allocation", icon: "Briefcase" },
  { path: "/growth-projection", label: "Growth Projection", icon: "TrendingUp" },
  { path: "/retirement-analysis", label: "Retirement Analysis", icon: "Shield" },
  { path: "/sip-tracker", label: "SIP Tracker", icon: "ClipboardList" },
  { path: "/settings-privacy", label: "Settings & Privacy", icon: "Lock" },
] as const;
```

#### 3.6.2 Sidebar.tsx

**File:** `frontend/src/layouts/Sidebar.tsx`

Add `Gem` to the lucide-react import and `iconMap`:

```typescript
import {
  LayoutDashboard,
  Coins,
  Gem,          // <-- NEW
  Settings,
  Briefcase,
  TrendingUp,
  Shield,
  ClipboardList,
  Lock,
  LogOut,
  X,
} from "lucide-react";

const iconMap: Record<string, React.ComponentType<{ size?: number }>> = {
  LayoutDashboard,
  Coins,
  Gem,           // <-- NEW
  Settings,
  Briefcase,
  TrendingUp,
  Shield,
  ClipboardList,
  Lock,
};
```

No other changes needed in Sidebar.tsx -- it dynamically renders from `NAV_ITEMS`.

#### 3.6.3 App.tsx

**File:** `frontend/src/App.tsx`

Add the lazy import and route:

```typescript
// Add to lazy imports section:
const GoldPortfolio = lazy(() => import("./pages/GoldPortfolio"));

// Add route after the /income-expenses route:
<Route
  path="/gold-portfolio"
  element={
    <ProtectedRoute>
      <GoldPortfolio />
    </ProtectedRoute>
  }
/>
```

---

## 4. Data Flow

### 4.1 User Adds a Gold Purchase

```
1. User fills GoldPurchaseForm fields (date, weight, price/g, purity, owner, notes)
2. User clicks "Add" button
3. GoldPurchaseForm.handleSubmit() validates inputs
4. Calls onSave(data) which is save.mutateAsync from useGoldPurchases
5. Hook sends POST /api/gold-purchases with JSON body
6. api.ts attaches Bearer token from Supabase session
7. FastAPI gold.py router receives request
8. Pydantic GoldPurchase model validates the body
9. gold_svc.save_gold_purchase() is called
10. Service creates Supabase user-scoped client (RLS)
11. INSERT into gold_purchases table (total_cost is auto-generated)
12. PostgreSQL CHECK constraints validate data
13. Response returns the inserted row (including id, total_cost, timestamps)
14. Router returns {"data": row, "message": "Gold purchase added"}
15. audit_svc logs the action
16. React Query onSuccess fires queryClient.invalidateQueries(["gold-purchases"])
17. useGoldPurchases refetches GET /api/gold-purchases
18. useGoldSummary also refetches (separate query key, triggered manually or by staleTime)
19. UI re-renders with the new purchase in GoldHoldingsTable
```

### 4.2 Gold Rate Fetch Flow (On-Demand)

```
1. GoldPortfolio page mounts
2. useGoldRate() hook fires queryFn
3. GET /api/gold-rate is called
4. gold_svc.fetch_gold_rate() executes the 3-tier cache:

   Tier 1: Check in-memory _rate_cache
   - If populated AND < 15 min old -> return immediately (no DB or API call)

   Tier 2: Check gold_rate_cache table
   - Query latest row WHERE currency='INR' ORDER BY fetched_at DESC LIMIT 1
   - If row exists AND < 1 hour old -> return it, update in-memory cache

   Tier 3: External API call
   - Try Metals.dev: GET /v1/metal/spot?metal=gold&currency=INR
   - Convert troy oz to grams: price / 31.1035
   - Derive 22K = 24K * (22/24), 18K = 24K * (18/24)
   - On success: INSERT into gold_rate_cache, update in-memory cache, return

   - If Metals.dev fails, try GoldAPI.io: GET /api/XAU/INR
   - GoldAPI provides gram prices directly
   - On success: same cache update flow

   Fallback: If both APIs fail
   - Return stale DB cache row with is_stale=true
   - If no DB cache at all, return None

5. Response reaches frontend: {"data": {...rate data...}}
6. useGoldRate stores in React Query cache (staleTime: 15 min)
7. refetchInterval: auto re-fetches every 15 min while page is mounted
8. GoldRateBar component renders rates, shows stale badge if is_stale=true
9. GoldHoldingsTable uses rate to compute per-row current value and P&L
```

### 4.3 Portfolio Summary Computation

```
1. useGoldSummary hook calls GET /api/gold-portfolio/summary
2. gold_svc.compute_portfolio_summary() is called:
   a. Load all active gold_purchases for user (via RLS)
   b. Fetch current gold rate (3-tier cache)
   c. For each purchase:
      - Look up rate for its purity (24K/22K/18K)
      - current_value = weight_grams * rate_for_purity
      - pnl = current_value - total_cost
   d. Aggregate by owner and by purity
   e. Compute totals: total_weight, total_cost, total_value, total_pnl, total_pnl_pct
3. Response includes all aggregates + rate_used for display
4. Frontend MetricCard components render the summary data
```

---

## 5. Implementation Plan

### Step 1: Database Migration

**Files to create:**
- `migrations/007_gold_portfolio.sql`

**Actions:**
1. Create the migration file with the exact SQL from Section 1.1
2. Run the migration in the Supabase SQL Editor

**Verification:**
```bash
# Verify tables exist in Supabase SQL Editor:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('gold_purchases', 'gold_rate_cache');

# Verify RLS is enabled:
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename = 'gold_purchases';

# Verify generated column:
SELECT column_name, is_generated FROM information_schema.columns
WHERE table_name = 'gold_purchases' AND column_name = 'total_cost';
```

**Dependencies:** None (first step)

---

### Step 2: Backend Config + Models

**Files to modify:**
- `backend/app/config.py` -- add `gold_api_key` and `gold_api_key_fallback`
- `backend/app/core/models.py` -- add `GoldPurchase` and `GoldPurchaseUpdate`
- `.env` -- add `GOLD_API_KEY=` and `GOLD_API_KEY_FALLBACK=` (empty during dev)

**Actions:**
1. Add the two optional Settings fields (Section 2.1)
2. Add the two Pydantic models (Section 2.2)
3. Add env vars to `.env` (can be empty initially)

**Verification:**
```bash
cd backend
python -c "from app.core.models import GoldPurchase, GoldPurchaseUpdate; print('Models OK')"
python -c "from app.config import get_settings; s = get_settings(); print(f'gold_api_key={repr(s.gold_api_key)}')"
```

**Dependencies:** None

---

### Step 3: Backend Service Layer

**Files to create:**
- `backend/app/services/gold_svc.py`

**Actions:**
1. Create the full service file (Section 2.3)
2. Verify imports resolve correctly

**Verification:**
```bash
cd backend
python -c "from app.services import gold_svc; print('Service imports OK')"
```

**Dependencies:** Step 2 (needs models and config)

---

### Step 4: Backend Router + Registration

**Files to create:**
- `backend/app/routers/gold.py`

**Files to modify:**
- `backend/app/main.py` -- add gold router import and registration

**Actions:**
1. Create the router file (Section 2.4)
2. Add the import and `app.include_router(gold.router, prefix="/api")` to main.py (Section 2.5)

**Verification:**
```bash
cd backend
# Start the server and check endpoints exist:
uvicorn app.main:app --reload &
sleep 3

# Check the OpenAPI docs list the new endpoints:
curl -s http://localhost:8000/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
paths = [p for p in spec['paths'] if 'gold' in p]
print('Gold endpoints:', paths)
assert len(paths) >= 4, 'Expected at least 4 gold endpoints'
print('Router OK')
"
```

**Dependencies:** Step 3 (needs service layer)

---

### Step 5: Backend Integration Test

**Actions:**
1. Start the backend server
2. Obtain a test JWT from Supabase
3. Test each endpoint manually:

```bash
# Get gold rate (may return null if no API keys configured)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/gold-rate

# Create a gold purchase
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purchase_date":"2026-03-15","weight_grams":10,"price_per_gram":13500,"purity":"24K","owner":"you","notes":"Test"}' \
  http://localhost:8000/api/gold-purchases

# List gold purchases
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/gold-purchases

# Get portfolio summary
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/gold-portfolio/summary

# Soft-delete (use the id from the create response)
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/gold-purchases/{id}
```

**Dependencies:** Steps 1-4

---

### Step 6: Frontend Hooks

**Files to create:**
- `frontend/src/hooks/useGoldPurchases.ts`
- `frontend/src/hooks/useGoldRate.ts`
- `frontend/src/hooks/useGoldSummary.ts`

**Actions:**
1. Create the three hook files (Sections 3.2, 3.3, 3.4)

**Verification:**
```bash
cd frontend
npx tsc --noEmit 2>&1 | grep -i gold || echo "No TypeScript errors for gold hooks"
```

**Dependencies:** None (can be done in parallel with backend steps)

---

### Step 7: Frontend Components

**Files to create:**
- `frontend/src/components/gold/GoldRateBar.tsx`
- `frontend/src/components/gold/GoldPurchaseForm.tsx`
- `frontend/src/components/gold/GoldHoldingsTable.tsx`

**Actions:**
1. Create the `frontend/src/components/gold/` directory
2. Create the three component files (Sections 3.5.2, 3.5.3, 3.5.4)

**Verification:**
```bash
cd frontend
npx tsc --noEmit 2>&1 | grep -i gold || echo "No TypeScript errors for gold components"
```

**Dependencies:** Step 6 (components import hook types)

---

### Step 8: Frontend Page

**Files to create:**
- `frontend/src/pages/GoldPortfolio.tsx`

**Actions:**
1. Create the page component (Section 3.5.1)

**Verification:**
```bash
cd frontend
npx tsc --noEmit 2>&1 | grep -i "GoldPortfolio" || echo "No TypeScript errors for GoldPortfolio page"
```

**Dependencies:** Steps 6-7

---

### Step 9: Navigation Integration

**Files to modify:**
- `frontend/src/lib/constants.ts` -- add NAV_ITEMS entry
- `frontend/src/layouts/Sidebar.tsx` -- add Gem icon import + iconMap entry
- `frontend/src/App.tsx` -- add lazy import + route

**Actions:**
1. Add the nav item to `NAV_ITEMS` after Income & Expenses (Section 3.6.1)
2. Add `Gem` to Sidebar imports and iconMap (Section 3.6.2)
3. Add lazy import and `<Route>` in App.tsx (Section 3.6.3)

**Verification:**
```bash
cd frontend
npm run build 2>&1 | tail -5
# Should complete without errors

# Manual: Open the app in browser, verify "Gold Portfolio" appears in sidebar
# after "Income & Expenses", click it, verify the page loads
```

**Dependencies:** Step 8

---

### Step 10: End-to-End Verification

**Actions:**
1. Start both backend and frontend dev servers
2. Log in to the app
3. Navigate to Gold Portfolio via sidebar
4. Verify empty state message appears
5. Add a gold purchase using the form
6. Verify the purchase appears in the table
7. Verify summary cards update
8. Verify the gold rate bar displays (or shows "unavailable" if no API key)
9. Test owner filter buttons
10. Test soft-delete (Remove button)
11. Verify the deactivated purchase no longer appears

**Dependencies:** Steps 1-9

---

### Step 11: Gold API Key Setup (Optional for Dev)

**Actions:**
1. Sign up for Metals.dev free tier at https://metals.dev
2. Copy the API key into `.env` as `GOLD_API_KEY=your_key_here`
3. Optionally sign up for GoldAPI.io free tier and set `GOLD_API_KEY_FALLBACK=`
4. Restart the backend
5. Verify `/api/gold-rate` returns live rates with `is_stale: false`
6. Verify gold portfolio summary shows correct current values

**Dependencies:** Step 10 (everything else working first)

---

## 6. File Inventory

### New Files (10)

| # | File | Type |
|---|------|------|
| 1 | `migrations/007_gold_portfolio.sql` | Database migration |
| 2 | `backend/app/services/gold_svc.py` | Backend service |
| 3 | `backend/app/routers/gold.py` | Backend router |
| 4 | `frontend/src/hooks/useGoldPurchases.ts` | Frontend hook |
| 5 | `frontend/src/hooks/useGoldRate.ts` | Frontend hook |
| 6 | `frontend/src/hooks/useGoldSummary.ts` | Frontend hook |
| 7 | `frontend/src/components/gold/GoldRateBar.tsx` | Frontend component |
| 8 | `frontend/src/components/gold/GoldPurchaseForm.tsx` | Frontend component |
| 9 | `frontend/src/components/gold/GoldHoldingsTable.tsx` | Frontend component |
| 10 | `frontend/src/pages/GoldPortfolio.tsx` | Frontend page |

### Modified Files (5)

| # | File | Changes |
|---|------|---------|
| 1 | `backend/app/config.py` | Add `gold_api_key`, `gold_api_key_fallback` to Settings |
| 2 | `backend/app/core/models.py` | Add `GoldPurchase`, `GoldPurchaseUpdate` models |
| 3 | `backend/app/main.py` | Import and register gold router |
| 4 | `frontend/src/lib/constants.ts` | Add Gold Portfolio to NAV_ITEMS |
| 5 | `frontend/src/layouts/Sidebar.tsx` | Add Gem icon import + iconMap entry |
| 6 | `frontend/src/App.tsx` | Add lazy import + Route for GoldPortfolio |

### Environment Changes (1)

| # | File | Changes |
|---|------|---------|
| 1 | `.env` | Add `GOLD_API_KEY=` and `GOLD_API_KEY_FALLBACK=` |

---

## 7. Design Compliance Notes

- **No red colors:** All negative P&L uses amber `#E5A100`, not red. Error messages in the form also use amber backgrounds (`bg-[#E5A100]/10`) instead of red.
- **Prosperity palette:** Gold highlights use `#D4A843`. Positive values use `#00895E`. Background surfaces use `#0D1B2A` / `#132E3D`.
- **Owner badges:** Identical colors to `ExpenseTable.tsx` -- You: `#D4A843`, Wife: `#E07A5F`, Household: `#6B7280`.
- **Running totals row:** Gold-colored (`text-[#D4A843]`) with `bg-[#0D1B2A]/40`, matching the SipTracker pattern.
- **Stale rate badge:** Uses `#E5A100` amber with `/20` opacity background.
- **Empty state:** Uses the existing `EmptyState` component with contextual message.
- **Form error styling:** Uses amber (not red) for the error banner, matching the design constraint. The existing `ExpenseQuickAdd` uses `red-500` -- this should be considered for a future consistency pass, but the gold form is correct per the design rules.
