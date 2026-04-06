"""Project expenses CRUD + summary service."""
import logging
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _verify_project_ownership(project_id: str, user_id: str, access_token: str) -> None:
    """Check that project_id belongs to user_id. Raises DataNotFoundError if not."""
    client = get_user_client(access_token)
    response = (
        client.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise DataNotFoundError("Project not found")


def load_project_expenses(
    user_id: str,
    access_token: str,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
) -> list[dict]:
    """Fetch project expenses. Requires project_id for scoping."""
    try:
        if project_id:
            _verify_project_ownership(project_id, user_id, access_token)

        client = get_user_client(access_token)
        query = client.table("project_expenses").select("*")
        if project_id:
            query = query.eq("project_id", project_id)
        if active_only:
            query = query.eq("is_active", True)
        if category:
            query = query.eq("category", category)
        response = query.order("date", desc=True).execute()
        return response.data or []
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not load project expenses: %s", e)
        raise DatabaseError("Could not load project expenses") from e


def save_project_expense(
    user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Create a new project expense."""
    try:
        _verify_project_ownership(data["project_id"], user_id, access_token)
        client = get_user_client(access_token)
        response = client.table("project_expenses").insert(data).execute()
        return response.data[0] if response.data else None
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not save project expense: %s", e)
        raise DatabaseError("Could not save project expense") from e


def update_project_expense(
    expense_id: str, user_id: str, data: dict, access_token: str
) -> Optional[dict]:
    """Update a project expense by ID."""
    try:
        client = get_user_client(access_token)
        response = (
            client.table("project_expenses")
            .update(data)
            .eq("id", expense_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Project expense not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update project expense: %s", e)
        raise DatabaseError("Could not update project expense") from e


def deactivate_project_expense(
    expense_id: str, user_id: str, access_token: str
) -> None:
    """Soft-delete a project expense."""
    update_project_expense(expense_id, user_id, {"is_active": False}, access_token)


def compute_project_summary(
    user_id: str, access_token: str, project_id: str
) -> dict:
    """Compute category totals and monthly totals for a project."""
    expenses = load_project_expenses(user_id, access_token, project_id=project_id)

    category_totals: dict[str, float] = {}
    monthly_totals: dict[str, float] = {}
    total_paid = 0.0

    for e in expenses:
        paid = float(e.get("paid_amount", 0))
        total_paid += paid

        cat = e.get("category", "Other")
        category_totals[cat] = category_totals.get(cat, 0) + paid

        month = e.get("date", "")[:7]  # YYYY-MM
        if month:
            monthly_totals[month] = monthly_totals.get(month, 0) + paid

    return {
        "total_paid": round(total_paid, 2),
        "entry_count": len(expenses),
        "category_totals": category_totals,
        "monthly_totals": monthly_totals,
    }
