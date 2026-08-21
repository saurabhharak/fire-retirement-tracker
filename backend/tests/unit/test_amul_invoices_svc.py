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
