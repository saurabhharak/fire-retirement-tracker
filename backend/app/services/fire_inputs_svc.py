"""FIRE inputs CRUD service."""
import logging
from typing import Optional
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

# Mapping: API field name -> DB column name
# The DB schema uses "gold_return"/"gold_pct" but the API model uses
# "precious_metals_return"/"precious_metals_pct".
_API_TO_DB = {
    "precious_metals_return": "gold_return",
    "precious_metals_pct": "gold_pct",
}
_DB_TO_API = {v: k for k, v in _API_TO_DB.items()}


def _to_db(data: dict) -> dict:
    """Rename API field names to DB column names."""
    return {_API_TO_DB.get(k, k): v for k, v in data.items()}


def _to_api(row: dict) -> dict:
    """Rename DB column names to API field names."""
    return {_DB_TO_API.get(k, k): v for k, v in row.items()}


def load_fire_inputs(user_id: str, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        response = client.table("fire_inputs").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            return _to_api(response.data[0])
        return None
    except Exception as e:
        logger.error("Could not load fire inputs: %s", e)
        raise DatabaseError("Could not load FIRE settings") from e

def save_fire_inputs(user_id: str, data: dict, access_token: str) -> dict:
    try:
        client = get_user_client(access_token)
        payload = _to_db({**data, "user_id": user_id})
        response = client.table("fire_inputs").upsert(payload, on_conflict="user_id").execute()
        if response.data:
            return _to_api(response.data[0])
        raise DatabaseError("No data returned after save")
    except DatabaseError:
        raise
    except Exception as e:
        logger.error("Could not save fire inputs: %s", e)
        raise DatabaseError("Could not save FIRE settings") from e
