"""Parlour + membership CRUD service (multi-tenant business module).

Ownership is enforced via a membership gate (_verify_parlour_membership /
_require_owner) in addition to RLS — same defense-in-depth pattern as
project_expenses_svc._verify_project_ownership.
"""

import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError, ForbiddenError
from app.services.audit_svc import log_audit
from app.services.supabase_client import get_service_client, get_user_client

logger = logging.getLogger(__name__)


def _verify_parlour_membership(parlour_id: str, user_id: str, access_token: str) -> str:
    """Return the caller's role in the parlour, or raise DataNotFoundError."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .select("role")
            .eq("parlour_id", parlour_id)
            .eq("member_id", user_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Parlour not found")
        return response.data[0]["role"]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not verify parlour membership: %s", e)
        raise DatabaseError("Could not verify parlour membership") from e


def _require_owner(parlour_id: str, user_id: str, access_token: str) -> None:
    """Raise ForbiddenError unless the caller is an owner of the parlour."""
    role = _verify_parlour_membership(parlour_id, user_id, access_token)
    if role != "owner":
        raise ForbiddenError("Owner role required")


def _serialize_dates(data: dict) -> dict:
    from datetime import date as date_type
    return {k: v.isoformat() if isinstance(v, date_type) else v for k, v in data.items()}


def create_parlour(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    """Create a new parlour; the owner membership row is added by a DB trigger."""
    try:
        client = get_user_client(access_token)
        payload = {**_serialize_dates(data), "owner_id": user_id}
        response = client.table("parlours").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not create parlour: %s", e)
        raise DatabaseError("Could not create parlour") from e


def list_user_parlours(user_id: str, access_token: str) -> list[dict]:
    """List parlours the user is a member of."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .select("parlour_id, role, parlours(*)")
            .eq("member_id", user_id)
            .execute()
        )
        rows = response.data or []
        return [
            {**r.get("parlours", {}), "role": r.get("role")}
            for r in rows
            if r.get("parlours")
        ]
    except Exception as e:
        logger.error("Could not list parlours: %s", e)
        raise DatabaseError("Could not list parlours") from e


def get_parlour(parlour_id: str, user_id: str, access_token: str) -> Optional[dict]:
    """Fetch a single parlour (membership required)."""
    role = _verify_parlour_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlours").select("*").eq("id", parlour_id).execute()
        )
        if not response.data:
            raise DataNotFoundError("Parlour not found")
        result = dict(response.data[0])
        result["role"] = role
        return result
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not get parlour: %s", e)
        raise DatabaseError("Could not get parlour") from e


def update_parlour(
    parlour_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a parlour (owner only)."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlours")
            .update(_serialize_dates(data))
            .eq("id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Parlour not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update parlour: %s", e)
        raise DatabaseError("Could not update parlour") from e


def list_members(parlour_id: str, user_id: str, access_token: str) -> list[dict]:
    """List parlour members (owner only)."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .select("id, member_id, role, created_at")
            .eq("parlour_id", parlour_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error("Could not list members: %s", e)
        raise DatabaseError("Could not list members") from e


def _resolve_user_id_by_email(email: str) -> Optional[str]:
    """Resolve a Supabase auth user id from their email (service role)."""
    try:
        client = get_service_client()
        response = (
            client.table("auth.users")
            .select("id")
            .eq("email", email)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]["id"]
    except Exception as e:
        logger.error("Could not resolve user by email: %s", e)
        raise DatabaseError("Could not resolve user by email") from e


def add_member(
    parlour_id: str,
    member_email: str,
    role: str,
    user_id: str,
    access_token: str,
) -> Optional[dict]:
    """Add a member by email (owner only)."""
    _require_owner(parlour_id, user_id, access_token)
    member_id = _resolve_user_id_by_email(member_email)
    if not member_id:
        raise DataNotFoundError("No user found with that email")
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .insert({"parlour_id": parlour_id, "member_id": member_id, "role": role})
            .execute()
        )
        log_audit(user_id, "add_parlour_member", {"parlour_id": parlour_id, "email": member_email}, access_token)
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not add member: %s", e)
        raise DatabaseError("Could not add member") from e


def update_member_role(
    parlour_id: str,
    member_id: str,
    role: str,
    user_id: str,
    access_token: str,
) -> Optional[dict]:
    """Update a member's role (owner only). Blocks demoting the last owner."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        target = (
            client.table("parlour_members")
            .select("role")
            .eq("id", member_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not target.data:
            raise DataNotFoundError("Member not found")
        if target.data[0]["role"] == "owner" and role != "owner":
            owners = (
                client.table("parlour_members")
                .select("id")
                .eq("parlour_id", parlour_id)
                .eq("role", "owner")
                .execute()
            )
            if len(owners.data or []) <= 1:
                raise ForbiddenError("Cannot demote the last owner")
        response = (
            client.table("parlour_members")
            .update({"role": role})
            .eq("id", member_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Member not found")
        return response.data[0]
    except (DataNotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error("Could not update member role: %s", e)
        raise DatabaseError("Could not update member role") from e


def remove_member(
    parlour_id: str, member_id: str, user_id: str, access_token: str
) -> None:
    """Remove a member (owner only). Cannot remove the parlour's owner."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .select("role")
            .eq("id", member_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Member not found")
        if response.data[0]["role"] == "owner":
            raise ForbiddenError("Cannot remove the parlour owner")
        (
            client.table("parlour_members")
            .delete()
            .eq("id", member_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        log_audit(user_id, "remove_parlour_member", {"parlour_id": parlour_id, "member_id": member_id}, access_token)
    except (DataNotFoundError, ForbiddenError):
        raise
    except Exception as e:
        logger.error("Could not remove member: %s", e)
        raise DatabaseError("Could not remove member") from e
