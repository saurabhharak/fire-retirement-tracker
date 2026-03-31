"""Expenses API routes."""
from fastapi import APIRouter, Depends, Query
from app.dependencies import CurrentUser, get_current_user
from app.services import expenses_svc

router = APIRouter(tags=["expenses"])

@router.get("/expenses")
async def list_expenses(active: bool = Query(True), user: CurrentUser = Depends(get_current_user)):
    entries = await expenses_svc.load_fixed_expenses(user.id, user.access_token, active_only=active)
    return {"data": entries}

@router.post("/expenses")
async def create_expense(data: dict, user: CurrentUser = Depends(get_current_user)):
    result = await expenses_svc.save_fixed_expense(user.id, data, user.access_token)
    return {"data": result, "message": "Expense added"}

@router.patch("/expenses/{expense_id}")
async def update_expense(expense_id: str, data: dict, user: CurrentUser = Depends(get_current_user)):
    result = await expenses_svc.update_fixed_expense(expense_id, user.id, data, user.access_token)
    return {"data": result, "message": "Expense updated"}

@router.delete("/expenses/{expense_id}")
async def deactivate_expense(expense_id: str, user: CurrentUser = Depends(get_current_user)):
    await expenses_svc.deactivate_fixed_expense(expense_id, user.id, user.access_token)
    return {"message": "Expense deactivated"}
