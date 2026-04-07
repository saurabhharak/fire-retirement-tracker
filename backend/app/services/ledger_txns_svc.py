"""Ledger transactions CRUD service."""
import logging
from datetime import date as date_type
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _serialize_dates(data: dict) -> dict:
    """Convert date objects to ISO strings for Supabase JSON serialization."""
    return {k: v.isoformat() if isinstance(v, date_type) else v for k, v in data.items()}


def _verify_contact_ownership(contact_id: str, user_id: str, client) -> None:
    """Check that contact_id belongs to user_id. Raises DataNotFoundError if not."""
    response = (
        client.table("ledger_contacts")
        .select("id")
        .eq("id", contact_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise DataNotFoundError("Contact not found")


def load_transactions(
    user_id: str,
    access_token: str,
    contact_id: Optional[str] = None,
) -> list[dict]:
    """Fetch transactions for a contact, ordered by date descending."""
    try:
        client = get_user_client(access_token)
        if contact_id:
            _verify_contact_ownership(contact_id, user_id, client)

        query = client.table("ledger_transactions").select("*")
        if contact_id:
            query = query.eq("contact_id", contact_id)
        response = query.order("date", desc=True).execute()
        return response.data or []
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not load transactions: %s", e)
        raise DatabaseError("Could not load transactions") from e


def save_transaction(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    """Create a new ledger transaction. Verifies contact ownership first."""
    try:
        client = get_user_client(access_token)
        _verify_contact_ownership(data["contact_id"], user_id, client)
        response = client.table("ledger_transactions").insert(_serialize_dates(data)).execute()
        return response.data[0] if response.data else None
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not save transaction: %s", e)
        raise DatabaseError("Could not save transaction") from e


def update_transaction(
    txn_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a ledger transaction by ID. Verifies ownership via contact join."""
    try:
        client = get_user_client(access_token)
        # Fetch existing transaction to get contact_id
        existing = (
            client.table("ledger_transactions")
            .select("contact_id")
            .eq("id", txn_id)
            .execute()
        )
        if not existing.data:
            raise DataNotFoundError("Transaction not found")
        _verify_contact_ownership(existing.data[0]["contact_id"], user_id, client)
        response = (
            client.table("ledger_transactions")
            .update(_serialize_dates(data))
            .eq("id", txn_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Transaction not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update transaction: %s", e)
        raise DatabaseError("Could not update transaction") from e


def delete_transaction(txn_id: str, user_id: str, access_token: str) -> None:
    """Hard-delete a ledger transaction. Verifies ownership via contact join."""
    try:
        client = get_user_client(access_token)
        # Verify ownership via contact join
        existing = (
            client.table("ledger_transactions")
            .select("contact_id")
            .eq("id", txn_id)
            .execute()
        )
        if not existing.data:
            raise DataNotFoundError("Transaction not found")
        _verify_contact_ownership(existing.data[0]["contact_id"], user_id, client)
        client.table("ledger_transactions").delete().eq("id", txn_id).execute()
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not delete transaction: %s", e)
        raise DatabaseError("Could not delete transaction") from e
