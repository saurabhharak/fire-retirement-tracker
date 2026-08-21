"""Export and account data management service."""
import logging
from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)

# Tables keyed directly by user_id. Child rows (sip_log_funds,
# project_expenses, ledger_transactions) cascade via FK ON DELETE CASCADE.
_USER_TABLES = [
    "sip_log",
    "income_entries",
    "fixed_expenses",
    "fire_inputs",
    "precious_metal_purchases",
    "projects",
    "ledger_contacts",
    "kite_sessions",          # stored Zerodha tokens MUST be removed
    "mf_portfolio_snapshots",
]

# Audit trail is exported but intentionally NOT deleted: it is the
# tamper-evidence record for a finance app (and has no DELETE policy in RLS).
_EXPORT_ONLY_TABLES = ["audit_log"]


def export_all_data(user_id: str, access_token: str) -> dict:
    """Export all personal user data from every table."""
    try:
        client = get_user_client(access_token)
        data = {
            table: client.table(table).select("*").eq("user_id", user_id).execute().data
            for table in _USER_TABLES + _EXPORT_ONLY_TABLES
        }
        data["parlours_owned"] = (
            client.table("parlours").select("*").eq("owner_id", user_id).execute().data
        )
        data["parlour_memberships"] = (
            client.table("parlour_members").select("*").eq("member_id", user_id).execute().data
        )
        return data
    except Exception as e:
        logger.error("Could not export data: %s", e)
        raise DatabaseError("Could not export user data") from e

def delete_account_data(user_id: str, access_token: str) -> None:
    """Delete all personal user data.

    Covers every user-keyed table plus parlours the user owns (which cascade
    to members, daily sales, invoices/items, other expenses and Sarvam usage
    via FK ON DELETE CASCADE) and the user's own memberships. Rows the user
    entered into OTHER owners' parlours are that parlour's business records
    and are kept; entered_by is anonymized when the auth account is removed.
    """
    try:
        client = get_user_client(access_token)
        for table in _USER_TABLES:
            client.table(table).delete().eq("user_id", user_id).execute()
        client.table("parlours").delete().eq("owner_id", user_id).execute()
        client.table("parlour_members").delete().eq("member_id", user_id).execute()
    except Exception as e:
        logger.error("Could not delete account data: %s", e)
        raise DatabaseError("Could not delete account data") from e
