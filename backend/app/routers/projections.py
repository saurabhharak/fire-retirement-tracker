"""Projection API routes -- computed from engine.py, not stored."""
from fastapi import APIRouter, Depends, HTTPException, Request
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
@limiter.limit("30/minute")
async def get_growth_projection(request: Request, user: CurrentUser = Depends(get_current_user)) -> dict:
    inputs = _get_inputs(user)
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
