"""Precious metals API routes — purchases, rates, portfolio summary."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import PreciousMetalPurchase, PreciousMetalPurchaseUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import precious_metals_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["precious-metals"])


# NOTE: /rates and /summary MUST be defined before /{purchase_id} so FastAPI
# does not treat the literal strings "rates" or "summary" as a UUID path param.


@router.get("/precious-metals/rates")
@limiter.limit("60/minute")
async def get_metal_rates(
    request: Request,
    metal: Optional[str] = Query(None, description="Filter by metal type (gold/silver/platinum)"),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return current rates for all metals (or a single metal if ?metal= is provided)."""
    rates = precious_metals_svc.fetch_rates(metal_type=metal)
    if rates is None:
        return {"data": None, "message": "Metal rates unavailable"}
    return {"data": rates}


@router.get("/precious-metals/summary")
@limiter.limit("30/minute")
async def get_portfolio_summary(
    request: Request,
    metal: Optional[str] = Query(None, description="Filter by metal type (gold/silver/platinum)"),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return portfolio summary across all metals (or a single metal if ?metal= is provided)."""
    summary = precious_metals_svc.compute_portfolio_summary(
        user.id, user.access_token, metal_type=metal
    )
    return {"data": summary}


@router.get("/precious-metals")
@limiter.limit("60/minute")
async def list_precious_metal_purchases(
    request: Request,
    metal: Optional[str] = Query(None, description="Filter by metal type (gold/silver/platinum)"),
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """List precious metal purchases, optionally filtered by metal type and active status."""
    entries = precious_metals_svc.load_purchases(
        user.id, user.access_token, metal_type=metal, active_only=active,
    )
    return {"data": entries}


@router.post("/precious-metals")
@limiter.limit("30/minute")
async def create_precious_metal_purchase(
    request: Request,
    data: PreciousMetalPurchase,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create a new precious metal purchase entry."""
    result = precious_metals_svc.save_purchase(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(
        user.id,
        "create_precious_metal_purchase",
        {"purchase_id": result.get("id") if result else None},
        user.access_token,
    )
    return {"data": result, "message": "Precious metal purchase added"}


@router.patch("/precious-metals/{purchase_id}")
@limiter.limit("30/minute")
async def update_precious_metal_purchase(
    request: Request,
    purchase_id: UUID,
    data: PreciousMetalPurchaseUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Partially update an existing precious metal purchase."""
    result = precious_metals_svc.update_purchase(
        str(purchase_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(
        user.id,
        "update_precious_metal_purchase",
        {"purchase_id": str(purchase_id)},
        user.access_token,
    )
    return {"data": result, "message": "Precious metal purchase updated"}


@router.delete("/precious-metals/{purchase_id}")
@limiter.limit("10/minute")
async def deactivate_precious_metal_purchase(
    request: Request,
    purchase_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Soft-delete (deactivate) a precious metal purchase."""
    precious_metals_svc.deactivate_purchase(str(purchase_id), user.id, user.access_token)
    log_audit(
        user.id,
        "deactivate_precious_metal_purchase",
        {"purchase_id": str(purchase_id)},
        user.access_token,
    )
    return {"message": "Precious metal purchase deactivated"}
