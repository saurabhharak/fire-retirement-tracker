"""Export and account management routes."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import export_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["export"])


class DeleteConfirmation(BaseModel):
    confirm: str  # Must be "DELETE_ALL_DATA"


@router.get("/export")
@limiter.limit("5/minute")
async def export_all_data(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    data = export_svc.export_all_data(user.id, user.access_token)
    return {"data": data}

@router.delete("/account")
@limiter.limit("1/hour")
async def delete_account_data(
    request: Request,
    body: DeleteConfirmation,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if body.confirm != "DELETE_ALL_DATA":
        raise HTTPException(status_code=400, detail='Confirmation required: send {"confirm": "DELETE_ALL_DATA"}')
    log_audit(user.id, "delete_account", {"confirm": body.confirm}, user.access_token)
    export_svc.delete_account_data(user.id, user.access_token)
    return {"message": "All data deleted"}
