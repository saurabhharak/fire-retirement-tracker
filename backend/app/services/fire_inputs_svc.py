"""FIRE inputs CRUD service."""
import logging
from typing import Optional
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

def load_fire_inputs(user_id: str, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        response = client.table("fire_inputs").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Could not load fire inputs: %s", e)
        raise DatabaseError("Could not load FIRE settings") from e

def save_fire_inputs(user_id: str, data: dict, access_token: str) -> dict:
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = client.table("fire_inputs").upsert(payload, on_conflict="user_id").execute()
        if response.data:
            return response.data[0]
        raise DatabaseError("No data returned after save")
    except DatabaseError:
        raise
    except Exception as e:
        logger.error("Could not save fire inputs: %s", e)
        raise DatabaseError("Could not save FIRE settings") from e
