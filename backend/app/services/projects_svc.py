"""Projects CRUD service."""
import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def load_projects(
    user_id: str,
    access_token: str,
    status: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch all projects for the user."""
    try:
        client = get_user_client(access_token)
        query = client.table("projects").select("*").eq("user_id", user_id)
        if active_only:
            query = query.eq("is_active", True)
        if status:
            query = query.eq("status", status)
        response = query.order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load projects: %s", e)
        raise DatabaseError("Could not load projects") from e


def _serialize_dates(data: dict) -> dict:
    """Convert date objects to ISO strings for Supabase JSON serialization."""
    from datetime import date as date_type
    return {k: v.isoformat() if isinstance(v, date_type) else v for k, v in data.items()}


def save_project(user_id: str, data: dict, access_token: str) -> Optional[dict]:
    """Create a new project."""
    try:
        client = get_user_client(access_token)
        payload = {**_serialize_dates(data), "user_id": user_id}
        response = client.table("projects").insert(payload).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Could not save project: %s", e)
        raise DatabaseError("Could not save project") from e


def update_project(
    project_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a project by ID."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("projects")
            .update(_serialize_dates(data))
            .eq("id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Project not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update project: %s", e)
        raise DatabaseError("Could not update project") from e


def deactivate_project(
    project_id: str, user_id: str, access_token: str
) -> None:
    """Soft-delete a project."""
    update_project(project_id, user_id, {"is_active": False}, access_token)
