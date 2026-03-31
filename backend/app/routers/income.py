"""Income API routes."""
from fastapi import APIRouter, Depends, Query
from app.dependencies import CurrentUser, get_current_user
from app.services import income_svc

router = APIRouter(tags=["income"])

@router.get("/income")
async def list_income(limit: int = Query(12, ge=1, le=100), user: CurrentUser = Depends(get_current_user)):
    entries = await income_svc.load_income_entries(user.id, user.access_token, limit)
    return {"data": entries}

@router.post("/income")
async def create_income(data: dict, user: CurrentUser = Depends(get_current_user)):
    result = await income_svc.save_income_entry(user.id, data, user.access_token)
    return {"data": result, "message": "Income entry saved"}

@router.delete("/income/{month}/{year}")
async def delete_income(month: int, year: int, user: CurrentUser = Depends(get_current_user)):
    await income_svc.delete_income_entry(user.id, month, year, user.access_token)
    return {"message": "Income entry deleted"}
