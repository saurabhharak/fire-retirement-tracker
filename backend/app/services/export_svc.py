"""Export and account data management service."""
import logging
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

def export_all_data(user_id: str, access_token: str) -> dict:
    """Export all user data from every table."""
    try:
        client = get_user_client(access_token)
        data = {
            "fire_inputs": client.table("fire_inputs").select("*").eq("user_id", user_id).execute().data,
            "income_entries": client.table("income_entries").select("*").eq("user_id", user_id).execute().data,
            "fixed_expenses": client.table("fixed_expenses").select("*").eq("user_id", user_id).execute().data,
            "sip_log": client.table("sip_log").select("*, sip_log_funds(*)").eq("user_id", user_id).execute().data,
        }
        return data
    except Exception as e:
        logger.error(f"Could not export data: {e}")
        raise DatabaseError("Could not export user data") from e

def delete_account_data(user_id: str, access_token: str) -> None:
    """Delete all user data from every table."""
    try:
        client = get_user_client(access_token)
        for table in ["sip_log", "income_entries", "fixed_expenses", "fire_inputs", "audit_log"]:
            client.table(table).delete().eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Could not delete account data: {e}")
        raise DatabaseError("Could not delete account data") from e
