"""SIP log CRUD service."""
import logging
from typing import Optional
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

def load_sip_logs(user_id: str, access_token: str, limit: int = 60) -> list[dict]:
    try:
        client = get_user_client(access_token)
        response = (client.table("sip_log").select("*, sip_log_funds(*)")
            .eq("user_id", user_id).order("year", desc=True)
            .order("month", desc=True).limit(limit).execute())
        return response.data or []
    except Exception as e:
        logger.error("Could not load SIP logs: %s", e)
        raise DatabaseError("Could not load SIP logs") from e

def save_sip_log(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    try:
        client = get_user_client(access_token)
        payload_data = dict(data)
        funds = payload_data.pop("funds", [])
        payload = {**payload_data, "user_id": user_id}
        response = (client.table("sip_log")
            .upsert(payload, on_conflict="user_id,month,year").execute())
        sip_log_row = response.data[0] if response.data else None
        if sip_log_row and funds:
            sip_log_id = sip_log_row["id"]
            client.table("sip_log_funds").delete().eq("sip_log_id", sip_log_id).execute()
            fund_rows = [{"sip_log_id": sip_log_id, "fund_name": f["fund_name"], "amount": f["amount"]} for f in funds]
            client.table("sip_log_funds").insert(fund_rows).execute()
        return sip_log_row
    except Exception as e:
        logger.error("Could not save SIP log: %s", e)
        raise DatabaseError("Could not save SIP log") from e
