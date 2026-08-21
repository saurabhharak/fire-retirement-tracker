"""Amul daily sales CRUD service (WhatsApp cash + online)."""

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


def load_daily_sales(
    parlour_id: str,
    user_id: str,
    access_token: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list[dict]:
    """Fetch daily sales for a parlour (membership required)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        query = client.table("amul_daily_sales").select("*")
        query = query.eq("parlour_id", parlour_id)
        if from_date:
            query = query.gte("sale_date", from_date)
        if to_date:
            query = query.lte("sale_date", to_date)
        response = query.order("sale_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load daily sales: %s", e)
        raise DatabaseError("Could not load daily sales") from e


def save_daily_sale(
    parlour_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Create or update a daily sales entry (idempotent per parlour+date).

    Uses upsert on (parlour_id, sale_date) so importing the same day twice
    updates the amounts instead of inserting a duplicate row.
    """
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        payload = {
            **_serialize_dates(data),
            "parlour_id": parlour_id,
            "entered_by": user_id,
        }
        response = (
            client.table("amul_daily_sales")
            .upsert(payload, on_conflict="parlour_id,sale_date")
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save daily sale: %s", e)
        raise DatabaseError("Could not save daily sale") from e


def update_daily_sale(
    sale_id: str,
    parlour_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Update a daily sale."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_daily_sales")
            .update(_serialize_dates(data))
            .eq("id", sale_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Daily sale not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update daily sale: %s", e)
        raise DatabaseError("Could not update daily sale") from e


def delete_daily_sale(
    sale_id: str, parlour_id: str, user_id: str, access_token: str
) -> None:
    """Delete a daily sale."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        (
            client.table("amul_daily_sales")
            .delete()
            .eq("id", sale_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
    except Exception as e:
        logger.error("Could not delete daily sale: %s", e)
        raise DatabaseError("Could not delete daily sale") from e
