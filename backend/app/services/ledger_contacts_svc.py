"""Ledger contacts CRUD + balance computation service."""
import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _compute_balance_label(balance: float) -> str:
    if balance > 0:
        return "owes you"
    if balance < 0:
        return "you owe"
    return "settled"


def load_contacts(
    user_id: str,
    access_token: str,
    active_only: bool = True,
) -> list[dict]:
    """Fetch all contacts for the user with computed balances."""
    try:
        client = get_user_client(access_token)
        query = client.table("ledger_contacts").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("name").execute()
        contacts = response.data or []

        # Compute balance for each contact
        for contact in contacts:
            txn_resp = (
                client.table("ledger_transactions")
                .select("direction, amount")
                .eq("contact_id", contact["id"])
                .execute()
            )
            txns = txn_resp.data or []
            total_gave = sum(float(t["amount"]) for t in txns if t["direction"] == "gave")
            total_received = sum(float(t["amount"]) for t in txns if t["direction"] == "received")
            balance = total_gave - total_received
            contact["total_gave"] = round(total_gave, 2)
            contact["total_received"] = round(total_received, 2)
            contact["balance"] = round(balance, 2)
            contact["balance_label"] = _compute_balance_label(balance)

        return contacts
    except Exception as e:
        logger.error("Could not load contacts: %s", e)
        raise DatabaseError("Could not load contacts") from e


def save_contact(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    """Create a new ledger contact."""
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = client.table("ledger_contacts").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save contact: %s", e)
        raise DatabaseError("Could not save contact") from e


def update_contact(
    contact_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a ledger contact by ID."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("ledger_contacts")
            .update(data)
            .eq("id", contact_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Contact not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update contact: %s", e)
        raise DatabaseError("Could not update contact") from e


def deactivate_contact(contact_id: str, user_id: str, access_token: str) -> None:
    """Soft-delete a contact by setting is_active=false."""
    update_contact(contact_id, user_id, {"is_active": False}, access_token)


def compute_summary(user_id: str, access_token: str) -> dict:
    """Aggregate total_gave, total_received, net_balance, people_count across all contacts."""
    try:
        client = get_user_client(access_token)
        # Fetch all active contacts for this user
        contacts_resp = (
            client.table("ledger_contacts")
            .select("id")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        contacts = contacts_resp.data or []
        contact_ids = [c["id"] for c in contacts]

        total_gave = 0.0
        total_received = 0.0

        if contact_ids:
            # Fetch all transactions for these contacts
            txn_resp = (
                client.table("ledger_transactions")
                .select("direction, amount, contact_id")
                .in_("contact_id", contact_ids)
                .execute()
            )
            txns = txn_resp.data or []
            total_gave = sum(float(t["amount"]) for t in txns if t["direction"] == "gave")
            total_received = sum(float(t["amount"]) for t in txns if t["direction"] == "received")

        net_balance = total_gave - total_received
        return {
            "total_gave": round(total_gave, 2),
            "total_received": round(total_received, 2),
            "net_balance": round(net_balance, 2),
            "people_count": len(contact_ids),
        }
    except Exception as e:
        logger.error("Could not compute summary: %s", e)
        raise DatabaseError("Could not compute summary") from e
