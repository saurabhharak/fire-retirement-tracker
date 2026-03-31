"""Income entries CRUD service."""
import logging
from typing import Optional
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

def load_income_entries(user_id: str, access_token: str, limit: int = 12) -> list[dict]:
    try:
        client = get_user_client(access_token)
        response = (client.table("income_entries").select("*")
            .eq("user_id", user_id).order("year", desc=True)
            .order("month", desc=True).limit(limit).execute())
        return response.data or []
    except Exception as e:
        logger.error(f"Could not load income entries: {e}")
        raise DatabaseError("Could not load income entries") from e

def save_income_entry(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = (client.table("income_entries")
            .upsert(payload, on_conflict="user_id,month,year").execute())
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Could not save income entry: {e}")
        raise DatabaseError("Could not save income entry") from e

def delete_income_entry(user_id: str, month: int, year: int, access_token: str) -> bool:
    try:
        client = get_user_client(access_token)
        client.table("income_entries").delete().eq("user_id", user_id).eq("month", month).eq("year", year).execute()
        return True
    except Exception as e:
        logger.error(f"Could not delete income entry: {e}")
        raise DatabaseError("Could not delete income entry") from e
