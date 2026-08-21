"""Amul other business expenses CRUD service (rent, electricity, wages...)."""

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


def load_other_expenses(
    parlour_id: str,
    user_id: str,
    access_token: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch operating expenses for a parlour (membership required)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        query = client.table("amul_other_expenses").select("*")
        query = query.eq("parlour_id", parlour_id)
        if from_date:
            query = query.gte("expense_date", from_date)
        if to_date:
            query = query.lte("expense_date", to_date)
        if category:
            query = query.eq("category", category)
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("expense_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load other expenses: %s", e)
        raise DatabaseError("Could not load other expenses") from e


def save_other_expense(
    parlour_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Create an operating expense."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        payload = {**_serialize_dates(data), "parlour_id": parlour_id}
        response = client.table("amul_other_expenses").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save other expense: %s", e)
        raise DatabaseError("Could not save other expense") from e


def update_other_expense(
    expense_id: str,
    parlour_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Update an operating expense."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_other_expenses")
            .update(_serialize_dates(data))
            .eq("id", expense_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Other expense not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update other expense: %s", e)
        raise DatabaseError("Could not update other expense") from e


def delete_other_expense(
    expense_id: str, parlour_id: str, user_id: str, access_token: str
) -> None:
    """Delete an operating expense (hard delete; entries are granular)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        (
            client.table("amul_other_expenses")
            .delete()
            .eq("id", expense_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
    except Exception as e:
        logger.error("Could not delete other expense: %s", e)
        raise DatabaseError("Could not delete other expense") from e
