"""Export and account management routes."""
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, get_current_user
from app.services.supabase_client import get_user_client

router = APIRouter(tags=["export"])

@router.get("/export")
async def export_all_data(user: CurrentUser = Depends(get_current_user)):
    client = get_user_client(user.access_token)
    data = {
        "fire_inputs": client.table("fire_inputs").select("*").eq("user_id", user.id).execute().data,
        "income_entries": client.table("income_entries").select("*").eq("user_id", user.id).execute().data,
        "fixed_expenses": client.table("fixed_expenses").select("*").eq("user_id", user.id).execute().data,
        "sip_log": client.table("sip_log").select("*, sip_log_funds(*)").eq("user_id", user.id).execute().data,
    }
    return {"data": data}

@router.delete("/account")
async def delete_account_data(user: CurrentUser = Depends(get_current_user)):
    client = get_user_client(user.access_token)
    for table in ["sip_log", "income_entries", "fixed_expenses", "fire_inputs", "audit_log"]:
        client.table(table).delete().eq("user_id", user.id).execute()
    return {"message": "All data deleted"}
