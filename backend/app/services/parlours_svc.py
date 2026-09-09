"""Parlour + membership CRUD service (multi-tenant business module).

Ownership is enforced via a membership gate (_verify_parlour_membership /
_require_owner) in addition to RLS — same defense-in-depth pattern as
project_expenses_svc._verify_project_ownership.
"""

import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.exceptions import DatabaseError, DataNotFoundError, ForbiddenError
from app.services.audit_svc import log_audit
from app.services.supabase_client import get_user_client

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
    """List parlour members (owner only), enriched with email/phone from auth."""
    _require_owner(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        try:
            response = (
                client.table("parlour_members")
                .select("id, member_id, role, phone, created_at")
                .eq("parlour_id", parlour_id)
                .order("created_at", desc=False)
                .execute()
            )
            rows = response.data or []
        except Exception:
            # phone column may not exist yet (migration 030 not applied)
            response = (
                client.table("parlour_members")
                .select("id, member_id, role, created_at")
                .eq("parlour_id", parlour_id)
                .order("created_at", desc=False)
                .execute()
            )
            rows = response.data or []
        auth_users = _list_auth_users()
        for row in rows:
            auth = auth_users.get(row.get("member_id"), {})
            row["email"] = auth.get("email")
            if not row.get("phone"):
                row["phone"] = auth.get("phone")
        return rows
    except Exception as e:
        logger.error("Could not list members: %s", e)
        raise DatabaseError("Could not list members") from e


def _list_auth_users() -> dict:
    """Return {user_id: {email, phone}} for all auth users (admin API)."""
    settings = get_settings()
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    users: dict = {}
    try:
        with httpx.Client(timeout=10) as http:
            page = 1
            for _ in range(10):
                response = http.get(
                    f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
                    params={"page": page, "per_page": 1000},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                for u in payload.get("users") or []:
                    users[u["id"]] = {"email": u.get("email"), "phone": u.get("phone")}
                if payload.get("nextPage") is None:
                    break
                page = payload["nextPage"]
    except httpx.HTTPError as e:
        logger.error("Could not list auth users: %s", e)
    return users


def _normalize_phone(phone: str) -> Optional[str]:
    """Normalize a mobile number to E.164, defaulting to +91 for 10-digit numbers."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if phone.strip().startswith("+"):
        candidate = f"+{digits}"
    elif len(digits) == 10:
        candidate = f"+91{digits}"
    else:
        candidate = f"+{digits}"
    if not 10 <= len(candidate) - 1 <= 15:
        return None
    return candidate


def _resolve_user_id_by_phone(phone: str) -> Optional[str]:
    """Resolve a Supabase auth user id from their phone number (E.164)."""
    for uid, info in _list_auth_users().items():
        if info.get("phone") == phone:
            return uid
    return None


def _create_user_by_phone(phone: str) -> str:
    """Create an auth user for a phone number (admin API). Returns the user id.

    The user logs in later with a mobile OTP — requires a Phone/SMS provider
    to be configured in the Supabase dashboard.
    """
    settings = get_settings()
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=10) as http:
            response = http.post(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
                json={"phone": phone, "phone_confirm": False},
                headers=headers,
            )
            if response.status_code == 422:
                # Already registered — resolve instead
                existing = _resolve_user_id_by_phone(phone)
                if existing:
                    return existing
            response.raise_for_status()
            user = response.json()
            return user["id"]
    except httpx.HTTPError as e:
        logger.error("Could not create user by phone: %s", e)
        raise DatabaseError("Could not create user for that mobile number") from e


def _resolve_user_id_by_email(email: str) -> Optional[str]:
    """Resolve a Supabase auth user id from their email.

    auth.users lives in the auth schema and is not exposed through PostgREST
    (PGRST205), and the Admin Auth API ignores its email query param — it
    returns every user — so list users page by page and match the email
    ourselves.
    """
    settings = get_settings()
    target = email.strip().lower()
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    try:
        with httpx.Client(timeout=10) as http:
            page = 1
            for _ in range(10):  # hard cap; a parlour roster has few users
                response = http.get(
                    f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
                    params={"page": page, "per_page": 1000},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                for u in payload.get("users") or []:
                    if str(u.get("email", "")).lower() == target:
                        return u["id"]
                if payload.get("nextPage") is None:
                    return None
                page = payload["nextPage"]
        return None
    except httpx.HTTPError as e:
        logger.error("Could not resolve user by email: %s", e)
        raise DatabaseError("Could not resolve user by email") from e


def add_member(
    parlour_id: str,
    member_email: Optional[str],
    role: str,
    user_id: str,
    access_token: str,
    phone: Optional[str] = None,
) -> Optional[dict]:
    """Add a member by email and/or mobile number (owner only).

    Email members must already have an account. Mobile members get an auth
    user created automatically, so they can log in with a phone OTP.
    """
    _require_owner(parlour_id, user_id, access_token)

    normalised_phone = _normalize_phone(phone) if phone else None
    if phone and not normalised_phone:
        raise DataNotFoundError("Enter a valid mobile number (10 digits for India)")

    insert: dict = {"parlour_id": parlour_id, "role": role}
    audit_meta: dict = {"parlour_id": parlour_id}
    if member_email:
        member_id = _resolve_user_id_by_email(member_email)
        if not member_id:
            raise DataNotFoundError("No user found with that email")
        insert["member_id"] = member_id
        audit_meta["email"] = member_email
    elif normalised_phone:
        member_id = _resolve_user_id_by_phone(normalised_phone)
        if not member_id:
            member_id = _create_user_by_phone(normalised_phone)
        insert["member_id"] = member_id
        insert["phone"] = normalised_phone
        audit_meta["phone"] = normalised_phone
    else:
        raise DataNotFoundError("Provide an email or a mobile number")

    try:
        client = get_user_client(access_token)
        response = (
            client.table("parlour_members")
            .insert(insert)
            .execute()
        )
        log_audit(user_id, "add_parlour_member", audit_meta, access_token)
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
