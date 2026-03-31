"""Audit logging service."""
import logging
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

def log_audit(user_id: str, action: str, details: dict = None, access_token: str = "") -> None:
    try:
        client = get_user_client(access_token) if access_token else None
        if client:
            client.table("audit_log").insert({"user_id": user_id, "action": action, "details": details}).execute()
    except Exception as e:
        logger.warning("Audit log failed (non-blocking): %s", e)
