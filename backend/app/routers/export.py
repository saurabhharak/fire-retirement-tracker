"""Export and account management routes."""
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, get_current_user
from app.services import export_svc

router = APIRouter(tags=["export"])

@router.get("/export")
async def export_all_data(user: CurrentUser = Depends(get_current_user)) -> dict:
    data = export_svc.export_all_data(user.id, user.access_token)
    return {"data": data}

@router.delete("/account")
async def delete_account_data(user: CurrentUser = Depends(get_current_user)) -> dict:
    export_svc.delete_account_data(user.id, user.access_token)
    return {"message": "All data deleted"}
