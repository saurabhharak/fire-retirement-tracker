"""Unit tests for amul_purchases_svc (daily manual purchases CRUD).

DB-mocked via _FakeClient + monkeypatch (pattern from test_amul_sales_svc.py).
Ownership enforced via _verify_parlour_membership gate.
"""

import pytest

from app.exceptions import DataNotFoundError
from app.services import amul_purchases_svc, parlours_svc


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

    def upsert(self, payload, on_conflict=None):
        self.calls.append(("upsert", payload, on_conflict))
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


def _member_rows(role="owner"):
    return {"parlour_members": [{"parlour_id": "p1", "member_id": "u1", "role": role}]}


def _patch_clients(monkeypatch, fake):
    """Patch both the purchases service and the parlours membership gate."""
    monkeypatch.setattr(amul_purchases_svc, "get_user_client", lambda token: fake)
    monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)


class TestLoadDailyPurchases:
    def test_load_daily_purchases_returns_rows_scoped_to_parlour(self, monkeypatch):
        rows = [
            {"id": "pu1", "parlour_id": "p1", "purchase_date": "2026-08-15",
             "amount": 8400, "note": "Mahavir"}
        ]
        fake = _FakeClient({"amul_daily_purchases": rows, **_member_rows()})
        _patch_clients(monkeypatch, fake)
        result = amul_purchases_svc.load_daily_purchases("p1", "u1", "tok")
        assert result == rows

    def test_load_filters_by_date_range(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.load_daily_purchases(
            "p1", "u1", "tok", from_date="2026-08-01", to_date="2026-08-31"
        )
        filters = [c for c in fake.calls if c[0] in ("gte", "lte")]
        assert ("purchase_date", "2026-08-01") in [f[1] for f in filters]
        assert ("purchase_date", "2026-08-31") in [f[1] for f in filters]

    def test_load_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_purchases_svc.load_daily_purchases("p1", "u1", "tok")

    def test_load_orders_by_purchase_date_desc(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.load_daily_purchases("p1", "u1", "tok")
        order_calls = [c for c in fake.calls if c[0] == "order"]
        assert order_calls and order_calls[-1][1][0] == "purchase_date"


class TestSaveDailyPurchase:
    def test_save_daily_purchase_injects_parlour_id_and_entered_by(self, monkeypatch):
        upserted = {}
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        orig = fake.upsert

        def _upsert(payload, on_conflict=None):
            upserted.update(payload)
            return orig(payload, on_conflict=on_conflict)

        fake.upsert = _upsert
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.save_daily_purchase(
            "p1", "u1",
            {"purchase_date": "2026-08-15", "amount": 8400, "note": "Mahavir"},
            "tok",
        )
        assert upserted["parlour_id"] == "p1"
        assert upserted["entered_by"] == "u1"

    def test_save_uses_upsert_on_parlour_date_to_avoid_duplicates(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.save_daily_purchase(
            "p1", "u1",
            {"purchase_date": "2026-08-15", "amount": 8400, "note": ""},
            "tok",
        )
        upserts = [c for c in fake.calls if c[0] == "upsert"]
        assert upserts, "expected save_daily_purchase to upsert"
        assert upserts[0][2] == "parlour_id,purchase_date"

    def test_save_allows_zero_amount_placeholder(self, monkeypatch):
        """Zero rows are the team's 'not filled yet' markers — must not be rejected."""
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.save_daily_purchase(
            "p1", "u1",
            {"purchase_date": "2026-08-15", "amount": 0, "note": ""},
            "tok",
        )
        assert any(c[0] == "upsert" for c in fake.calls)

    def test_save_daily_purchase_for_non_member_raises_data_not_found(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_purchases_svc.save_daily_purchase(
                "p1", "u1",
                {"purchase_date": "2026-08-15", "amount": 10, "note": ""},
                "tok",
            )


class TestUpdateDelete:
    def test_update_daily_purchase(self, monkeypatch):
        fake = _FakeClient(
            {
                "amul_daily_purchases": [{"id": "pu1", "amount": 999}],
                **_member_rows(),
            }
        )
        _patch_clients(monkeypatch, fake)
        result = amul_purchases_svc.update_daily_purchase(
            "pu1", "p1", "u1", {"amount": 3000}, "tok"
        )
        assert result["amount"] == 999  # fake returns canned row

    def test_update_daily_purchase_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_purchases_svc.update_daily_purchase(
                "pu1", "p1", "u1", {"amount": 3000}, "tok"
            )

    def test_delete_daily_purchase(self, monkeypatch):
        fake = _FakeClient({"amul_daily_purchases": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_purchases_svc.delete_daily_purchase("pu1", "p1", "u1", "tok")  # no raise
        assert any(c[0] == "delete" for c in fake.calls)
