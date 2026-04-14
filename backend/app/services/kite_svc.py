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
        raise ExternalServiceError("Could not initiate Kite login") from e

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

    If state is empty (Kite personal apps may not forward it), falls back
    to finding the most recent unexpired nonce to identify the user.
    """
    settings = get_settings()
    client = get_service_client()

    if state:
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
    else:
        # Fallback: Kite personal apps may not forward state param.
        # Find the most recent unexpired nonce to identify the user.
        try:
            nonce_result = (
                client.table("kite_oauth_nonces")
                .select("nonce, user_id")
                .gt("expires_at", datetime.now(timezone.utc).isoformat())
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not nonce_result.data:
                raise ExternalServiceError("No pending authorization found. Please try again.")
            user_id = nonce_result.data[0]["user_id"]
            nonce = nonce_result.data[0]["nonce"]
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.error("Nonce lookup failed: %s", type(e).__name__)
            raise ExternalServiceError("Authorization failed. Please try again.")

    # Verify nonce is unused (one-time use) and consume it
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
        raise ExternalServiceError("Authorization verification failed.") from e

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
        raise ExternalServiceError("Could not save Kite connection.") from e

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
        raise ExternalServiceError("Could not disconnect Kite.") from e


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

    # Build fund name lookup from SIP data (SIPs always have fund names)
    fund_name_lookup: dict[str, str] = {}
    for sip in raw_sips:
        ts = sip.get("tradingsymbol", "")
        name = sip.get("fund", "")
        if ts and name:
            fund_name_lookup[ts] = name

    # Process holdings + merge SIP data
    holdings = []
    total_invested = 0.0
    total_current = 0.0
    total_pnl = 0.0

    for h in raw_holdings:
        qty = float(h.get("quantity", 0))
        avg = float(h.get("average_price", 0))
        last = float(h.get("last_price", 0))
        invested = round(avg * qty, 2)
        current_value = round(last * qty, 2)
        # Compute P&L ourselves — Kite API often returns pnl=0 even when values differ
        pnl = round(current_value - invested, 2)
        pnl_pct = round((pnl / invested) * 100, 2) if invested > 0 else 0.0

        total_invested += invested
        total_current += current_value
        total_pnl += pnl

        # Merge SIP info
        ts = h.get("tradingsymbol", "")
        sip = sip_lookup.get(ts)

        # Resolve fund name: holdings > SIP data > tradingsymbol
        fund_name = h.get("fund", "") or fund_name_lookup.get(ts, "") or ts

        holdings.append({
            "fund": fund_name,
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
