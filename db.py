"""
Supabase CRUD module for the FIRE Retirement Tracker.

All functions handle errors with try/except and return None on failure
or raise descriptive errors where appropriate.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the .env file."
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
# NOTE: This client is shared across all sessions via @st.cache_resource.
# supabase-py v2+ scopes auth per-request using the JWT passed with each call.
# RLS enforcement depends on the auth.uid() from the request JWT, not client state.
# For a single-user personal app this is safe. For multi-user, consider per-session clients.
@st.cache_resource
def get_supabase_client() -> Client:
    """Return a cached Supabase client instance."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# fire_inputs
# ---------------------------------------------------------------------------
def load_fire_inputs(user_id: str) -> Optional[dict]:
    """Load the FIRE settings row for a given user.

    Returns the row as a dict, or None if no row exists or on error.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("fire_inputs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logging.error(f"Could not load FIRE inputs: {e}")
        st.error("Could not load FIRE inputs. Please try again.")
        return None


def save_fire_inputs(user_id: str, data: dict) -> Optional[dict]:
    """Upsert (insert or update) the FIRE settings row for a user.

    ``data`` should contain all fire_inputs columns except user_id and
    updated_at (which are set automatically).

    Returns the upserted row dict, or None on error.
    """
    try:
        client = get_supabase_client()
        payload = {**data, "user_id": user_id}
        response = (
            client.table("fire_inputs")
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Could not save FIRE inputs: {e}")
        st.error("Could not save FIRE inputs. Please try again.")
        return None


# ---------------------------------------------------------------------------
# income_entries
# ---------------------------------------------------------------------------
def load_income_entries(user_id: str, limit: int = 12) -> list[dict]:
    """Load the most recent income entries for a user.

    Returns a list of dicts ordered by year desc, month desc.
    Returns an empty list on error.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("income_entries")
            .select("*")
            .eq("user_id", user_id)
            .order("year", desc=True)
            .order("month", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logging.error(f"Could not load income entries: {e}")
        st.error("Could not load income entries. Please try again.")
        return []


def save_income_entry(user_id: str, data: dict) -> Optional[dict]:
    """Upsert an income entry on the (user_id, month, year) unique key.

    ``data`` must include month, year, your_income, wife_income, and
    optionally notes.

    Returns the upserted row dict, or None on error.
    """
    try:
        client = get_supabase_client()
        payload = {**data, "user_id": user_id}
        response = (
            client.table("income_entries")
            .upsert(payload, on_conflict="user_id,month,year")
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Could not save income entry: {e}")
        st.error("Could not save income entry. Please try again.")
        return None


# ---------------------------------------------------------------------------
# fixed_expenses
# ---------------------------------------------------------------------------
def load_fixed_expenses(
    user_id: str, active_only: bool = True
) -> list[dict]:
    """Load fixed expenses for a user.

    When *active_only* is True (default), only rows with
    ``is_active = true`` are returned.

    Returns a list of dicts, or an empty list on error.
    """
    try:
        client = get_supabase_client()
        query = (
            client.table("fixed_expenses")
            .select("*")
            .eq("user_id", user_id)
        )
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logging.error(f"Could not load fixed expenses: {e}")
        st.error("Could not load fixed expenses. Please try again.")
        return []


def save_fixed_expense(user_id: str, data: dict) -> Optional[dict]:
    """Insert a new fixed expense row.

    ``data`` must include name, amount, and frequency.

    Returns the inserted row dict, or None on error.
    """
    try:
        client = get_supabase_client()
        payload = {**data, "user_id": user_id}
        response = (
            client.table("fixed_expenses")
            .insert(payload)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Could not save fixed expense: {e}")
        st.error("Could not save fixed expense. Please try again.")
        return None


def update_fixed_expense(expense_id: str, user_id: str, data: dict) -> Optional[dict]:
    """Update an existing fixed expense by its id.

    ``data`` may contain any subset of updatable columns (name, amount,
    frequency, is_active).  The ``user_id`` filter ensures a user can
    only modify their own expenses.

    Returns the updated row dict, or None on error.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("fixed_expenses")
            .update(data)
            .eq("id", expense_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Could not update fixed expense: {e}")
        st.error("Could not update fixed expense. Please try again.")
        return None


def deactivate_fixed_expense(expense_id: str, user_id: str) -> Optional[dict]:
    """Soft-delete a fixed expense by setting is_active = false.

    The ``user_id`` filter ensures a user can only deactivate their own
    expenses.

    Returns the updated row dict, or None on error.
    """
    return update_fixed_expense(expense_id, user_id, {"is_active": False})


# ---------------------------------------------------------------------------
# sip_log
# ---------------------------------------------------------------------------
def load_sip_logs(user_id: str, limit: int = 60) -> list[dict]:
    """Load SIP log entries for a user.

    Returns a list of dicts ordered by year desc, month desc.
    Returns an empty list on error.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("sip_log")
            .select("*, sip_log_funds(*)")
            .eq("user_id", user_id)
            .order("year", desc=True)
            .order("month", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logging.error(f"Could not load SIP logs: {e}")
        st.error("Could not load SIP logs. Please try again.")
        return []


def save_sip_log(user_id: str, data: dict) -> Optional[dict]:
    """Upsert a SIP log entry on the (user_id, month, year) unique key.

    ``data`` must include month, year, and actual_invested.  It may also
    include planned_sip, notes, and a ``funds`` list of dicts with
    fund_name and amount.

    Fund breakdown rows are replaced on each save (delete + re-insert).

    Returns the upserted SIP log row dict (without funds), or None on
    error.
    """
    try:
        client = get_supabase_client()

        # Separate fund breakdown from the main payload
        funds: list[dict] = data.pop("funds", [])

        payload = {**data, "user_id": user_id}
        response = (
            client.table("sip_log")
            .upsert(payload, on_conflict="user_id,month,year")
            .execute()
        )

        if not response.data:
            return None

        sip_log_row = response.data[0]
        sip_log_id = sip_log_row["id"]

        # Replace fund breakdown rows
        if funds:
            # Delete existing fund rows for this SIP log entry
            client.table("sip_log_funds").delete().eq(
                "sip_log_id", sip_log_id
            ).execute()

            # Insert new fund rows
            fund_rows = [
                {
                    "sip_log_id": sip_log_id,
                    "fund_name": f["fund_name"],
                    "amount": f["amount"],
                }
                for f in funds
            ]
            client.table("sip_log_funds").insert(fund_rows).execute()

        return sip_log_row
    except Exception as e:
        logging.error(f"Could not save SIP log: {e}")
        st.error("Could not save SIP log. Please try again.")
        return None


# ---------------------------------------------------------------------------
# audit_log
# ---------------------------------------------------------------------------
def log_audit(
    user_id: str,
    action: str,
    details: Optional[dict] = None,
) -> Optional[dict]:
    """Insert an audit log entry.

    Returns the inserted row dict, or None on error (silently -- audit
    failures should never block the user).
    """
    try:
        client = get_supabase_client()
        payload: dict = {
            "user_id": user_id,
            "action": action,
        }
        if details is not None:
            payload["details"] = json.dumps(details) if isinstance(details, dict) else details
        response = (
            client.table("audit_log")
            .insert(payload)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception:
        # Audit logging should never disrupt the user experience
        return None


# ---------------------------------------------------------------------------
# Privacy: export & delete
# ---------------------------------------------------------------------------
def export_all_data(user_id: str) -> Optional[dict]:
    """Export all data for a user across every table.

    Returns a dict keyed by table name, each containing a list of row
    dicts.  Returns None on error.
    """
    try:
        client = get_supabase_client()

        fire_inputs = (
            client.table("fire_inputs")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        ).data or []

        income_entries = (
            client.table("income_entries")
            .select("*")
            .eq("user_id", user_id)
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
        ).data or []

        fixed_expenses = (
            client.table("fixed_expenses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        ).data or []

        sip_logs = (
            client.table("sip_log")
            .select("*, sip_log_funds(*)")
            .eq("user_id", user_id)
            .order("year", desc=True)
            .order("month", desc=True)
            .execute()
        ).data or []

        audit_logs = (
            client.table("audit_log")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        ).data or []

        return {
            "fire_inputs": fire_inputs,
            "income_entries": income_entries,
            "fixed_expenses": fixed_expenses,
            "sip_logs": sip_logs,
            "audit_log": audit_logs,
        }
    except Exception as e:
        logging.error(f"Could not export data: {e}")
        st.error("Could not export data. Please try again.")
        return None


def delete_all_user_data(user_id: str) -> bool:
    """Delete all rows belonging to a user from every table.

    Deletion order respects foreign-key relationships.  sip_log_funds
    rows are cascade-deleted when their parent sip_log rows are removed.

    Returns True on success, False on error.
    """
    try:
        client = get_supabase_client()

        # Order matters: children before parents, sip_log_funds cascade
        # automatically via ON DELETE CASCADE on sip_log.
        client.table("audit_log").delete().eq("user_id", user_id).execute()
        client.table("income_entries").delete().eq("user_id", user_id).execute()
        client.table("fixed_expenses").delete().eq("user_id", user_id).execute()
        client.table("sip_log").delete().eq("user_id", user_id).execute()
        client.table("fire_inputs").delete().eq("user_id", user_id).execute()

        return True
    except Exception as e:
        logging.error(f"Could not delete user data: {e}")
        st.error("Could not delete user data. Please try again.")
        return False
