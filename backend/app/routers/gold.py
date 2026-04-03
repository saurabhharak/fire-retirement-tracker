"""Gold portfolio API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import GoldPurchase, GoldPurchaseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import gold_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["gold"])


@router.get("/gold-purchases")
@limiter.limit("60/minute")
async def list_gold_purchases(
    request: Request,
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = gold_svc.load_gold_purchases(
        user.id, user.access_token, active_only=active,
    )
    return {"data": entries}


@router.post("/gold-purchases")
@limiter.limit("30/minute")
async def create_gold_purchase(
    request: Request,
    data: GoldPurchase,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = gold_svc.save_gold_purchase(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(
        user.id,
        "create_gold_purchase",
        {"purchase_id": result.get("id") if result else None},
        user.access_token,
    )
    return {"data": result, "message": "Gold purchase added"}


@router.patch("/gold-purchases/{purchase_id}")
@limiter.limit("30/minute")
async def update_gold_purchase(
    request: Request,
    purchase_id: UUID,
    data: GoldPurchaseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = gold_svc.update_gold_purchase(
        str(purchase_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_gold_purchase", {"purchase_id": str(purchase_id)}, user.access_token)
    return {"data": result, "message": "Gold purchase updated"}


@router.delete("/gold-purchases/{purchase_id}")
@limiter.limit("10/minute")
async def deactivate_gold_purchase(
    request: Request,
    purchase_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    gold_svc.deactivate_gold_purchase(str(purchase_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_gold_purchase", {"purchase_id": str(purchase_id)}, user.access_token)
    return {"message": "Gold purchase deactivated"}


@router.get("/gold-rate")
@limiter.limit("60/minute")
async def get_gold_rate(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    rate = gold_svc.fetch_gold_rate()
    if rate is None:
        return {"data": None, "message": "Gold rate unavailable"}
    return {"data": rate}


@router.get("/gold-portfolio/summary")
@limiter.limit("30/minute")
async def get_portfolio_summary(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = gold_svc.compute_portfolio_summary(user.id, user.access_token)
    return {"data": summary}
