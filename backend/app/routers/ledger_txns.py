"""Ledger transactions API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.models import LedgerTxnCreate, LedgerTxnUpdate
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import ledger_txns_svc
from app.services.audit_svc import log_audit

router = APIRouter(tags=["ledger-txns"])


@router.get("/ledger-txns")
@limiter.limit("60/minute")
async def list_transactions(
    request: Request,
    contact_id: str = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = ledger_txns_svc.load_transactions(
        user.id, user.access_token, contact_id=contact_id,
    )
    return {"data": entries}


@router.post("/ledger-txns")
@limiter.limit("30/minute")
async def create_transaction(
    request: Request,
    data: LedgerTxnCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = ledger_txns_svc.save_transaction(
        user.id, data.model_dump(), user.access_token,
    )
    log_audit(
        user.id,
        "create_ledger_txn",
        {"contact_id": data.contact_id, "direction": data.direction, "amount": data.amount},
        user.access_token,
    )
    return {"data": result, "message": "Transaction created"}


@router.patch("/ledger-txns/{txn_id}")
@limiter.limit("30/minute")
async def update_transaction(
    request: Request,
    txn_id: UUID,
    data: LedgerTxnUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = ledger_txns_svc.update_transaction(
        str(txn_id), user.id, data.model_dump(exclude_unset=True), user.access_token,
    )
    log_audit(user.id, "update_ledger_txn", {"txn_id": str(txn_id)}, user.access_token)
    return {"data": result, "message": "Transaction updated"}


@router.delete("/ledger-txns/{txn_id}")
@limiter.limit("10/minute")
async def delete_transaction(
    request: Request,
    txn_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ledger_txns_svc.delete_transaction(str(txn_id), user.id, user.access_token)
    log_audit(user.id, "delete_ledger_txn", {"txn_id": str(txn_id)}, user.access_token)
    return {"message": "Transaction deleted"}
