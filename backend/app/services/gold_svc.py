"""Gold portfolio CRUD and rate fetching service."""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import get_settings
from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_anon_client, get_user_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TROY_OZ_TO_GRAMS = 31.1035
PURITY_FACTORS = {"24K": 1.0, "22K": 22 / 24, "18K": 18 / 24}

# S7: Sanity bounds for fetched gold rate (INR per gram)
RATE_MIN_INR_PER_GRAM = 1000.0
RATE_MAX_INR_PER_GRAM = 500000.0

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


def _is_rate_sane(rate_24k: float) -> bool:
    """S7: Reject fetched rates outside plausible INR/gram range."""
    return RATE_MIN_INR_PER_GRAM <= rate_24k <= RATE_MAX_INR_PER_GRAM


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
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
        resp.raise_for_status()
        body = resp.json()

        if body.get("status") != "success" or body.get("currency") != "INR":
            logger.error("Metals.dev unexpected response: %s", body)
            return None

        price_per_toz = float(body["price"])
        rate_24k = _toz_to_gram(price_per_toz)

        # S7: Sanity check
        if not _is_rate_sane(rate_24k):
            logger.error(
                "Metals.dev rate outside sane range: %.2f INR/gram (expected %s-%s)",
                rate_24k, RATE_MIN_INR_PER_GRAM, RATE_MAX_INR_PER_GRAM,
            )
            return None

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
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()

        # GoldAPI.io provides per-gram rates directly
        rate_24k = float(body.get("price_gram_24k", 0))
        if rate_24k <= 0:
            logger.error("GoldAPI.io returned invalid rate: %s", body)
            return None

        # S7: Sanity check
        if not _is_rate_sane(rate_24k):
            logger.error(
                "GoldAPI.io rate outside sane range: %.2f INR/gram (expected %s-%s)",
                rate_24k, RATE_MIN_INR_PER_GRAM, RATE_MAX_INR_PER_GRAM,
            )
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
    Also cleans up cache rows older than 90 days (A5).
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


def _cleanup_old_cache_rows() -> None:
    """A5: Delete gold_rate_cache rows older than 90 days via direct table filter."""
    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        client = get_anon_client()
        client.table("gold_rate_cache").delete().lt("fetched_at", cutoff).execute()
    except Exception as e:
        logger.warning("Cache cleanup failed (non-blocking): %s", e)


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
        _cleanup_old_cache_rows()
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
