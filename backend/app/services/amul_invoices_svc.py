"""Amul purchase invoices + line items CRUD service."""

import logging
from datetime import date as date_type
from typing import Optional

from app.exceptions import DatabaseError, DataNotFoundError
from app.services import parlours_svc
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


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


def save_invoice_with_items(
    parlour_id: str,
    user_id: str,
    invoice: dict,
    items: list[dict],
    access_token: str,
) -> Optional[dict]:
    """Create an invoice header and its line items."""
    _verify_membership(parlour_id, user_id, access_token)
    try:
        client = get_user_client(access_token)
        payload = {**_serialize_dates(invoice), "parlour_id": parlour_id}
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
            client.table("amul_invoice_items").insert(item_payload).execute()
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
