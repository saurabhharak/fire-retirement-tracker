"""Fixed expenses CRUD service."""
import logging
from typing import Optional
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

async def load_fixed_expenses(user_id: str, access_token: str, active_only: bool = True) -> list[dict]:
    try:
        client = get_user_client(access_token)
        query = client.table("fixed_expenses").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Could not load expenses: {e}")
        raise DatabaseError("Could not load expenses") from e

async def save_fixed_expense(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = client.table("fixed_expenses").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Could not save expense: {e}")
        raise DatabaseError("Could not save expense") from e

async def update_fixed_expense(expense_id: str, user_id: str, data: dict, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        response = (client.table("fixed_expenses").update(data)
            .eq("id", expense_id).eq("user_id", user_id).execute())
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Could not update expense: {e}")
        raise DatabaseError("Could not update expense") from e

async def deactivate_fixed_expense(expense_id: str, user_id: str, access_token: str) -> Optional[dict]:
    return await update_fixed_expense(expense_id, user_id, {"is_active": False}, access_token)
