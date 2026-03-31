"""Income API routes."""
from fastapi import APIRouter, Depends, Path, Query, Request
from app.core.models import IncomeEntry
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import income_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["income"])

@router.get("/income")
@limiter.limit("60/minute")
async def list_income(request: Request, limit: int = Query(12, ge=1, le=100), user: CurrentUser = Depends(get_current_user)) -> dict:
    entries = income_svc.load_income_entries(user.id, user.access_token, limit)
    return {"data": entries}

@router.post("/income")
@limiter.limit("30/minute")
async def create_income(request: Request, data: IncomeEntry, user: CurrentUser = Depends(get_current_user)) -> dict:
    result = income_svc.save_income_entry(user.id, data.model_dump(), user.access_token)
    return {"data": result, "message": "Income entry saved"}

@router.delete("/income/{month}/{year}")
@limiter.limit("10/minute")
async def delete_income(
    request: Request,
    month: int = Path(ge=1, le=12),
    year: int = Path(ge=2020, le=2100),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    income_svc.delete_income_entry(user.id, month, year, user.access_token)
    log_audit(user.id, "delete_income", {"month": month, "year": year}, user.access_token)
    return {"message": "Income entry deleted"}
