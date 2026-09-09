"""Amul parlour module API routes: sales, invoices, analytics, Sarvam usage."""
from uuid import UUID
import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import ValidationError

from app.core.models import (
    AmulDailyPurchaseCreate,
    AmulDailyPurchaseUpdate,
    AmulDailySaleCreate,
    AmulDailySaleUpdate,
    AmulInvoiceItemUpdate,
    AmulInvoiceUpdate,
    AmulOtherExpenseCreate,
    AmulOtherExpenseUpdate,
)
from app.core import business_engine
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import (
    amul_invoices_svc,
    amul_other_expenses_svc,
    amul_purchases_svc,
    amul_sales_svc,
    parlours_svc,
    sarvam_client,
    sarvam_usage_svc,
)
from app.services.audit_svc import log_audit

router = APIRouter(tags=["amul"])

MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_WHATSAPP_CHARS = 200_000


# ---------------------------------------------------------------------------
# Daily sales (WhatsApp cash + online)
# ---------------------------------------------------------------------------

@router.get("/amul/sales")
@limiter.limit("60/minute")
async def list_daily_sales(
    request: Request,
    parlour_id: str = Query(...),
    from_date: str = Query(None),
    to_date: str = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = amul_sales_svc.load_daily_sales(
        parlour_id, user.id, user.access_token,
        from_date=from_date, to_date=to_date,
    )
    return {"data": entries}


@router.post("/amul/sales")
@limiter.limit("30/minute")
async def create_daily_sale(
    request: Request,
    data: AmulDailySaleCreate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    # Allow both query-param and body parlour_id for flexibility
    result = amul_sales_svc.save_daily_sale(
        parlour_id, user.id, data.model_dump(mode='json'), user.access_token,
    )
    return {"data": result, "message": "Daily sale added"}


@router.patch("/amul/sales/{sale_id}")
@limiter.limit("30/minute")
async def update_daily_sale(
    request: Request,
    sale_id: UUID,
    data: AmulDailySaleUpdate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_sales_svc.update_daily_sale(
        str(sale_id), parlour_id, user.id,
        data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Daily sale updated"}


@router.delete("/amul/sales/{sale_id}")
@limiter.limit("10/minute")
async def delete_daily_sale(
    request: Request,
    sale_id: UUID,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    amul_sales_svc.delete_daily_sale(str(sale_id), parlour_id, user.id, user.access_token)
    log_audit(user.id, "delete_amul_sale", {"sale_id": str(sale_id)}, user.access_token)
    return {"message": "Daily sale deleted"}


# ---------------------------------------------------------------------------
# Daily purchases (manual day-by-day totals)
# ---------------------------------------------------------------------------

@router.get("/amul/purchases")
@limiter.limit("60/minute")
async def list_daily_purchases(
    request: Request,
    parlour_id: str = Query(...),
    from_date: str = Query(None),
    to_date: str = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = amul_purchases_svc.load_daily_purchases(
        parlour_id, user.id, user.access_token,
        from_date=from_date, to_date=to_date,
    )
    return {"data": entries}


@router.post("/amul/purchases")
@limiter.limit("30/minute")
async def create_daily_purchase(
    request: Request,
    data: AmulDailyPurchaseCreate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_purchases_svc.save_daily_purchase(
        parlour_id, user.id, data.model_dump(mode='json'), user.access_token,
    )
    return {"data": result, "message": "Daily purchase added"}


@router.patch("/amul/purchases/{purchase_id}")
@limiter.limit("30/minute")
async def update_daily_purchase(
    request: Request,
    purchase_id: UUID,
    data: AmulDailyPurchaseUpdate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_purchases_svc.update_daily_purchase(
        str(purchase_id), parlour_id, user.id,
        data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Daily purchase updated"}


@router.delete("/amul/purchases/{purchase_id}")
@limiter.limit("10/minute")
async def delete_daily_purchase(
    request: Request,
    purchase_id: UUID,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    amul_purchases_svc.delete_daily_purchase(str(purchase_id), parlour_id, user.id, user.access_token)
    log_audit(user.id, "delete_amul_purchase", {"purchase_id": str(purchase_id)}, user.access_token)
    return {"message": "Daily purchase deleted"}


# ---------------------------------------------------------------------------
# Purchase invoices
# ---------------------------------------------------------------------------

@router.get("/amul/invoices")
@limiter.limit("60/minute")
async def list_invoices(
    request: Request,
    parlour_id: str = Query(...),
    month: str = Query(None),
    distributor: str = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = amul_invoices_svc.load_invoices(
        parlour_id, user.id, user.access_token,
        month=month, distributor=distributor,
    )
    return {"data": entries}


@router.get("/amul/invoices/{invoice_id}")
@limiter.limit("60/minute")
async def get_invoice(
    request: Request,
    invoice_id: UUID,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_invoices_svc.get_invoice_with_items(
        str(invoice_id), parlour_id, user.id, user.access_token,
    )
    return {"data": result}


@router.post("/amul/invoices/upload")
@limiter.limit("5/minute")
async def upload_invoices_pdf(
    request: Request,
    parlour_id: str = Form(...),
    use_docling: bool = Form(False),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Upload a purchase PDF, OCR it (Sarvam or free Docling), and store drafts."""
    # Authorize BEFORE spending paid OCR credits (any authed user could
    # otherwise burn a parlour's Sarvam quota by naming it here).
    parlours_svc._verify_parlour_membership(parlour_id, user.id, user.access_token)

    # Enforce size + type limits BEFORE materializing the body in memory.
    declared = request.headers.get("content-length")
    if declared and int(declared) > MAX_PDF_BYTES * 2:  # multipart overhead headroom
        raise HTTPException(status_code=413, detail="PDF too large (max 20 MB)")
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF too large (max 20 MB)")
        chunks.append(chunk)
    pdf_bytes = b"".join(chunks)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    # Dedup layer 1: the exact same file was already processed for this
    # parlour — skip OCR (and paid credits) entirely and return what exists.
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    existing = amul_invoices_svc.find_by_pdf_hash(parlour_id, pdf_hash, user.access_token)
    if existing:
        return {
            "data": existing,
            "credits_used": 0.0,
            "status": "success",
            "source": "cache",
            "duplicate": True,
            "created_count": 0,
        }

    extraction = sarvam_client.extract_invoices_from_pdf(
        pdf_bytes,
        parlour_id,
        user.id,
        user.access_token,
        use_docling=use_docling,
        source_pdf=file.filename,
    )
    created = []
    skipped_duplicates = 0
    skipped_undated = extraction.get("skipped_undated", 0)
    for invoice in extraction["invoices"]:
        # bill_date is NOT NULL in the DB — an invoice without a readable
        # date must never reach the insert.
        if not invoice.get("bill_date"):
            skipped_undated += 1
            continue
        # Dedup layer 2: the same bill (bill_no + bill_date) is already stored
        # — e.g. a re-scan or a different PDF containing the same invoice.
        if amul_invoices_svc.find_duplicate(parlour_id, invoice, user.access_token):
            skipped_duplicates += 1
            continue
        result = amul_invoices_svc.save_invoice_with_items(
            parlour_id, user.id,
            {k: v for k, v in invoice.items()
             if k not in ("items", "status", "warning", "page_no")},
            invoice.get("items", []),
            user.access_token,
            source_pdf_hash=pdf_hash,
        )
        created.append(result)
    log_audit(user.id, "upload_amul_invoices", {"parlour_id": parlour_id, "count": len(created)}, user.access_token)
    return {
        "data": created,
        "credits_used": extraction["credits_used"],
        "status": extraction["status"],
        "source": extraction["source"],
        "duplicate": False,
        "created_count": len(created),
        "skipped_duplicates": skipped_duplicates,
        "skipped_undated": skipped_undated,
    }


@router.patch("/amul/invoices/{invoice_id}")
@limiter.limit("30/minute")
async def update_invoice(
    request: Request,
    invoice_id: UUID,
    data: AmulInvoiceUpdate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_invoices_svc.update_invoice(
        str(invoice_id), parlour_id, user.id,
        data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Invoice updated"}


@router.patch("/amul/invoice-items/{item_id}")
@limiter.limit("30/minute")
async def update_invoice_item(
    request: Request,
    item_id: UUID,
    data: AmulInvoiceItemUpdate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_invoices_svc.update_invoice_item(
        str(item_id), parlour_id, user.id,
        data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Invoice item updated"}


@router.delete("/amul/invoices/{invoice_id}")
@limiter.limit("10/minute")
async def delete_invoice(
    request: Request,
    invoice_id: UUID,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    amul_invoices_svc.delete_invoice(str(invoice_id), parlour_id, user.id, user.access_token)
    log_audit(user.id, "delete_amul_invoice", {"invoice_id": str(invoice_id)}, user.access_token)
    return {"message": "Invoice deleted"}


# ---------------------------------------------------------------------------
# Other business expenses (rent, electricity, wages, etc.)
# ---------------------------------------------------------------------------

@router.get("/amul/expenses")
@limiter.limit("60/minute")
async def list_other_expenses(
    request: Request,
    parlour_id: str = Query(...),
    from_date: str = Query(None),
    to_date: str = Query(None),
    category: str = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    entries = amul_other_expenses_svc.load_other_expenses(
        parlour_id, user.id, user.access_token,
        from_date=from_date, to_date=to_date, category=category,
    )
    return {"data": entries}


@router.post("/amul/expenses")
@limiter.limit("30/minute")
async def create_other_expense(
    request: Request,
    data: AmulOtherExpenseCreate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_other_expenses_svc.save_other_expense(
        parlour_id, user.id, data.model_dump(mode='json'), user.access_token,
    )
    return {"data": result, "message": "Expense added"}


@router.patch("/amul/expenses/{expense_id}")
@limiter.limit("30/minute")
async def update_other_expense(
    request: Request,
    expense_id: UUID,
    data: AmulOtherExpenseUpdate,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    result = amul_other_expenses_svc.update_other_expense(
        str(expense_id), parlour_id, user.id,
        data.model_dump(mode='json', exclude_unset=True), user.access_token,
    )
    return {"data": result, "message": "Expense updated"}


@router.delete("/amul/expenses/{expense_id}")
@limiter.limit("10/minute")
async def delete_other_expense(
    request: Request,
    expense_id: UUID,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    amul_other_expenses_svc.delete_other_expense(str(expense_id), parlour_id, user.id, user.access_token)
    log_audit(user.id, "delete_amul_expense", {"expense_id": str(expense_id)}, user.access_token)
    return {"message": "Expense deleted"}


@router.post("/amul/sales/import-whatsapp")
@limiter.limit("5/minute")
async def import_whatsapp_sales(
    request: Request,
    parlour_id: str = Query(...),
    text: str = Form(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Import daily sales from a WhatsApp group chat export.

    Parses the chat text (label-aware cash/online) and bulk-inserts the rows
    as draft sales (membership required). Returns how many were imported and
    the parsed rows for confirmation.
    """
    from app.services.whatsapp_sales_parser import parse_whatsapp_chat

    if len(text) > MAX_WHATSAPP_CHARS:
        raise HTTPException(status_code=413, detail="Chat export too large (max 200k characters)")

    rows = parse_whatsapp_chat(text)
    imported = []
    skipped = 0
    for row in rows:
        # Parser output bypasses nothing: validate through the same Pydantic
        # model the manual-create endpoint uses before touching the DB.
        try:
            validated = AmulDailySaleCreate(**{k: v for k, v in row.items() if k != "source"})
        except ValidationError:
            skipped += 1
            continue
        result = amul_sales_svc.save_daily_sale(
            parlour_id, user.id, validated.model_dump(mode='json'), user.access_token,
        )
        if result:
            imported.append(result)
        else:
            skipped += 1
    log_audit(user.id, "import_whatsapp_sales", {"parlour_id": parlour_id, "count": len(imported)}, user.access_token)
    return {"data": imported, "count": len(imported), "skipped": skipped}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/amul/analytics")
@limiter.limit("60/minute")
async def analytics(
    request: Request,
    parlour_id: str = Query(...),
    period: str = Query("month"),
    period_value: str = Query(None),
    year: int = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    sales = amul_sales_svc.load_daily_sales(parlour_id, user.id, user.access_token)
    invoices = amul_invoices_svc.load_invoices(parlour_id, user.id, user.access_token)
    expenses = amul_other_expenses_svc.load_other_expenses(parlour_id, user.id, user.access_token)
    summary = business_engine.compute_pnl(
        sales, invoices, period, period_value=period_value,
        expenses=expenses, year=year,
    )
    trends = business_engine.compute_trends(
        sales, invoices, period, period_value=period_value, expenses=expenses,
    )
    return {"data": {"summary": summary, "trends": trends}}


# ---------------------------------------------------------------------------
# Sarvam usage / spend
# ---------------------------------------------------------------------------

@router.get("/amul/sarvam-usage")
@limiter.limit("60/minute")
async def sarvam_usage(
    request: Request,
    parlour_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    summary = sarvam_usage_svc.get_spend_summary(parlour_id, user.id, user.access_token)
    return {"data": summary}
