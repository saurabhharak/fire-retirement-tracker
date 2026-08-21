"""Sarvam usage / spend-tracking read service (owner-only)."""

import logging
from typing import Optional

from app.exceptions import DatabaseError, ForbiddenError
from app.core.business_engine import compute_sarvam_balance
from app.services import parlours_svc
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _require_owner(parlour_id: str, user_id: str, access_token: str) -> None:
    role = parlours_svc._verify_parlour_membership(parlour_id, user_id, access_token)
    if role != "owner":
        raise ForbiddenError("Owner role required to view Sarvam spend")


def load_usage(
    parlour_id: str,
    user_id: str,
    access_token: str,
    from_date: Optional[str] = None,
) -> list[dict]:
    """Fetch Sarvam usage rows (owner only)."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        query = client.table("sarvam_usage").select("*").eq("parlour_id", parlour_id)
        if from_date:
            query = query.gte("created_at", from_date)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load Sarvam usage: %s", e)
        raise DatabaseError("Could not load Sarvam usage") from e


def get_spend_summary(
    parlour_id: str, user_id: str, access_token: str
) -> dict:
    """Return starting/used/remaining credits + call count (owner only)."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        parlour_resp = (
            client.table("parlours")
            .select("sarvam_starting_credits")
            .eq("id", parlour_id)
            .execute()
        )
        starting = float(parlour_resp.data[0]["sarvam_starting_credits"]) if parlour_resp.data else 0.0
        usage_resp = (
            client.table("sarvam_usage")
            .select("credits_used,cost_estimate_inr")
            .eq("parlour_id", parlour_id)
            .execute()
        )
        return compute_sarvam_balance(starting, usage_resp.data or [])
    except Exception as e:
        logger.error("Could not compute Sarvam spend summary: %s", e)
        raise DatabaseError("Could not compute Sarvam spend summary") from e
