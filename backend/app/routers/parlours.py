"""Parlour + membership API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.models import ParlourCreate, ParlourMemberAdd, ParlourMemberUpdate, ParlourUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import parlours_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["parlours"])


@router.get("/parlours")
@limiter.limit("60/minute")
async def list_parlours(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = parlours_svc.list_user_parlours(user.id, user.access_token)
    return {"data": entries}


@router.post("/parlours")
@limiter.limit("30/minute")
async def create_parlour(
    request: Request,
    data: ParlourCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = parlours_svc.create_parlour(user.id, data.model_dump(mode='json'), user.access_token)
    return {"data": result, "message": "Parlour created"}


@router.get("/parlours/{parlour_id}")
@limiter.limit("60/minute")
async def get_parlour(
    request: Request,
    parlour_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = parlours_svc.get_parlour(str(parlour_id), user.id, user.access_token)
    return {"data": result}


@router.patch("/parlours/{parlour_id}")
@limiter.limit("30/minute")
async def update_parlour(
    request: Request,
    parlour_id: UUID,
    data: ParlourUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = parlours_svc.update_parlour(
        str(parlour_id), user.id, data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_parlour", {"parlour_id": str(parlour_id)}, user.access_token)
    return {"data": result, "message": "Parlour updated"}


@router.get("/parlours/{parlour_id}/members")
@limiter.limit("60/minute")
async def list_members(
    request: Request,
    parlour_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    members = parlours_svc.list_members(str(parlour_id), user.id, user.access_token)
    return {"data": members}


@router.post("/parlours/{parlour_id}/members")
@limiter.limit("30/minute")
async def add_member(
    request: Request,
    parlour_id: UUID,
    data: ParlourMemberAdd,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = parlours_svc.add_member(
        str(parlour_id), data.member_email, data.role, user.id, user.access_token,
    )
    return {"data": result, "message": "Member added"}


@router.patch("/parlours/{parlour_id}/members/{member_id}")
@limiter.limit("30/minute")
async def update_member_role(
    request: Request,
    parlour_id: UUID,
    member_id: UUID,
    data: ParlourMemberUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = parlours_svc.update_member_role(
        str(parlour_id), str(member_id), data.role, user.id, user.access_token,
    )
    log_audit(user.id, "update_member_role", {
        "parlour_id": str(parlour_id), "member_id": str(member_id), "role": data.role,
    }, user.access_token)
    return {"data": result, "message": "Member role updated"}


@router.delete("/parlours/{parlour_id}/members/{member_id}")
@limiter.limit("10/minute")
async def remove_member(
    request: Request,
    parlour_id: UUID,
    member_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    parlours_svc.remove_member(str(parlour_id), str(member_id), user.id, user.access_token)
    return {"message": "Member removed"}
