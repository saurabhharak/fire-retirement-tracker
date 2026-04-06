"""Project expenses API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import ProjectExpenseCreate, ProjectExpenseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import project_expenses_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["project-expenses"])


@router.get("/project-expenses")
@limiter.limit("60/minute")
async def list_project_expenses(
    request: Request,
    project_id: str = Query(None),
    category: str = Query(None),
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = project_expenses_svc.load_project_expenses(
        user.id, user.access_token,
        project_id=project_id, category=category, active_only=active,
    )
    return {"data": entries}


@router.get("/project-expenses/summary")
@limiter.limit("30/minute")
async def project_expense_summary(
    request: Request,
    project_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = project_expenses_svc.compute_project_summary(
        user.id, user.access_token, project_id,
    )
    return {"data": summary}


@router.post("/project-expenses")
@limiter.limit("30/minute")
async def create_project_expense(
    request: Request,
    data: ProjectExpenseCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = project_expenses_svc.save_project_expense(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(user.id, "create_project_expense", {"project_id": data.project_id, "category": data.category}, user.access_token)
    return {"data": result, "message": "Expense added"}


@router.patch("/project-expenses/{expense_id}")
@limiter.limit("30/minute")
async def update_project_expense(
    request: Request,
    expense_id: UUID,
    data: ProjectExpenseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = project_expenses_svc.update_project_expense(
        str(expense_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_project_expense", {"expense_id": str(expense_id)}, user.access_token)
    return {"data": result, "message": "Expense updated"}


@router.delete("/project-expenses/{expense_id}")
@limiter.limit("10/minute")
async def deactivate_project_expense(
    request: Request,
    expense_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    project_expenses_svc.deactivate_project_expense(str(expense_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_project_expense", {"expense_id": str(expense_id)}, user.access_token)
    return {"message": "Expense deactivated"}
