"""Projection API routes -- computed from engine.py, not stored."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.engine import (
    compute_derived_inputs, compute_fund_allocation,
    compute_growth_projection, compute_monthly_sips, compute_retirement_metrics,
)
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import fire_inputs_svc

router = APIRouter(tags=["projections"])

def _get_inputs(user: CurrentUser) -> dict:
    raw = fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if raw is None:
        raise HTTPException(status_code=404, detail="Configure FIRE Settings first")
    return compute_derived_inputs(raw)

@router.get("/projections/growth")
@limiter.limit("60/minute")
async def get_growth_projection(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    # What-if scenario overrides (optional, not persisted)
    your_sip: Optional[float] = Query(None, ge=0),
    wife_sip: Optional[float] = Query(None, ge=0),
    equity_return: Optional[float] = Query(None, gt=0, le=0.3),
    inflation: Optional[float] = Query(None, gt=0, le=0.2),
    step_up_pct: Optional[float] = Query(None, ge=0, le=0.5),
    retirement_age: Optional[int] = Query(None, ge=19, le=99),
) -> dict:
    raw = fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if raw is None:
        raise HTTPException(status_code=404, detail="Configure FIRE Settings first")
    # Apply what-if overrides without mutating the stored record
    overrides: dict = dict(raw)
    if your_sip is not None:
        overrides["your_sip"] = your_sip
    if wife_sip is not None:
        overrides["wife_sip"] = wife_sip
    if equity_return is not None:
        overrides["equity_return"] = equity_return
    if inflation is not None:
        overrides["inflation"] = inflation
    if step_up_pct is not None:
        overrides["step_up_pct"] = step_up_pct
    if retirement_age is not None:
        overrides["retirement_age"] = retirement_age
    inputs = compute_derived_inputs(overrides)
    return {"data": compute_growth_projection(inputs)}

@router.get("/projections/retirement")
@limiter.limit("30/minute")
async def get_retirement_analysis(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    inputs = _get_inputs(user)
    projection = compute_growth_projection(inputs)
    years = inputs["years_to_retirement"]
    corpus = projection[years]["portfolio"] if years < len(projection) else projection[-1]["portfolio"]
    return {"data": compute_retirement_metrics(inputs, corpus)}

@router.get("/projections/fund-allocation")
@limiter.limit("30/minute")
async def get_fund_allocation(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    inputs = _get_inputs(user)
    return {"data": compute_fund_allocation(inputs)}

@router.get("/projections/monthly-sips")
@limiter.limit("30/minute")
async def get_monthly_sips(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    inputs = _get_inputs(user)
    return {"data": compute_monthly_sips(inputs)}
