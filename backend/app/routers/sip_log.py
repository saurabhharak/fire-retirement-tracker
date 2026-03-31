"""SIP log API routes."""
from fastapi import APIRouter, Depends, Query
from app.core.models import SipLogEntry
from app.dependencies import CurrentUser, get_current_user
from app.services import sip_log_svc

router = APIRouter(tags=["sip-log"])

@router.get("/sip-log")
async def list_sip_logs(limit: int = Query(60, ge=1, le=500), user: CurrentUser = Depends(get_current_user)) -> dict:
    entries = sip_log_svc.load_sip_logs(user.id, user.access_token, limit)
    return {"data": entries}

@router.post("/sip-log")
async def create_sip_log(data: SipLogEntry, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = sip_log_svc.save_sip_log(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "SIP log saved"}
