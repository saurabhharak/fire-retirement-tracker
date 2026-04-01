"""Expenses API routes."""
from fastapi import APIRouter, Depends, Query, Request
from app.core.models import FixedExpense, FixedExpenseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import expenses_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["expenses"])

@router.get("/expenses")
@limiter.limit("60/minute")
async def list_expenses(
    request: Request,
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = expenses_svc.load_fixed_expenses(
        user.id, user.access_token, active_only=active,
    )
    return {"data": entries}

@router.post("/expenses")
@limiter.limit("30/minute")
async def create_expense(request: Request, data: FixedExpense, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = expenses_svc.save_fixed_expense(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "Expense added"}

@router.patch("/expenses/{expense_id}")
@limiter.limit("30/minute")
async def update_expense(request: Request, expense_id: str, data: FixedExpenseUpdate, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = expenses_svc.update_fixed_expense(expense_id, user.id, data.model_dump(exclude_unset=True), user.access_token)
    return {"data": result, "message": "Expense updated"}

@router.delete("/expenses/{expense_id}")
@limiter.limit("10/minute")
async def deactivate_expense(request: Request, expense_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    expenses_svc.deactivate_fixed_expense(expense_id, user.id, user.access_token)
    log_audit(user.id, "deactivate_expense", {"expense_id": expense_id}, user.access_token)
    return {"message": "Expense deactivated"}
