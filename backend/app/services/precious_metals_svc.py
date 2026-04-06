"""Precious metals (gold, silver, platinum) portfolio CRUD and rate fetching service.

Replaces gold_svc.py with multi-metal support. Provides:
- Per-metal purity factors and sanity bounds
- Metals.dev /v1/latest API (all metals in one call) + GoldAPI.io fallback
- 3-tier caching (memory -> DB -> API)
- CRUD operations against precious_metal_purchases table
- Portfolio summary with per-metal and per-owner breakdowns
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import get_settings
from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_anon_client, get_user_client

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

PURE_PURITY: dict[str, str] = {"gold": "24K", "silver": "999", "platinum": "999"}

SANITY_BOUNDS: dict[str, tuple[float, float]] = {
    "gold": (1000, 500000),       # INR per gram
    "silver": (50, 500),
    "platinum": (1000, 200000),
}

GOLDAPI_SYMBOLS: dict[str, str] = {"gold": "XAU", "silver": "XAG", "platinum": "XPT"}
TROY_OZ_TO_GRAMS: float = 31.1035
MEMORY_CACHE_SECONDS: int = 6 * 3600   # 6 hours
DB_CACHE_SECONDS: int = 12 * 3600      # 12 hours

# ---------------------------------------------------------------------------
# In-memory rate cache (keyed per metal)
# ---------------------------------------------------------------------------
_rate_cache: dict[str, dict] = {}  # metal_type -> {purities..., source, fetched_at}
_rate_cache_ts: dict[str, float] = {}  # metal_type -> epoch timestamp


# ===================================================================
# Pure functions
# ===================================================================

def compute_purity_rates(metal_type: str, pure_rate_per_gram: float) -> dict[str, float]:
    """Derive per-purity rates from the pure (highest) rate for a given metal.

    Returns a dict keyed by purity label (e.g. "24K", "22K", "18K" for gold).
    All values are rounded to 2 decimal places.
    """
    factors = PURITY_FACTORS[metal_type]
    return {
        purity: round(pure_rate_per_gram * factor, 2)
        for purity, factor in factors.items()
    }


def is_rate_sane(metal_type: str, pure_rate: float) -> bool:
    """Check if a fetched rate is within plausible INR/gram bounds for the metal."""
    low, high = SANITY_BOUNDS[metal_type]
    return low <= pure_rate <= high


def _toz_to_gram(price_per_toz: float) -> float:
    """Convert price per troy ounce to price per gram."""
    return price_per_toz / TROY_OZ_TO_GRAMS


def _is_rate_stale(fetched_at_str: str, threshold_seconds: int = MEMORY_CACHE_SECONDS) -> bool:
    """Check if a cached rate is older than the threshold."""
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age_seconds > threshold_seconds
    except Exception:
        return True


# ===================================================================
# Rate Fetching: Primary (Metals.dev /v1/latest)
# ===================================================================

def _fetch_from_metals_dev() -> Optional[dict[str, dict]]:
    """Call Metals.dev /v1/latest API. Returns all three metals in one call.

    Returns dict keyed by metal_type, each value containing purity rates + metadata.
    Returns None on failure.
    """
    settings = get_settings()
    if not settings.gold_api_key:
        logger.warning("GOLD_API_KEY not configured, skipping Metals.dev")
        return None

    try:
        url = "https://api.metals.dev/v1/latest"
        params = {
            "api_key": settings.gold_api_key,
            "currency": "INR",
        }
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
        resp.raise_for_status()
        body = resp.json()

        if body.get("status") != "success" or body.get("currency") != "INR":
            logger.error("Metals.dev unexpected response: %s", body)
            return None

        metals_data = body.get("metals", {})
        now_iso = datetime.now(timezone.utc).isoformat()
        result: dict[str, dict] = {}

        for metal_type in METAL_TYPES:
            price_toz = metals_data.get(metal_type)
            if price_toz is None:
                logger.warning("Metals.dev missing price for %s", metal_type)
                continue

            pure_rate = _toz_to_gram(float(price_toz))

            if not is_rate_sane(metal_type, pure_rate):
                logger.error(
                    "Metals.dev %s rate outside sane range: %.2f INR/gram (expected %s-%s)",
                    metal_type, pure_rate, *SANITY_BOUNDS[metal_type],
                )
                continue

            rates = compute_purity_rates(metal_type, pure_rate)
            rates["source"] = "metals.dev"
            rates["fetched_at"] = now_iso
            result[metal_type] = rates

        return result if result else None
    except Exception as e:
        logger.error("Metals.dev API call failed: %s", e)
        return None


# ===================================================================
# Rate Fetching: Fallback (GoldAPI.io per-metal)
# ===================================================================

def _fetch_single_from_goldapi(metal_type: str) -> Optional[dict]:
    """Call GoldAPI.io for a single metal. Returns rate dict or None."""
    settings = get_settings()
    if not settings.gold_api_key_fallback:
        logger.warning("GOLD_API_KEY_FALLBACK not configured, skipping GoldAPI.io")
        return None

    symbol = GOLDAPI_SYMBOLS[metal_type]
    try:
        url = f"https://www.goldapi.io/api/{symbol}/INR"
        headers = {"x-access-token": settings.gold_api_key_fallback}
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
        resp.raise_for_status()
        body = resp.json()

        # GoldAPI.io provides per-gram rates for gold; for others use toz conversion
        if metal_type == "gold":
            pure_rate = float(body.get("price_gram_24k", 0))
        else:
            # For silver/platinum, GoldAPI returns price per troy ounce
            price_toz = float(body.get("price", 0))
            pure_rate = _toz_to_gram(price_toz) if price_toz > 0 else 0

        if pure_rate <= 0:
            logger.error("GoldAPI.io returned invalid rate for %s: %s", metal_type, body)
            return None

        if not is_rate_sane(metal_type, pure_rate):
            logger.error(
                "GoldAPI.io %s rate outside sane range: %.2f INR/gram (expected %s-%s)",
                metal_type, pure_rate, *SANITY_BOUNDS[metal_type],
            )
            return None

        rates = compute_purity_rates(metal_type, pure_rate)
        rates["source"] = "goldapi.io"
        rates["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return rates
    except Exception as e:
        logger.error("GoldAPI.io API call failed for %s: %s", metal_type, e)
        return None


def _fetch_from_goldapi() -> Optional[dict[str, dict]]:
    """Call GoldAPI.io for all metals as fallback. Returns dict keyed by metal_type."""
    result: dict[str, dict] = {}
    for metal_type in METAL_TYPES:
        rates = _fetch_single_from_goldapi(metal_type)
        if rates is not None:
            result[metal_type] = rates
    return result if result else None


# ===================================================================
# DB Cache: Read / Write / Cleanup
# ===================================================================

def _get_db_cached_rates() -> Optional[dict[str, dict]]:
    """Read the latest rates for each metal from precious_metal_rate_cache.

    Uses the anon client (no RLS on cache tables).
    """
    try:
        client = get_anon_client()
        result: dict[str, dict] = {}

        for metal_type in METAL_TYPES:
            response = (
                client.table("precious_metal_rate_cache")
                .select("*")
                .eq("metal_type", metal_type)
                .order("fetched_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                row = response.data[0]
                # Reconstruct purity rates from normalized row
                purities = PURITY_FACTORS[metal_type]
                rates = {}
                for purity_key in purities:
                    col_name = f"rate_{purity_key.lower()}"
                    if col_name in row:
                        rates[purity_key] = float(row[col_name])

                # Fallback: use rate_per_gram with purity factors
                if not rates and "rate_per_gram" in row:
                    pure_rate = float(row["rate_per_gram"])
                    rates = compute_purity_rates(metal_type, pure_rate)

                if rates:
                    rates["source"] = row.get("source", "db_cache")
                    rates["fetched_at"] = row.get("fetched_at", "")
                    result[metal_type] = rates

        return result if result else None
    except Exception as e:
        logger.error("Could not read precious metal rate cache: %s", e)
        return None


def _save_db_cached_rates(all_rates: dict[str, dict]) -> None:
    """Persist fresh rates into precious_metal_rate_cache.

    Uses the anon client (no RLS on cache tables).
    """
    try:
        client = get_anon_client()
        for metal_type, rates in all_rates.items():
            pure_purity = PURE_PURITY[metal_type]
            pure_rate = rates.get(pure_purity, 0)
            row = {
                "metal_type": metal_type,
                "purity": pure_purity,
                "rate_per_gram": pure_rate,
                "source": rates.get("source", "unknown"),
                "fetched_at": rates.get("fetched_at", datetime.now(timezone.utc).isoformat()),
            }
            client.table("precious_metal_rate_cache").insert(row).execute()
    except Exception as e:
        logger.warning("Could not persist precious metal rates to cache (non-blocking): %s", e)


def _cleanup_old_cache_rows() -> None:
    """Delete precious_metal_rate_cache rows older than 90 days."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        client = get_anon_client()
        client.table("precious_metal_rate_cache").delete().lt("fetched_at", cutoff).execute()
    except Exception as e:
        logger.warning("Cache cleanup failed (non-blocking): %s", e)


# ===================================================================
# 3-Tier Rate Fetching (memory -> DB -> API)
# ===================================================================

def fetch_rates(metal_type: Optional[str] = None) -> Optional[dict[str, dict]]:
    """3-tier cache: in-memory -> DB cache -> external API.

    If metal_type is specified, returns rates for that metal only.
    Otherwise returns rates for all available metals.

    Returns dict keyed by metal_type, each containing:
        {purity_label: rate, ..., source, fetched_at, is_stale}

    Returns None only if absolutely no rate is available.
    """
    global _rate_cache, _rate_cache_ts

    metals_to_fetch = (metal_type,) if metal_type else METAL_TYPES
    now = time.time()

    # --- Tier 1: In-memory cache ---
    all_cached = True
    result: dict[str, dict] = {}
    for m in metals_to_fetch:
        if m in _rate_cache and (now - _rate_cache_ts.get(m, 0)) < MEMORY_CACHE_SECONDS:
            result[m] = {
                **_rate_cache[m],
                "is_stale": _is_rate_stale(_rate_cache[m].get("fetched_at", "")),
            }
        else:
            all_cached = False
            break

    if all_cached and result:
        return result

    # --- Tier 2: DB cache ---
    db_rates = _get_db_cached_rates()
    if db_rates:
        all_fresh = True
        for m in metals_to_fetch:
            if m not in db_rates:
                all_fresh = False
                break
            fetched_at = db_rates[m].get("fetched_at", "")
            if _is_rate_stale(fetched_at, DB_CACHE_SECONDS):
                all_fresh = False
                break

        if all_fresh:
            # Refresh in-memory cache from DB
            for m in metals_to_fetch:
                _rate_cache[m] = db_rates[m]
                _rate_cache_ts[m] = now
            return {
                m: {**db_rates[m], "is_stale": False}
                for m in metals_to_fetch
                if m in db_rates
            }

    # --- Tier 3: External API call ---
    # Try primary: Metals.dev /v1/latest (single call for all metals)
    api_rates = _fetch_from_metals_dev()

    # Try fallback: GoldAPI.io (per-metal calls)
    if api_rates is None:
        api_rates = _fetch_from_goldapi()

    if api_rates:
        # Update both caches for fetched metals
        for m, rates in api_rates.items():
            _rate_cache[m] = rates
            _rate_cache_ts[m] = now
        _save_db_cached_rates(api_rates)
        _cleanup_old_cache_rows()

        filtered = {
            m: {**api_rates[m], "is_stale": False}
            for m in metals_to_fetch
            if m in api_rates
        }
        if filtered:
            return filtered

    # --- Fallback: Return stale DB cache ---
    if db_rates:
        for m in metals_to_fetch:
            if m in db_rates:
                _rate_cache[m] = db_rates[m]
                _rate_cache_ts[m] = now
        stale_result = {
            m: {**db_rates[m], "is_stale": True}
            for m in metals_to_fetch
            if m in db_rates
        }
        if stale_result:
            return stale_result

    # --- No rate available at all ---
    return None


# ===================================================================
# CRUD: Precious Metal Purchases
# ===================================================================

TABLE = "precious_metal_purchases"


def load_purchases(
    user_id: str,
    access_token: str,
    metal_type: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch precious metal purchases for the authenticated user.

    Optionally filter by metal_type. Returns rows ordered by purchase_date DESC.
    """
    try:
        client = get_user_client(access_token)
        query = client.table(TABLE).select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        if metal_type:
            query = query.eq("metal_type", metal_type)
        response = query.order("purchase_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load precious metal purchases: %s", e)
        raise DatabaseError("Could not load precious metal purchases") from e


def save_purchase(
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Insert a new precious metal purchase. total_cost is a generated column."""
    try:
        client = get_user_client(access_token)
        # Remove total_cost if present -- it is a generated column
        data.pop("total_cost", None)
        payload = {**data, "user_id": user_id}
        # Convert date to ISO string for JSON serialization
        if "purchase_date" in payload and hasattr(payload["purchase_date"], "isoformat"):
            payload["purchase_date"] = payload["purchase_date"].isoformat()
        response = client.table(TABLE).insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save precious metal purchase: %s", e)
        raise DatabaseError("Could not save precious metal purchase") from e


def update_purchase(
    purchase_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Partial update of a precious metal purchase. Rejects updates on deactivated rows."""
    try:
        client = get_user_client(access_token)
        # Remove total_cost if present -- it is a generated column
        data.pop("total_cost", None)
        # Convert date to ISO string if present
        if "purchase_date" in data and hasattr(data["purchase_date"], "isoformat"):
            data["purchase_date"] = data["purchase_date"].isoformat()
        response = (
            client.table(TABLE)
            .update(data)
            .eq("id", purchase_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Purchase not found or already deactivated")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update precious metal purchase: %s", e)
        raise DatabaseError("Could not update precious metal purchase") from e


def deactivate_purchase(
    purchase_id: str,
    user_id: str,
    access_token: str,
) -> Optional[dict]:
    """Soft-delete a precious metal purchase by setting is_active=false."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table(TABLE)
            .update({"is_active": False})
            .eq("id", purchase_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Purchase not found or already deactivated")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not deactivate precious metal purchase: %s", e)
        raise DatabaseError("Could not deactivate precious metal purchase") from e


# ===================================================================
# Portfolio Summary
# ===================================================================

def compute_portfolio_summary(
    user_id: str,
    access_token: str,
    metal_type: Optional[str] = None,
) -> Optional[dict]:
    """Aggregate precious metal holdings against live rates.

    Returns total weight, cost, current value, P&L, breakdowns by metal
    and by owner, and the rates used for computation.

    If metal_type is specified, only that metal's purchases are included.
    """
    purchases = load_purchases(user_id, access_token, metal_type=metal_type, active_only=True)
    all_rates = fetch_rates(metal_type=metal_type)

    if not purchases:
        return {
            "total_weight_grams": 0,
            "total_cost": 0,
            "current_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "by_metal": [],
            "by_owner": [],
            "rate_used": all_rates,
        }

    total_weight = 0.0
    total_cost = 0.0
    total_value = 0.0

    # Accumulators for breakdowns
    metal_agg: dict[str, dict] = {}  # metal -> {weight, cost, value}
    owner_agg: dict[str, dict] = {}  # owner -> {weight, cost, value}

    for p in purchases:
        w = float(p["weight_grams"])
        c = float(p["total_cost"])
        purity = p["purity"]
        owner = p["owner"]
        p_metal = p["metal_type"]

        # Look up current rate for this metal + purity
        current_rate = 0.0
        if all_rates and p_metal in all_rates:
            metal_rates = all_rates[p_metal]
            current_rate = metal_rates.get(purity, 0)
            # If purity key not found directly (unlikely), try to derive
            if current_rate == 0 and isinstance(current_rate, (int, float)):
                pure_key = PURE_PURITY.get(p_metal, "")
                pure_rate = metal_rates.get(pure_key, 0)
                factor = PURITY_FACTORS.get(p_metal, {}).get(purity, 0)
                current_rate = pure_rate * factor

        v = w * current_rate

        total_weight += w
        total_cost += c
        total_value += v

        # Metal breakdown
        if p_metal not in metal_agg:
            metal_agg[p_metal] = {"weight_grams": 0, "cost": 0, "value": 0}
        metal_agg[p_metal]["weight_grams"] += w
        metal_agg[p_metal]["cost"] += c
        metal_agg[p_metal]["value"] += v

        # Owner breakdown
        if owner not in owner_agg:
            owner_agg[owner] = {"weight_grams": 0, "cost": 0, "value": 0}
        owner_agg[owner]["weight_grams"] += w
        owner_agg[owner]["cost"] += c
        owner_agg[owner]["value"] += v

    total_pnl = total_value - total_cost
    total_pnl_pct = round((total_pnl / total_cost * 100), 2) if total_cost > 0 else 0

    by_metal = [
        {
            "metal": k,
            "weight_grams": round(v["weight_grams"], 3),
            "cost": round(v["cost"], 2),
            "value": round(v["value"], 2),
            "pnl": round(v["value"] - v["cost"], 2),
        }
        for k, v in metal_agg.items()
    ]

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

    return {
        "total_weight_grams": round(total_weight, 3),
        "total_cost": round(total_cost, 2),
        "current_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "by_metal": by_metal,
        "by_owner": by_owner,
        "rate_used": all_rates,
    }
