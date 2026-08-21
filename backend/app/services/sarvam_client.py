"""Sarvam OCR client + invoice parsing for the Amul parlour module.

The heavy-tested core is parse_invoice_page(text) — a pure mapper from OCR
text to a structured invoice. The Sarvam HTTP call (call_sarvam_ocr) is a
thin httpx adapter, monkeypatched in tests. Every call is logged to
sarvam_usage so credit spend can be tracked.
"""

import logging
import re
from typing import Optional

from app.config import get_settings
from app.core.business_engine import compute_sarvam_balance
from app.exceptions import ExternalServiceError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


# ===================================================================
# Pure parsing (heavily unit-tested)
# ===================================================================

# Distributors we know how to classify from the invoice text
_DISTRIBUTOR_PATTERNS = [
    (re.compile(r"MAHAVIR", re.IGNORECASE), "M/S.MAHAVIR SUPER MARKET"),
    (re.compile(r"VASTU SHILP", re.IGNORECASE), "VASTU SHILP ENTERPRISES"),
    (re.compile(r"SHIV AGENCY", re.IGNORECASE), "SHIV AGENCY"),
]


def _to_float(value) -> float:
    """Extract a float from OCR text, tolerating ₹, commas, whitespace."""
    if value is None:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _to_int(value) -> int:
    try:
        return int(re.sub(r"[^\d]", "", str(value)) or 0)
    except (ValueError, TypeError):
        return 0


def _classify_distributor(text: str) -> str:
    for pattern, name in _DISTRIBUTOR_PATTERNS:
        if pattern.search(text):
            return name
    return ""


def _classify_invoice_type(text: str, distributor: str = "") -> str:
    """Classify tax_invoice vs bill_of_supply.

    Vastu Shilp Enterprises is a composition dealer and only issues Bills of
    Supply. Otherwise a 'BILL OF SUPPLY' heading near the seller block (not
    the footer) also indicates bill_of_supply.
    """
    if "VASTU SHILP" in distributor.upper():
        return "bill_of_supply"
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"BILL OF SUPPLY", line, re.IGNORECASE):
            nearby = "\n".join(lines[max(0, i - 5) : i + 1])
            if re.search(r"(Dist\.|Composition|Bill\s+Date)", nearby, re.IGNORECASE):
                return "bill_of_supply"
    return "tax_invoice"


def _extract_bill_no(text: str) -> Optional[str]:
    m = re.search(r"Bill\s+No[:\s]*([A-Za-z0-9\-]{3,})", text, re.IGNORECASE)
    if m:
        return m.group(1)
    # Fallback: "Bill No: AMUL2602568" may be split across tokens
    m = re.search(r"Bill\s*No[:\s]*([A-Z]{2,}\d+)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    # Shiv Agency invoices use "Invoice No : 3987"
    m = re.search(r"Invoice\s*No[:\s]*([A-Za-z0-9\-]{3,})", text, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_bill_date(text: str) -> Optional[str]:
    m = re.search(r"Bill\s+Date[:\s]*(\d{2})/(\d{2})/(\d{4})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Invoice\s+Date[:\s]*(\d{2})/(\d{2})/(\d{4})", text, re.IGNORECASE)
    if not m:
        return None
    day, month, year = m.group(1), m.group(2), m.group(3)
    try:
        return f"{year}-{month}-{day}"
    except ValueError:
        return None


def _extract_total_amount(text: str) -> float:
    """Extract the invoice total.

    Real OCR puts 'Total:-' and the amount on separate lines, and repeats
    totals in words. Sarvam HTML puts the total in the LAST cell of the
    tfoot row. Strategy:
      1. For HTML: find a <tfoot> row containing 'Total' and take its last
         decimal amount; fall back to the largest decimal in the whole tfoot.
      2. Else: prefer a decimal amount on the same line as 'Total', else the
         largest amount within the next 3 lines.
    """
    if "<tfoot" in text.lower():
        for tfoot in re.finditer(r"<tfoot[^>]*>(.*?)</tfoot>", text, re.DOTALL | re.IGNORECASE):
            for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", tfoot.group(1), re.DOTALL | re.IGNORECASE):
                row_text = re.sub(r"<[^>]+>", " ", row.group(1))
                if "total" in row_text.lower():
                    values = [float(v.replace(",", "")) for v in re.findall(r"\d+(?:,\d{3})*\.\d{2}", row_text)]
                    if values:
                        return max(values)
            # No row had 'Total' labelled; take the largest decimal in tfoot
            tfoot_text = re.sub(r"<[^>]+>", " ", tfoot.group(1))
            values = [float(v.replace(",", "")) for v in re.findall(r"\d+(?:,\d{3})*\.\d{2}", tfoot_text)]
            if values:
                return max(values)
        return 0.0

    lines = text.splitlines()
    same_line: list[float] = []
    candidates: list[float] = []
    for i, line in enumerate(lines):
        if not re.search(r"Total", line, re.IGNORECASE):
            continue
        for m in re.finditer(r"\d+(?:,\d{3})*\.\d{2}", line):
            same_line.append(_to_float(m.group(0)))
        window = "\n".join(lines[i : i + 4])
        for m in re.finditer(r"\d+(?:,\d{3})*\.\d{2}", window):
            candidates.append(_to_float(m.group(0)))
    if same_line:
        return max(same_line)
    return max(candidates, default=0.0)


def _extract_tax_breakdown(text: str) -> tuple[float, float]:
    """Return (taxable_amount, tax_amount) from CGST/SGST lines.

    Works for both pipe-delimited OCR ("CGST 2.50% 41.95") and Sarvam HTML
    cells ("<td>Tax Desc- CGST 2.50%</td><td>Tax Amt 41.95</td>").
    """
    taxable = 0.0
    tax = 0.0
    # Taxable amount (may be in "Taxable Amt 1677.98" or a cell after it)
    taxable_m = re.search(r"Taxable\s*Amt[:\s]*([\d.]+)", text, re.IGNORECASE)
    if taxable_m:
        taxable = _to_float(taxable_m.group(1))
    # Sum CGST + SGST tax amounts. Handle "CGST 2.50% 41.95" and
    # "CGST 2.50% <br/> Tax Amt 41.95" (HTML cell boundary).
    for m in re.finditer(
        r"(CGST|SGST)[^0-9]*([\d.]+)%[^0-9]{0,80}?(\d+(?:\.\d+)?)",
        text, re.IGNORECASE,
    ):
        tax += _to_float(m.group(3))
    return taxable, tax


def _parse_html_tables(text: str) -> list[list[list[str]]]:
    """Extract all HTML tables as lists of rows (each row = list of cell texts)."""
    tables: list[list[list[str]]] = []
    for table_match in re.finditer(r"<table[^>]*>(.*?)</table>", text, re.DOTALL | re.IGNORECASE):
        rows: list[list[str]] = []
        for row_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.DOTALL | re.IGNORECASE):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_match.group(1), re.DOTALL | re.IGNORECASE)
            cleaned = [re.sub(r"<[^>]+>", " ", c).strip() for c in cells]
            rows.append(cleaned)
        tables.append(rows)
    return tables


def _is_amul_layout(header_row: list[str]) -> bool:
    """Amul invoices have a 'Description' + 'Net Amt' header."""
    joined = " ".join(header_row).lower()
    return "description" in joined and "net amt" in joined


def _parse_items_from_html_tables(text: str) -> list[dict]:
    """Parse line items from Sarvam's HTML-table digitise blocks.

    Handles both the Amul layout (Sr|HSN|Description|MRP|Rate|Box|Pcs|...|Net)
    and the Shiv Agency layout (Sr|Name of Product|HSN|Mrp|...|Rate|...|Total).
    """
    items: list[dict] = []
    for rows in _parse_html_tables(text):
        if not rows:
            continue
        header = rows[0]
        # Find the header row that describes the columns (first with >2 cells)
        body_start = 1
        for idx, row in enumerate(rows):
            if len(row) >= 4 and any("description" in c.lower() or "product" in c.lower() for c in row):
                header = row
                body_start = idx + 1
                break
        amul = _is_amul_layout(header)

        def _col(name: str) -> int:
            for i, c in enumerate(header):
                if name.lower() in c.lower():
                    return i
            return -1

        desc_idx = _col("description") if amul else _col("product")
        if desc_idx < 0:
            desc_idx = _col("name of") if not amul else desc_idx
        net_idx = _col("net amt") if amul else _col("total")
        rate_idx = _col("rate")

        for row in rows[body_start:]:
            if len(row) < 3:
                continue
            # Skip totals/foot rows
            if any(k in row[0].lower() for k in ("tax summary", "total:-", "wd bank", "tax desc")):
                continue
            description = ""
            if desc_idx >= 0 and desc_idx < len(row):
                description = row[desc_idx]
            if not description or not description[0].isalpha():
                # Some rows merge sr+hsn into first cell; description is 2nd
                description = row[1] if len(row) > 1 else ""
            # Amul descriptions often start with the HSN: "1806 Amul ..."
            if not description or not any(c.isalpha() for c in description):
                continue
            net = _to_float(row[net_idx]) if 0 <= net_idx < len(row) else 0.0
            rate = _to_float(row[rate_idx]) if 0 <= rate_idx < len(row) else 0.0
            sr = _to_int(row[0]) if row and row[0].strip().split() else 0
            # hsn: for Amul it's merged into description ("1806 Amul ...")
            m = re.match(r"^(\d{3,8})\s+(.*)$", description)
            hsn = m.group(1) if m else ""
            desc_clean = m.group(2) if m else description
            items.append(
                {
                    "sr_no": sr or len(items) + 1,
                    "hsn": hsn,
                    "description": desc_clean,
                    "mrp": 0.0,
                    "rate": rate,
                    "box_qty": 0,
                    "pcs_qty": 0,
                    "free_qty": 0,
                    "scheme": "",
                    "discount": 0.0,
                    "gst_pct": 0.0,
                    "gst_amount": 0.0,
                    "net_amount": net,
                }
            )
    return items


def _parse_items(text: str) -> list[dict]:
    """Extract line items from a scanned invoice's OCR text.

    The real Amul scans are pipe-delimited tables (Docling/Sarvam output
    keeps the pipes). Best-effort: returns [] when nothing can be parsed.
    """
    items: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 4:
            continue
        # Skip header rows
        if cells[0].lower().startswith("sr") or cells[0].lower().startswith("fssai"):
            continue
        # Expect: [sr [hsn], description, ..., rate, ..., net]
        sr = _to_int(cells[0].split()[0]) if cells[0].split() else 0
        if sr < 1:
            continue
        rest = cells[1:]
        description = rest[0]
        if not description or not description[0].isalpha():
            # sr and hsn may be merged in one cell, e.g. "1 1806"
            hsn_candidate = cells[0].split()[-1] if len(cells[0].split()) > 1 else ""
            description = rest[0]
            hsn = hsn_candidate
        else:
            hsn = ""
        # numbers after description: [mrp] rate [box] [pcs] ... net
        numbers = [_to_float(c) for c in rest[1:]]
        numbers = [n for n in numbers if n > 0]
        if not numbers:
            continue
        net_amount = numbers[-1]
        # Column order is MRP | Rate | ... | Net, so the rate is the second
        # positive number after the description (skip MRP) when present.
        rate = numbers[1] if len(numbers) >= 3 else numbers[0]
        # Integer-looking values between rate and net are box/pcs quantities.
        box_qty = 0
        pcs_qty = 0
        mid = numbers[1:-1]
        ints = [n for n in mid if n == int(n) and n < 1000]
        if ints:
            box_qty = int(ints[0])
            if len(ints) > 1:
                pcs_qty = int(ints[1])
        items.append(
            {
                "sr_no": sr,
                "hsn": hsn,
                "description": description,
                "mrp": numbers[0],
                "rate": rate,
                "box_qty": box_qty,
                "pcs_qty": pcs_qty,
                "free_qty": 0,
                "scheme": "",
                "discount": 0.0,
                "gst_pct": 0.0,
                "gst_amount": 0.0,
                "net_amount": net_amount,
            }
        )
    return items


def parse_invoice_page(text: str) -> dict:
    """Parse a single OCR'd invoice page into a structured invoice dict.

    Pure function — no I/O. Returns:
    {distributor, bill_no, bill_date, invoice_type, items[], total_amount,
     tax_amount, taxable_amount, status, warning}
    """
    if not text or not text.strip():
        return {
            "distributor": "", "bill_no": None, "bill_date": None,
            "invoice_type": "tax_invoice", "items": [],
            "total_amount": 0.0, "tax_amount": 0.0, "taxable_amount": 0.0,
            "status": "partial", "warning": "Empty OCR text",
        }

    distributor = _classify_distributor(text)
    invoice_type = _classify_invoice_type(text, distributor)
    bill_no = _extract_bill_no(text)
    bill_date = _extract_bill_date(text)
    total_amount = _extract_total_amount(text)
    taxable_amount, tax_amount = _extract_tax_breakdown(text)
    if "<table" in text.lower():
        items = _parse_items_from_html_tables(text)
    else:
        items = _parse_items(text)

    # Cross-check stated total against item sum; flag mismatch, don't fail
    warning = None
    item_sum = round(sum(i["net_amount"] for i in items), 2)
    if items and item_sum and abs(item_sum - total_amount) > 0.5:
        warning = (
            f"Item sum ({item_sum}) differs from stated total ({total_amount})"
        )

    status = "success" if distributor or bill_no or items else "partial"
    return {
        "distributor": distributor,
        "bill_no": bill_no,
        "bill_date": bill_date,
        "invoice_type": invoice_type,
        "items": items,
        "total_amount": round(total_amount, 2),
        "tax_amount": round(tax_amount, 2),
        "taxable_amount": round(taxable_amount, 2),
        "status": status,
        "warning": warning,
    }


# ===================================================================
# Sarvam Document AI adapters (job lifecycle, monkeypatched in tests)
#
# Real API contract (docs.sarvam.ai/api-reference/doc-ai):
#   POST /doc-ai/v1/job/digitise   -> {job_id, status, run_id}
#   GET  /doc-ai/v1/job/{id}/status -> {status, usage:{pages_*}}
#   GET  /doc-ai/v1/job/{id}/results?format=json
#        -> {documents:[{pages:[{blocks:[{text, layout_tag}]}]}], usage}
#   Auth header: api-subscription-key: <key>
#   PDF limit: 10 pages per job -> larger PDFs are split into batches.
# ===================================================================

SARVAM_MAX_PAGES_PER_JOB = 10


def _headers(settings) -> dict:
    return {"api-subscription-key": settings.sarvam_api_key}


def _split_pdf_batches(pdf_bytes: bytes, max_pages: int = SARVAM_MAX_PAGES_PER_JOB) -> list[bytes]:
    """Split a multi-page PDF into batches of <= max_pages pages.

    Sarvam caps a digitise job at 10 pages, so a 21-page invoice bundle
    becomes 3 batches (10/10/1). Uses pymupdf to write partial PDFs.
    """
    try:
        import fitz  # pymupdf
    except ImportError as e:
        raise ExternalServiceError("pymupdf not available for PDF batching") from e

    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = src.page_count
    if total <= max_pages:
        src.close()
        return [pdf_bytes]

    batches: list[bytes] = []
    try:
        for start in range(0, total, max_pages):
            end = min(start + max_pages, total)
            out = fitz.open()
            out.insert_pdf(src, from_page=start, to_page=end - 1)
            batches.append(out.tobytes())
            out.close()
    finally:
        src.close()
    return batches


def _create_digitise_job(pdf_batch: bytes, settings=None) -> str:
    """POST a PDF batch to Sarvam digitise. Returns the job_id."""
    settings = settings or get_settings()
    if not settings.sarvam_api_key:
        raise ExternalServiceError("SARVAM_API_KEY is not configured")

    import httpx

    url = f"{settings.sarvam_base_url.rstrip('/')}/doc-ai/v1/job/digitise"
    try:
        resp = httpx.post(
            url,
            headers=_headers(settings),
            files={"file": ("document.pdf", pdf_batch, "application/pdf")},
            data={"language": "en-IN", "output_format": "md"},
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Sarvam digitise job creation failed: %s", e)
        raise ExternalServiceError("Sarvam digitise job creation failed") from e

    job_id = data.get("job_id")
    if not job_id:
        raise ExternalServiceError("Sarvam digitise response missing job_id")
    return job_id


def _poll_job_status(job_id: str, settings=None, timeout_seconds: int = 300) -> dict:
    """Poll the digitise job until a terminal status. Returns the status dict."""
    settings = settings or get_settings()
    import time

    import httpx

    url = f"{settings.sarvam_base_url.rstrip('/')}/doc-ai/v1/job/{job_id}/status"
    terminal = {"completed", "partially_completed", "failed", "rejected"}
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            resp = httpx.get(url, headers=_headers(settings), timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("Sarvam status poll failed: %s", e)
            time.sleep(3)
            continue
        if data.get("status", "").lower() in terminal:
            return data
        time.sleep(5)
    raise ExternalServiceError("Sarvam digitise job timed out")


def _fetch_digitise_results(job_id: str, settings=None) -> dict:
    """Fetch digitise results JSON: {documents: [...], usage: {pages_*}}."""
    settings = settings or get_settings()
    import httpx

    url = f"{settings.sarvam_base_url.rstrip('/')}/doc-ai/v1/job/{job_id}/results"
    try:
        resp = httpx.get(
            url, headers=_headers(settings), params={"format": "json"}, timeout=60.0
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.error("Sarvam digitise results fetch failed: %s", e)
        raise ExternalServiceError("Sarvam digitise results fetch failed") from e


def _flatten_digitise_pages(results: dict) -> list[str]:
    """Flatten Sarvam digitise blocks into per-page text.

    Results shape: {documents: [{pages: [{page_num, blocks: [{text,
    layout_tag, reading_order}]}]}]}. Blocks are concatenated in reading
    order; HTML tables keep their structure (the parser handles them).
    """
    pages: list[str] = []
    for doc in results.get("documents", []):
        for page in doc.get("pages", []):
            blocks = page.get("blocks", [])
            blocks.sort(key=lambda b: b.get("reading_order", 0))
            text = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
            pages.append(text)
    return pages


def _docling_ocr(pdf_bytes: bytes) -> str:
    """Free local OCR fallback via Docling (no Sarvam credits consumed)."""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as e:
        raise ExternalServiceError("docling not installed for fallback OCR") from e

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        return result.document.export_to_markdown()
    finally:
        import os
        os.unlink(tmp_path)


def log_sarvam_usage(
    parlour_id: str,
    endpoint: str,
    request_id: Optional[str],
    credits_used: float,
    cost_estimate_inr: float,
    purpose: str,
    pages: int,
    status: str,
    error: Optional[str] = None,
    access_token: str = "",
) -> None:
    """Fire-and-forget usage logging (never raises)."""
    try:
        client = get_user_client(access_token) if access_token else None
        if client is None:
            return
        client.table("sarvam_usage").insert(
            {
                "parlour_id": parlour_id,
                "endpoint": endpoint,
                "request_id": request_id,
                "purpose": purpose,
                "pages": pages,
                "credits_used": credits_used,
                "cost_estimate_inr": cost_estimate_inr,
                "status": status,
                "error_message": error,
            }
        ).execute()
    except Exception as e:
        logger.warning("Sarvam usage log failed (non-blocking): %s", e)


def extract_invoices_from_pdf(
    pdf_bytes: bytes,
    parlour_id: str,
    user_id: str,
    access_token: str,
    use_docling: bool = False,
    source_pdf: Optional[str] = None,
) -> dict:
    """OCR a purchase PDF and return structured invoices + credit usage.

    use_docling=True uses the free local Docling OCR (credits_used=0).
    Sarvam path: split the PDF into <=10-page batches, run a digitise job per
    batch (create -> poll -> results), and log usage per batch.
    """
    settings = get_settings()
    status = "success"
    error = None
    if use_docling:
        text = _docling_ocr(pdf_bytes)
        credits_used = 0.0
        request_id = None
        source = "docling"
        log_sarvam_usage(
            parlour_id, "docling_ocr", None, 0.0, 0.0,
            "PDF extraction (Docling fallback)", 1, "success",
            access_token=access_token,
        )
    else:
        batches = _split_pdf_batches(pdf_bytes)
        text_parts = []
        credits_used = 0.0
        request_ids: list[str] = []
        total_pages = 0
        try:
            for batch in batches:
                job_id = _create_digitise_job(batch, settings)
                request_ids.append(job_id)
                status_resp = _poll_job_status(job_id, settings)
                usage = status_resp.get("usage", {})
                pages_in_batch = int(usage.get("pages_total") or usage.get("pages_processed") or 1)
                total_pages += pages_in_batch
                results = _fetch_digitise_results(job_id, settings)
                # Sarvam reports no monetary credit figure in the response; we
                # conservatively estimate 1 credit per processed page.
                credits_used += float(pages_in_batch)
                text_parts.extend(_flatten_digitise_pages(results))
        except Exception as e:  # noqa: BLE001 - OCR failure must not crash the upload
            status = "error"
            # Canned type name only: str(e) could embed internal URLs/details
            # that end up owner-readable in sarvam_usage.error_message.
            error = type(e).__name__
            logger.error("Sarvam digitise failed for parlour %s: %s", parlour_id, e)
        request_id = ",".join(request_ids) if request_ids else f"sarvam-{parlour_id[:8]}"
        log_sarvam_usage(
            parlour_id, "sarvam_digitise", request_id, credits_used,
            round(credits_used * 0.05, 2), "PDF purchase extraction",
            max(total_pages, 1), status, error=error, access_token=access_token,
        )
        text = "\n\n".join(text_parts)
        source = "sarvam"

    if status == "error":
        return {
            "invoices": [], "credits_used": credits_used,
            "request_id": request_id, "status": "error", "source": source,
        }

    # Each digitise document is one page (typically one invoice). Docling text
    # may contain several invoices — split by distributor headers.
    if use_docling:
        chunks = split_invoice_chunks(text)
        parsed = [parse_invoice_page(chunk) for chunk in chunks]
    else:
        parsed = [parse_invoice_page(page_text) for page_text in text_parts if page_text.strip()]
    parsed = [p for p in parsed if p["status"] != "partial" or p["items"]]
    if not parsed:
        parsed = [parse_invoice_page(text)]
    return {
        "invoices": parsed,
        "credits_used": credits_used,
        "request_id": request_id,
        "status": "success" if all(p["status"] == "success" for p in parsed) else "partial",
        "source": source,
    }


def split_invoice_chunks(text: str) -> list[str]:
    """Split concatenated OCR text into per-invoice chunks.

    Each new distributor header or "Bill Date:" line begins a new invoice.
    Falls back to the whole text as one chunk.
    """
    lines = text.splitlines()
    start_indices: list[int] = []
    for i, line in enumerate(lines):
        if re.search(r"Dist\.?\s*[:：]", line, re.IGNORECASE) and re.search(
            r"(MAHAVIR|VASTU)", line, re.IGNORECASE
        ):
            start_indices.append(i)
        elif re.search(r"Bill\s+Date[:：]", line, re.IGNORECASE) and start_indices:
            # A new Bill Date after we already have a header starts a new invoice
            pass
    if not start_indices:
        return [text]

    chunks: list[str] = []
    for idx, start in enumerate(start_indices):
        end = start_indices[idx + 1] if idx + 1 < len(start_indices) else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text]


def get_sarvam_balance(parlour_id: str, user_id: str, access_token: str) -> dict:
    """Compute starting - used credits for a parlour."""
    client = get_user_client(access_token)
    parlour_resp = (
        client.table("parlours")
        .select("sarvam_starting_credits")
        .eq("id", parlour_id)
        .execute()
    )
    if not parlour_resp.data:
        return {
            "starting": 0.0, "used": 0.0, "remaining": 0.0,
            "call_count": 0, "cost_inr": 0.0,
        }
    starting = float(parlour_resp.data[0].get("sarvam_starting_credits", 0))
    usage_resp = (
        client.table("sarvam_usage")
        .select("credits_used,cost_estimate_inr")
        .eq("parlour_id", parlour_id)
        .execute()
    )
    return compute_sarvam_balance(starting, usage_resp.data or [])
