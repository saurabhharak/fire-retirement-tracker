"""SIP log API routes."""
from fastapi import APIRouter, Depends, Query, Request
from app.core.models import SipLogEntry
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import sip_log_svc

router = APIRouter(tags=["sip-log"])

@router.get("/sip-log")
@limiter.limit("60/minute")
async def list_sip_logs(request: Request, limit: int = Query(60, ge=1, le=500), user: CurrentUser = Depends(get_current_user)) -> dict:
    entries = sip_log_svc.load_sip_logs(user.id, user.access_token, limit)
    return {"data": entries}

@router.get("/sip-log/total-invested")
@limiter.limit("60/minute")
async def get_total_invested(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    total = sip_log_svc.get_total_sip_invested(user.id, user.access_token)
    return {"data": total}

@router.post("/sip-log")
@limiter.limit("30/minute")
async def create_sip_log(request: Request, data: SipLogEntry, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = sip_log_svc.save_sip_log(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "SIP log saved"}
