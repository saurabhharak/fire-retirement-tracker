"""Income API routes."""
from fastapi import APIRouter, Depends, Query
from app.core.models import IncomeEntry
from app.dependencies import CurrentUser, get_current_user
from app.services import income_svc

router = APIRouter(tags=["income"])

@router.get("/income")
async def list_income(limit: int = Query(12, ge=1, le=100), user: CurrentUser = Depends(get_current_user)) -> dict:
    entries = income_svc.load_income_entries(user.id, user.access_token, limit)
    return {"data": entries}

@router.post("/income")
async def create_income(data: IncomeEntry, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = income_svc.save_income_entry(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "Income entry saved"}

@router.delete("/income/{month}/{year}")
async def delete_income(month: int, year: int, user: CurrentUser = Depends(get_current_user)) -> dict:
    income_svc.delete_income_entry(user.id, month, year, user.access_token)
    return {"message": "Income entry deleted"}
