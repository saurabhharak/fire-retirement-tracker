"""Amul purchase invoices + line items CRUD service."""

import logging
from datetime import date as date_type
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services import parlours_svc
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


def _is_missing_hash_column_error(e: Exception) -> bool:
    """True when the failure is the absent source_pdf_hash column (pre-024)."""
    text = str(e)
    return "source_pdf_hash" in text and (
        "42703" in text or "PGRST204" in text or "does not exist" in text or "Could not find" in text
    )


def _serialize_dates(data: dict) -> dict:
    return {k: v.isoformat() if isinstance(v, date_type) else v for k, v in data.items()}


def _verify_membership(parlour_id: str, user_id: str, access_token: str) -> str:
    return parlours_svc._verify_parlour_membership(parlour_id, user_id, access_token)


def load_invoices(
    parlour_id: str,
    user_id: str,
    access_token: str,
    month: Optional[str] = None,
    distributor: Optional[str] = None,
) -> list[dict]:
    """Fetch invoices for a parlour (membership required)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        query = client.table("amul_invoices").select("*")
        query = query.eq("parlour_id", parlour_id)
        if month:
            query = query.gte("bill_date", f"{month}-01").lte("bill_date", f"{month}-31")
        if distributor:
            query = query.eq("distributor", distributor)
        response = query.order("bill_date", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error("Could not load invoices: %s", e)
        raise DatabaseError("Could not load invoices") from e


def get_invoice_with_items(
    invoice_id: str, parlour_id: str, user_id: str, access_token: str
) -> dict:
    """Fetch one invoice plus its line items (composite)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        invoice_resp = (
            client.table("amul_invoices")
            .select("*")
            .eq("id", invoice_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not invoice_resp.data:
            raise DataNotFoundError("Invoice not found")
        items_resp = (
            client.table("amul_invoice_items")
            .select("*")
            .eq("invoice_id", invoice_id)
            .order("sr_no", desc=False)
            .execute()
        )
        return {"invoice": invoice_resp.data[0], "items": items_resp.data or []}
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not get invoice: %s", e)
        raise DatabaseError("Could not get invoice") from e


def find_by_pdf_hash(
    parlour_id: str, file_hash: str, access_token: str
) -> list[dict]:
    """Return invoices previously created from this exact PDF (by hash).

    Membership is enforced by the upload route before this is called.
    """
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_invoices")
            .select("*")
            .eq("parlour_id", parlour_id)
            .eq("source_pdf_hash", file_hash)
            .execute()
        )
        return response.data or []
    except Exception as e:
        if _is_missing_hash_column_error(e):
            logger.warning(
                "source_pdf_hash column missing — run migration 024 to enable PDF dedup"
            )
            return []
        logger.error("Could not look up invoices by pdf hash: %s", e)
        raise DatabaseError("Could not look up invoices by pdf hash") from e


def find_duplicate(
    parlour_id: str, invoice: dict, access_token: str
) -> Optional[dict]:
    """Return an existing invoice with the same bill_no + bill_date, if any.

    Second dedup layer: catches the same invoice arriving again even when the
    file bytes differ (re-scan, re-export, combined PDF).
    """
    bill_no = invoice.get("bill_no")
    bill_date = invoice.get("bill_date")
    if not bill_no or not bill_date:
        return None
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_invoices")
            .select("*")
            .eq("parlour_id", parlour_id)
            .eq("bill_no", bill_no)
            .eq("bill_date", bill_date)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
    except Exception as e:
        logger.error("Could not look up duplicate invoice: %s", e)
        raise DatabaseError("Could not look up duplicate invoice") from e


def save_invoice_with_items(
    parlour_id: str,
    user_id: str,
    invoice: dict,
    items: list[dict],
    access_token: str,
    source_pdf_hash: Optional[str] = None,
) -> Optional[dict]:
    """Create an invoice header and its line items."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        payload = {**_serialize_dates(invoice), "parlour_id": parlour_id}
        if source_pdf_hash:
            payload["source_pdf_hash"] = source_pdf_hash
        try:
            resp = client.table("amul_invoices").insert(payload).execute()
        except Exception as e:
            if not (source_pdf_hash and _is_missing_hash_column_error(e)):
                raise
            logger.warning(
                "source_pdf_hash column missing — run migration 024; saving without hash"
            )
            payload.pop("source_pdf_hash")
            resp = client.table("amul_invoices").insert(payload).execute()
        if not resp.data:
            return None
        created = resp.data[0]
        for item in items:
            item_payload = {
                **_serialize_dates(item),
                "invoice_id": created["id"],
                "parlour_id": parlour_id,
            }
            try:
                client.table("amul_invoice_items").insert(item_payload).execute()
            except Exception as e:
                # OCR garbage in one line item (huge qty, overlong text —
                # Postgres class 22xxx) must not abort the whole upload.
                if not any(code in str(e) for code in ("22003", "22001", "22P02")):
                    raise
                logger.warning(
                    "Skipping unparseable invoice item for invoice %s: %s",
                    created["id"], e,
                )
        return created
    except Exception as e:
        logger.error("Could not save invoice: %s", e)
        raise DatabaseError("Could not save invoice") from e


def update_invoice(
    invoice_id: str,
    parlour_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Update an invoice header."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_invoices")
            .update(_serialize_dates(data))
            .eq("id", invoice_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Invoice not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update invoice: %s", e)
        raise DatabaseError("Could not update invoice") from e


def update_invoice_item(
    item_id: str,
    parlour_id: str,
    user_id: str,
    data: dict,
    access_token: str,
) -> Optional[dict]:
    """Update an invoice line item (ownership via invoice -> parlour)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        response = (
            client.table("amul_invoice_items")
            .update(_serialize_dates(data))
            .eq("id", item_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
        if not response.data:
            raise DataNotFoundError("Invoice item not found")
        return response.data[0]
    except DataNotFoundError:
        raise
    except Exception as e:
        logger.error("Could not update invoice item: %s", e)
        raise DatabaseError("Could not update invoice item") from e


def delete_invoice(
    invoice_id: str, parlour_id: str, user_id: str, access_token: str
) -> None:
    """Delete an invoice (cascades to its line items via FK)."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        (
            client.table("amul_invoices")
            .delete()
            .eq("id", invoice_id)
            .eq("parlour_id", parlour_id)
            .execute()
        )
    except Exception as e:
        logger.error("Could not delete invoice: %s", e)
        raise DatabaseError("Could not delete invoice") from e
