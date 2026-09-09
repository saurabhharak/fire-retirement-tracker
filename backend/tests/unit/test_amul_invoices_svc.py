"""Unit tests for amul_invoices_svc (purchase invoices + line items CRUD).

DB-mocked via _FakeClient + monkeypatch. Membership gate enforced via
_verify_parlour_membership; line items owned through their invoice.
"""

import pytest

from app.exceptions import DataNotFoundError
from app.services import amul_invoices_svc, parlours_svc


class _FakeClient:
    def __init__(self, rows_by_table=None):
        self._rows_by_table = rows_by_table or {}
        self._table_name = None
        self.calls = []

    def table(self, name):
        self._table_name = name
        self.calls.append(("table", name))
        return self

    def select(self, *args, **kwargs):
        self.calls.append(("select", args))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args))
        return self

    def gte(self, *args, **kwargs):
        self.calls.append(("gte", args))
        return self

    def lte(self, *args, **kwargs):
        self.calls.append(("lte", args))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args))
        return self

    def insert(self, payload):
        self.calls.append(("insert", payload))
        return self

    def update(self, payload):
        self.calls.append(("update", payload))
        return self

    def delete(self):
        self.calls.append(("delete",))
        return self

    def execute(self):
        class _Resp:
            data = self._rows_by_table.get(self._table_name, [])

        return _Resp()


def _rows(invoices=None, items=None, members=None):
    return {
        "amul_invoices": invoices or [],
        "amul_invoice_items": items or [],
        "parlour_members": members if members is not None
        else [{"parlour_id": "p1", "member_id": "u1", "role": "owner"}],
    }


def _patch_clients(monkeypatch, fake):
    monkeypatch.setattr(amul_invoices_svc, "get_user_client", lambda token: fake)
    monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)


# ===================================================================
# load_invoices
# ===================================================================
class TestLoadInvoices:
    def test_load_invoices_scoped_to_parlour(self, monkeypatch):
        rows = [
            {"id": "inv1", "parlour_id": "p1", "distributor": "M/S.MAHAVIR",
             "bill_date": "2026-07-01", "total_amount": 1761.88}
        ]
        fake = _FakeClient(_rows(invoices=rows))
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.load_invoices("p1", "u1", "tok")
        assert result == rows
    def test_load_filters_by_month_and_distributor(self, monkeypatch):
        fake = _FakeClient(_rows())
        _patch_clients(monkeypatch, fake)
        amul_invoices_svc.load_invoices(
            "p1", "u1", "tok", month="2026-07", distributor="M/S.MAHAVIR"
        )
        eq_calls = [f[1] for f in fake.calls if f[0] == "eq"]
        assert ("distributor", "M/S.MAHAVIR") in eq_calls

    def test_load_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient(_rows(members=[]))
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_invoices_svc.load_invoices("p1", "u1", "tok")


# ===================================================================
# get_invoice_with_items
# ===================================================================
class TestGetInvoiceWithItems:
    def test_returns_composite(self, monkeypatch):
        fake = _FakeClient(
            _rows(
                invoices=[{"id": "inv1", "total_amount": 100}],
                items=[{"id": "it1", "invoice_id": "inv1", "net_amount": 50}],
            )
        )
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.get_invoice_with_items("inv1", "p1", "u1", "tok")
        assert result["invoice"]["total_amount"] == 100
        assert len(result["items"]) == 1

    def test_missing_invoice_raises(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[], items=[]))
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_invoices_svc.get_invoice_with_items("inv1", "p1", "u1", "tok")


# ===================================================================
# save_invoice_with_items
# ===================================================================
class TestSaveInvoiceWithItems:
    def test_inserts_header_then_items(self, monkeypatch):
        fake = _FakeClient(
            _rows(invoices=[{"id": "inv1"}], items=[], )
        )
        inserts = []
        orig = fake.insert

        def _insert(payload):
            inserts.append(payload)
            return orig(payload)

        fake.insert = _insert
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.save_invoice_with_items(
            "p1", "u1",
            {"distributor": "M/S.MAHAVIR", "bill_date": "2026-07-01",
             "invoice_type": "tax_invoice", "total_amount": 100},
            [{"description": "Item A", "rate": 10, "net_amount": 100}],
            "tok",
        )
        # header insert + items insert
        assert inserts
        assert result is not None

    def test_save_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient(_rows(members=[]))
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_invoices_svc.save_invoice_with_items(
                "p1", "u1",
                {"distributor": "D", "bill_date": "2026-07-01",
                 "invoice_type": "tax_invoice", "total_amount": 10},
                [], "tok",
            )


# ===================================================================
# update / delete
# ===================================================================
class TestUpdateDelete:
    def test_update_invoice(self, monkeypatch):
        fake = _FakeClient(
            _rows(invoices=[{"id": "inv1", "status": "draft"}])
        )
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.update_invoice(
            "inv1", "p1", "u1", {"status": "confirmed"}, "tok"
        )
        assert result["status"] == "draft"  # canned row returned

    def test_update_invoice_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient(_rows(members=[]))
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_invoices_svc.update_invoice("inv1", "p1", "u1", {"status": "confirmed"}, "tok")

    def test_delete_invoice(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[{"id": "inv1"}]))
        _patch_clients(monkeypatch, fake)
        amul_invoices_svc.delete_invoice("inv1", "p1", "u1", "tok")
        assert any(c[0] == "delete" for c in fake.calls)


# ===================================================================
# membership gate (cross-parlour)
# ===================================================================
class TestMembershipGate:
    def test_cross_parlour_access_blocked(self, monkeypatch):
        # user is member of p1 only; attempts access to p2 -> blocked
        def _verify(parlour_id, user_id, access_token):
            if parlour_id != "p1":
                raise DataNotFoundError("Parlour not found")
            return "owner"

        monkeypatch.setattr(parlours_svc, "_verify_parlour_membership", _verify)
        fake = _FakeClient(_rows())
        monkeypatch.setattr(amul_invoices_svc, "get_user_client", lambda token: fake)
        with pytest.raises(DataNotFoundError):
            amul_invoices_svc.load_invoices("p2", "u1", "tok")


# ===================================================================
# PDF deduplication
# ===================================================================
class TestFindDuplicate:
    def test_matches_by_bill_no_and_date(self, monkeypatch):
        rows = [{"id": "inv1", "bill_no": "3987", "bill_date": "2026-08-10"}]
        fake = _FakeClient(_rows(invoices=rows))
        _patch_clients(monkeypatch, fake)
        dup = amul_invoices_svc.find_duplicate(
            "p1", {"bill_no": "3987", "bill_date": "2026-08-10"}, "tok"
        )
        assert dup is not None
        assert dup["id"] == "inv1"

    def test_no_match_returns_none(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[]))
        _patch_clients(monkeypatch, fake)
        assert amul_invoices_svc.find_duplicate(
            "p1", {"bill_no": "0000", "bill_date": "2026-08-10"}, "tok"
        ) is None

    def test_missing_bill_no_or_date_skips_lookup(self, monkeypatch):
        fake = _FakeClient(_rows())
        _patch_clients(monkeypatch, fake)
        assert amul_invoices_svc.find_duplicate(
            "p1", {"bill_date": "2026-08-10"}, "tok"
        ) is None
        assert amul_invoices_svc.find_duplicate("p1", {"bill_no": "3987"}, "tok") is None
        assert not any(c[0] == "table" for c in fake.calls)


class TestFindByPdfHash:
    def test_queries_by_parlour_and_hash(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[{"id": "inv1", "source_pdf_hash": "abc"}]))
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.find_by_pdf_hash("p1", "abc", "tok")
        assert result and result[0]["id"] == "inv1"
        eq_calls = [f[1] for f in fake.calls if f[0] == "eq"]
        assert ("source_pdf_hash", "abc") in eq_calls

    def test_no_match_returns_empty(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[]))
        _patch_clients(monkeypatch, fake)
        assert amul_invoices_svc.find_by_pdf_hash("p1", "abc", "tok") == []


class TestSaveInvoiceWithHash:
    def test_hash_persisted_when_provided(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[{"id": "inv1"}]))
        _patch_clients(monkeypatch, fake)
        amul_invoices_svc.save_invoice_with_items(
            "p1", "u1", {"bill_no": "3987", "bill_date": "2026-08-10"}, [],
            "tok", source_pdf_hash="deadbeef",
        )
        insert_calls = [f[1] for f in fake.calls if f[0] == "insert"]
        assert any(c.get("source_pdf_hash") == "deadbeef" for c in insert_calls)

    def test_hash_omitted_when_absent(self, monkeypatch):
        fake = _FakeClient(_rows(invoices=[{"id": "inv1"}]))
        _patch_clients(monkeypatch, fake)
        amul_invoices_svc.save_invoice_with_items(
            "p1", "u1", {"bill_no": "3987", "bill_date": "2026-08-10"}, [], "tok"
        )
        insert_calls = [f[1] for f in fake.calls if f[0] == "insert"]
        assert all("source_pdf_hash" not in c for c in insert_calls)


class TestDedupGracefulDegradation:
    """Pre-migration 024: uploads must still work, dedup just turns off."""

    def test_find_by_pdf_hash_returns_empty_when_column_missing(self, monkeypatch):
        class _NoColumnClient(_FakeClient):
            def execute(self):
                if self._table_name == "amul_invoices":
                    raise RuntimeError(
                        "{'message': 'column invoices.source_pdf_hash does not "
                        "exist', 'code': '42703'}"
                    )
                return super().execute()

        fake = _NoColumnClient(_rows())
        _patch_clients(monkeypatch, fake)
        assert amul_invoices_svc.find_by_pdf_hash("p1", "abc", "tok") == []

    def test_save_retries_without_hash_when_column_missing(self, monkeypatch):
        class _RetryClient(_FakeClient):
            def insert(self, payload):
                super().insert(payload)
                if "source_pdf_hash" in payload:
                    raise RuntimeError(
                        "{'message': 'column invoices.source_pdf_hash does not "
                        "exist', 'code': '42703'}"
                    )
                return self

        fake = _RetryClient(_rows(invoices=[{"id": "inv1"}]))
        _patch_clients(monkeypatch, fake)
        result = amul_invoices_svc.save_invoice_with_items(
            "p1", "u1", {"bill_no": "3987", "bill_date": "2026-08-10"}, [],
            "tok", source_pdf_hash="deadbeef",
        )
        assert result is not None
        insert_payloads = [f[1] for f in fake.calls if f[0] == "insert"]
        assert any("source_pdf_hash" not in p for p in insert_payloads)
