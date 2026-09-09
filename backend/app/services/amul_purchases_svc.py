"""Amul daily purchases CRUD service (manual day-by-day purchase totals)."""

import logging
from datetime import date as date_type
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services import parlours_svc
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _serialize_dates(data: dict) -> dict:
    return {k: v.isoformat() if isinstance(v, date_type) else v for k, v in data.items()}


def _verify_membership(parlour_id: str, user_id: str, access_token: str) -> str:
    return parlours_svc._verify_parlour_membership(parlour_id, user_id, access_token)


def load_daily_purchases(
    parlour_id: str,
    user_id: str,
    access_token: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list[dict]:
    """Fetch daily purchases for a parlour (membership required)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        query = client.table("amul_daily_purchases").select("*")
        query = query.eq("parlour_id", parlour_id)
        if from_date:
            query = query.gte("purchase_date", from_date)
        if to_date:
            query = query.lte("purchase_date", to_date)
        response = query.order("purchase_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load daily purchases: %s", e)
        raise DatabaseError("Could not load daily purchases") from e


def save_daily_purchase(
    parlour_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Create or update a daily purchase entry (idempotent per parlour+date)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        payload = {
            **_serialize_dates(data),
            "parlour_id": parlour_id,
            "entered_by": user_id,
        }
        response = (
            client.table("amul_daily_purchases")
            .upsert(payload, on_conflict="parlour_id,purchase_date")
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save daily purchase: %s", e)
        raise DatabaseError("Could not save daily purchase") from e


def update_daily_purchase(
    purchase_id: str,
    parlour_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Update a daily purchase."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_daily_purchases")
            .update(_serialize_dates(data))
            .eq("id", purchase_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Daily purchase not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update daily purchase: %s", e)
        raise DatabaseError("Could not update daily purchase") from e


def delete_daily_purchase(
    purchase_id: str, parlour_id: str, user_id: str, access_token: str
) -> None:
    """Delete a daily purchase."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        (
            client.table("amul_daily_purchases")
            .delete()
            .eq("id", purchase_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
    except Exception as e:
        logger.error("Could not delete daily purchase: %s", e)
        raise DatabaseError("Could not delete daily purchase") from e
