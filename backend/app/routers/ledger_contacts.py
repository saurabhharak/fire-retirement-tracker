"""Ledger contacts API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import LedgerContactCreate, LedgerContactUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import ledger_contacts_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["ledger-contacts"])


@router.get("/ledger-contacts")
@limiter.limit("60/minute")
async def list_contacts(
    request: Request,
    active: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = ledger_contacts_svc.load_contacts(
        user.id, user.access_token, active_only=active,
    )
    return {"data": entries}


# NOTE: /summary MUST be defined before /{contact_id} to prevent FastAPI path shadowing
@router.get("/ledger-contacts/summary")
@limiter.limit("30/minute")
async def contacts_summary(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = ledger_contacts_svc.compute_summary(user.id, user.access_token)
    return {"data": summary}


@router.post("/ledger-contacts")
@limiter.limit("30/minute")
async def create_contact(
    request: Request,
    data: LedgerContactCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = ledger_contacts_svc.save_contact(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(user.id, "create_ledger_contact", {"name": data.name}, user.access_token)
    return {"data": result, "message": "Contact created"}


@router.patch("/ledger-contacts/{contact_id}")
@limiter.limit("30/minute")
async def update_contact(
    request: Request,
    contact_id: UUID,
    data: LedgerContactUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = ledger_contacts_svc.update_contact(
        str(contact_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_ledger_contact", {"contact_id": str(contact_id)}, user.access_token)
    return {"data": result, "message": "Contact updated"}


@router.delete("/ledger-contacts/{contact_id}")
@limiter.limit("10/minute")
async def deactivate_contact(
    request: Request,
    contact_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ledger_contacts_svc.deactivate_contact(str(contact_id), user.id, user.access_token)
    log_audit(user.id, "deactivate_ledger_contact", {"contact_id": str(contact_id)}, user.access_token)
    return {"message": "Contact deactivated"}
