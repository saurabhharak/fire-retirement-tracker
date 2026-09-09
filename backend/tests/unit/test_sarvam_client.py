"""Unit tests for the Sarvam OCR client.

The parse_invoice_page pure mapper is the heavy-tested core. OCR snippets
are representative of the real Amul invoice scans, in BOTH formats the
client can receive: pipe-delimited (Docling fallback) and HTML tables
(Sarvam digitise blocks). The HTTP/job adapters are monkeypatched.
"""

import pytest

from app.services import sarvam_client
from app.services.sarvam_client import merge_page_invoices


# ===================================================================
# Representative OCR text (pipe-delimited — Docling fallback)
# ===================================================================
MAHAVIR_OCR = """
Dist.: M/S.MAHAVIR SUPER MARKET SHOP NO. 10 & 11, MORKYA PARK
| Sr. HSN | Description | MRP | Rate | Box | Pcs | Scheme | Disc | GST% | GST | Net Amt |
| 1 1806 | Amul Bindaaz Wafer Choco 6x75x12 Gm Jar | 5.00 | 3.97 | 1 | | | | 5.0 | 14.88 | 312.38 |
| 2 1905 | Amul Butter Cake Choco Walnut 24x150 Gm | 100.00 | 76.19 | | 4 | | | 5.0 | 15.24 | 320.00 |
Bill No: AMUL2602568 Bill Date:01/07/2026
Total:- 1761.88
CGST 2.50% 41.95 SGST 2.50% 41.95
Taxable Amt 1677.98
"""

VASTU_OCR = """
## Dist.: VASTU SHILP ENTERPRISES
Bill Date:02/07/2026
| Sr. HSN | Description | MRP | Rate | Box | Pcs | Free | CD | Scheme | Disc | Net Amt |
| 1 2105 | Amul IC BP Vanilla 5 L (1x6) | 600.00 | 495.00 | 1 | | | | | | 495.00 |
| 2 2105 | Amul IC Jumbo Cup Fr N Nut F 125ml(8x9) | | 28.88 | 2 | | | | | | 462.00 |
Total:- 2850.54
Bill of Supply
"""


# ===================================================================
# Representative OCR text (HTML tables — Sarvam digitise blocks)
# ===================================================================
MAHAVIR_HTML = """Page 1 of 1
<table>
<thead><tr><th>Sr. HSN</th><th>Description</th><th>MRP</th><th>Rate</th><th>Box</th><th>Pcs</th><th>Free</th><th>Scheme</th><th>Disc</th><th>GST%</th><th>GST</th><th>Net Amt</th></tr></thead>
<tbody>
<tr><td>1</td><td>1806 Amul Bindaaz Wafer Choco 6x75x12 Gm Jar</td><td>5.00</td><td>3.97</td><td>1</td><td></td><td></td><td></td><td></td><td>5.0</td><td>14.88</td><td>312.38</td></tr>
<tr><td>2</td><td>1905 Amul Butter Cake Choco Walnut 24x150 Gm</td><td>100.00</td><td>76.19</td><td></td><td>4</td><td></td><td></td><td></td><td>5.0</td><td>15.24</td><td>320.00</td></tr>
</tbody>
<tfoot>
<tr><td colspan="11">Tax Summary Total:- 2 7 0 0.00 0.00 / 83.90 1761.88</td></tr>
<tr><td colspan="4">Tax Desc- CGST 2.50%</td><td>Tax Amt 41.95</td><td>Taxable Amt 1677.98</td><td>Tax Desc SGST 2.50%</td><td>Tax Amt 41.95</td><td>Taxable Amt 1677.98</td></tr>
</tfoot>
</table>
Certified that the Particulars given above are true and correct
"""

SHIV_HTML = """SHIV AGENCY
Takli Road, Dwarka ,NASHIK 11 MOB. 9518909483.
TAX INVOICE
GSTIN : 27ANAPM6023E1ZD
<table>
<thead><tr><th colspan="12">VRINDAVAN TREATS APO..BHGR</th></tr>
<tr><td colspan="3">Salesman : AMUL</td><td colspan="3">Party No: 7796902555</td><td colspan="4">Invoice Date : 03/07/2026</td></tr>
<tr><th>Sr.</th><th>Name of Product</th><th>HSN /ACS</th><th>Mrp</th><th>Cases</th><th>Bx/Qty</th><th>Qty</th><th>UOM</th><th>Rate</th><th>Gross amt</th><th>Dis Am</th><th>Cd Am</th><th>GST %</th><th>Total</th></tr>
</thead>
<tbody>
<tr><td>1</td><td>AMUL HIGH AROMA COW GHEE 1LTIN</td><td>040590</td><td>550.00</td><td>1</td><td></td><td></td><td></td><td>520.00</td><td>520.00</td><td></td><td></td><td>5.0</td><td>520.00</td></tr>
</tbody>
</table>
"""


# ===================================================================
# parse_invoice_page
# ===================================================================
class TestParseInvoicePage:
    def test_extracts_mahavir_distributor(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert "MAHAVIR" in result["distributor"].upper()

    def test_extracts_vastu_shilp_distributor(self):
        result = sarvam_client.parse_invoice_page(VASTU_OCR)
        assert "VASTU SHILP" in result["distributor"].upper()

    def test_extracts_bill_no_from_tax_invoice(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert result["bill_no"] == "AMUL2602568"

    def test_bill_no_none_for_bill_of_supply(self):
        result = sarvam_client.parse_invoice_page(VASTU_OCR)
        assert result["bill_no"] is None

    def test_extracts_bill_date_ddmmyyyy_to_iso(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert result["bill_date"] == "2026-07-01"

    def test_classifies_tax_invoice_vs_bill_of_supply(self):
        assert sarvam_client.parse_invoice_page(MAHAVIR_OCR)["invoice_type"] == "tax_invoice"
        assert sarvam_client.parse_invoice_page(VASTU_OCR)["invoice_type"] == "bill_of_supply"

    def test_extracts_line_items_with_description_rate_qty_net(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        items = result["items"]
        assert len(items) == 2
        first = items[0]
        assert first["description"] == "Amul Bindaaz Wafer Choco 6x75x12 Gm Jar"
        assert first["rate"] == pytest.approx(3.97)
        assert first["box_qty"] == 1
        assert first["net_amount"] == pytest.approx(312.38)

    def test_extracts_total_amount(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert result["total_amount"] == pytest.approx(1761.88)

    def test_extracts_taxable_and_tax_amount(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert result["taxable_amount"] == pytest.approx(1677.98)
        assert result["tax_amount"] == pytest.approx(83.90)  # 41.95 + 41.95

    def test_total_cross_checks_against_item_sum_flags_warning(self):
        # Item sum is 632.38, stated total is 1761.88 -> mismatch warning
        result = sarvam_client.parse_invoice_page(MAHAVIR_OCR)
        assert result["total_amount"] == pytest.approx(1761.88)
        assert result["warning"] is not None

    def test_bill_of_supply_tax_zero(self):
        result = sarvam_client.parse_invoice_page(VASTU_OCR)
        assert result["tax_amount"] == 0
        assert result["taxable_amount"] == 0

    def test_handles_malformed_ocr_returns_partial_with_status(self):
        result = sarvam_client.parse_invoice_page("garbage text no invoice")
        assert result["status"] == "partial"
        assert result["items"] == []

    def test_empty_text_returns_empty_items(self):
        result = sarvam_client.parse_invoice_page("")
        assert result["items"] == []
        assert result["bill_no"] is None


# ===================================================================
# parse_invoice_page — HTML table format (Sarvam digitise blocks)
# ===================================================================
class TestParseHtmlInvoicePage:
    def test_extracts_items_from_html_table(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_HTML)
        assert len(result["items"]) == 2
        first = result["items"][0]
        assert first["description"] == "Amul Bindaaz Wafer Choco 6x75x12 Gm Jar"
        assert first["rate"] == pytest.approx(3.97)
        assert first["net_amount"] == pytest.approx(312.38)

    def test_extracts_total_and_tax_from_html_tfoot(self):
        result = sarvam_client.parse_invoice_page(MAHAVIR_HTML)
        assert result["total_amount"] == pytest.approx(1761.88)
        assert result["taxable_amount"] == pytest.approx(1677.98)
        assert result["tax_amount"] == pytest.approx(83.90)

    def test_extracts_distributor_from_html_paragraph(self):
        # Note: real Sarvam digitise often drops the Amul header block, so
        # this asserts the Shiv Agency case where the distributor IS present.
        result = sarvam_client.parse_invoice_page(SHIV_HTML)
        assert "SHIV AGENCY" in result["distributor"].upper()

    def test_shiv_agency_format_items(self):
        result = sarvam_client.parse_invoice_page(SHIV_HTML)
        assert len(result["items"]) == 1
        first = result["items"][0]
        assert first["description"] == "AMUL HIGH AROMA COW GHEE 1LTIN"
        assert first["rate"] == pytest.approx(520.00)
        assert first["net_amount"] == pytest.approx(520.00)

    def test_shiv_agency_distributor_detected(self):
        result = sarvam_client.parse_invoice_page(SHIV_HTML)
        assert "SHIV AGENCY" in result["distributor"].upper()

    def test_html_with_no_items_returns_partial(self):
        result = sarvam_client.parse_invoice_page("<table><tr><td>x</td></tr></table>")
        assert result["status"] == "partial"


# ===================================================================
# extract_invoices_from_pdf (Sarvam job lifecycle + batch splitting)
# ===================================================================
def _fake_digitise_results(text: str) -> dict:
    """Simulate the real Sarvam digitise results payload (blocks per page)."""
    return {
        "documents": [
            {
                "filename": "document.pdf",
                "page_count": 1,
                "status": "completed",
                "pages": [
                    {
                        "page_num": 1,
                        "blocks": [{"block_id": "p1-b1", "text": text, "layout_tag": "table", "reading_order": 1}],
                    }
                ],
            }
        ],
        "usage": {"pages_total": 1, "pages_processed": 1, "pages_succeeded": 1, "pages_failed": 0},
    }


class TestExtractInvoicesFromPdf:
    def test_splits_pdf_into_10_page_batches(self, monkeypatch):
        """Sarvam caps PDFs at 10 pages; a 21-page PDF must be batched."""
        batch_count = []

        def _fake_create_job(pdf_batch, settings=None):
            batch_count.append(1)
            return "job-1"

        def _fake_poll(job_id, settings=None):
            return {"job_id": job_id, "status": "completed",
                    "usage": {"pages_total": 1, "pages_processed": 1}}

        def _fake_results(job_id, settings=None):
            return _fake_digitise_results(MAHAVIR_OCR)

        monkeypatch.setattr(sarvam_client, "_create_digitise_job", _fake_create_job)
        monkeypatch.setattr(sarvam_client, "_poll_job_status", _fake_poll)
        monkeypatch.setattr(sarvam_client, "_fetch_digitise_results", _fake_results)
        monkeypatch.setattr(sarvam_client, "log_sarvam_usage", lambda *a, **k: None)
        monkeypatch.setattr(
            sarvam_client, "_split_pdf_batches",
            lambda pdf_bytes, max_pages=10: [b"batch1", b"batch2", b"batch3"],
        )

        result = sarvam_client.extract_invoices_from_pdf(b"pdf", "p1", "u1", "tok")
        assert result["status"] in ("success", "partial")
        assert batch_count == [1, 1, 1]  # one digitise job per batch

    def test_logs_sarvam_usage_with_credits(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sarvam_client, "_split_pdf_batches", lambda pdf_bytes, max_pages=10: [b"batch1"])
        monkeypatch.setattr(sarvam_client, "_create_digitise_job", lambda *a, **k: "job-1")
        monkeypatch.setattr(
            sarvam_client, "_poll_job_status",
            lambda *a, **k: {"job_id": "job-1", "status": "completed",
                             "usage": {"pages_total": 1, "pages_processed": 1}},
        )
        monkeypatch.setattr(
            sarvam_client, "_fetch_digitise_results",
            lambda *a, **k: _fake_digitise_results(MAHAVIR_OCR),
        )
        monkeypatch.setattr(
            sarvam_client, "log_sarvam_usage",
            lambda *a, **k: calls.append((a, k)),
        )
        sarvam_client.extract_invoices_from_pdf(b"pdf", "p1", "u1", "tok")
        assert len(calls) == 1
        assert calls[0][0][3] == pytest.approx(1.0)  # 1 page, 1 credit

    def test_use_docling_flag_avoids_sarvam_call(self, monkeypatch):
        called = {"sarvam": False}
        monkeypatch.setattr(
            sarvam_client, "_create_digitise_job",
            lambda *a, **k: called.__setitem__("sarvam", True) or "job-1",
        )
        monkeypatch.setattr(sarvam_client, "_docling_ocr", lambda pdf_bytes: VASTU_OCR)
        monkeypatch.setattr(sarvam_client, "log_sarvam_usage", lambda *a, **k: None)
        result = sarvam_client.extract_invoices_from_pdf(
            b"pdf", "p1", "u1", "tok", use_docling=True
        )
        assert called["sarvam"] is False
        assert result["credits_used"] == 0

    def test_ocr_error_still_logs_usage_with_status_error(self, monkeypatch):
        logs = []
        monkeypatch.setattr(sarvam_client, "_split_pdf_batches", lambda pdf_bytes, max_pages=10: [b"batch1"])
        monkeypatch.setattr(
            sarvam_client, "_create_digitise_job",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        monkeypatch.setattr(
            sarvam_client, "log_sarvam_usage",
            lambda *a, **k: logs.append(a),
        )
        result = sarvam_client.extract_invoices_from_pdf(b"pdf", "p1", "u1", "tok")
        assert result["status"] == "error"
        assert logs and logs[0][7] == "error"  # positional arg 8 = status


# ===================================================================
# log_sarvam_usage (DB-mocked)
# ===================================================================
class TestLogSarvamUsage:
    def test_inserts_usage_row(self, monkeypatch):
        class _FakeClient:
            def __init__(self):
                self.calls = []

            def table(self, name):
                self.calls.append(name)
                return self

            def insert(self, payload):
                self.calls.append(payload)
                return self

            def execute(self):
                class _Resp:
                    data = [{}]
                return _Resp()

        fake = _FakeClient()
        monkeypatch.setattr(sarvam_client, "get_user_client", lambda token: fake)
        sarvam_client.log_sarvam_usage(
            "p1", "ocr", "req-1", 2.0, 0.1, "pdf upload", 1, "success",
            access_token="tok",
        )
        assert fake.calls[0] == "sarvam_usage"
        assert fake.calls[1]["credits_used"] == 2.0


# ===================================================================
# get_sarvam_balance (DB-mocked + pure compute_sarvam_balance)
# ===================================================================
class TestGetSarvamBalance:
    def test_starting_minus_used(self, monkeypatch):
        class _FakeClient:
            def __init__(self, rows_by_table):
                self._rows_by_table = rows_by_table

            def table(self, name):
                self._table = name
                return self

            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def order(self, *a, **k): return self

            def execute(self):
                class _Resp:
                    data = self._rows_by_table.get(self._table, [])
                return _Resp()

        usage_rows = [
            {"credits_used": 2, "cost_estimate_inr": 0.1},
            {"credits_used": 3, "cost_estimate_inr": 0.15},
        ]
        fake = _FakeClient(
            {
                "parlours": [{"sarvam_starting_credits": 10}],
                "sarvam_usage": usage_rows,
            }
        )
        monkeypatch.setattr(sarvam_client, "get_user_client", lambda token: fake)

        result = sarvam_client.get_sarvam_balance("p1", "u1", "tok")
        assert result["starting"] == 10
        assert result["used"] == 5
        assert result["remaining"] == 5


# ===================================================================
# merge_page_invoices — multi-page scan handling
# ===================================================================
class TestMergePageInvoices:
    def _page(self, date=None, bill_no=None, items=None, total=0.0, page_no=None):
        return {
            "distributor": "SHIV AGENCY", "bill_no": bill_no, "bill_date": date,
            "invoice_type": "tax_invoice", "items": items or [],
            "total_amount": total, "tax_amount": 0.0, "taxable_amount": 0.0,
            "page_no": page_no, "status": "success", "warning": None,
        }

    def test_continuation_merges_into_dated_header(self):
        pages = [
            self._page(date="2026-07-27", bill_no="AMUL1", items=[{"sr_no": 1}], total=0.0),
            self._page(items=[{"sr_no": 2}, {"sr_no": 3}], total=8220.13, page_no=2),  # page 2 of 2
        ]
        invoices, skipped = merge_page_invoices(pages)
        assert len(invoices) == 1
        assert len(invoices[0]["items"]) == 3
        assert invoices[0]["bill_date"] == "2026-07-27"
        assert invoices[0]["total_amount"] == 8220.13  # running total from last page
        assert skipped == 0

    def test_headerless_page_before_any_invoice_is_skipped(self):
        pages = [
            self._page(items=[{"sr_no": 1}], total=1761.88),
            self._page(date="2026-07-03", items=[{"sr_no": 2}], total=5962.16),
        ]
        invoices, skipped = merge_page_invoices(pages)
        assert len(invoices) == 1
        assert invoices[0]["bill_date"] == "2026-07-03"
        assert skipped == 1

    def test_standalone_undated_page_not_merged(self):
        # "Page 1 of 1" headerless table belongs to another document — must
        # NOT bleed into the previous invoice.
        pages = [
            self._page(date="2026-06-05", bill_no="3987", items=[{"sr_no": 1}], total=8324.95),
            self._page(items=[{"sr_no": 2}], total=2183.78, page_no=1),  # Page 1 of 1
            self._page(items=[{"sr_no": 3}], total=23959.12),  # no marker at all
        ]
        invoices, skipped = merge_page_invoices(pages)
        assert len(invoices) == 1
        assert invoices[0]["bill_no"] == "3987"
        assert len(invoices[0]["items"]) == 1
        assert invoices[0]["total_amount"] == 8324.95
        assert skipped == 2

    def test_empty_header_invoice_dropped(self):
        pages = [
            self._page(date="2026-07-18", bill_no=None, items=[], total=0.0),
            self._page(date="2026-07-20", bill_no="12602380", items=[{"sr_no": 1}], total=21103.0),
        ]
        invoices, skipped = merge_page_invoices(pages)
        assert len(invoices) == 1
        assert invoices[0]["bill_no"] == "12602380"
        assert skipped == 1

    def test_two_dated_pages_stay_separate(self):
        pages = [
            self._page(date="2026-07-03", bill_no="A", items=[{"sr_no": 1}], total=100.0),
            self._page(date="2026-06-05", bill_no="B", items=[{"sr_no": 2}], total=200.0),
        ]
        invoices, skipped = merge_page_invoices(pages)
        assert len(invoices) == 2
        assert skipped == 0
