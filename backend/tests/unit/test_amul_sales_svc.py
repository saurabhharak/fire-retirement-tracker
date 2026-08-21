"""Unit tests for amul_sales_svc (daily WhatsApp sales CRUD).

DB-mocked via _FakeClient + monkeypatch (pattern from test_svc_regressions.py).
Ownership enforced via _verify_parlour_membership gate.
"""

import pytest

from app.exceptions import DataNotFoundError
from app.services import amul_sales_svc, parlours_svc


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
    """Patch both the sales service and the parlours membership gate."""
    monkeypatch.setattr(amul_sales_svc, "get_user_client", lambda token: fake)
    monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)


# ===================================================================
# load_daily_sales
# ===================================================================
class TestLoadDailySales:
    def test_load_daily_sales_returns_rows_scoped_to_parlour(self, monkeypatch):
        rows = [
            {"id": "s1", "parlour_id": "p1", "sale_date": "2026-08-15",
             "cash_amount": 2750, "online_amount": 5769}
        ]
        fake = _FakeClient({"amul_daily_sales": rows, **_member_rows()})
        _patch_clients(monkeypatch, fake)
        result = amul_sales_svc.load_daily_sales("p1", "u1", "tok")
        assert result == rows

    def test_load_filters_by_date_range(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_sales_svc.load_daily_sales(
            "p1", "u1", "tok", from_date="2026-08-01", to_date="2026-08-31"
        )
        filters = [c for c in fake.calls if c[0] in ("gte", "lte")]
        assert ("sale_date", "2026-08-01") in [f[1] for f in filters]
        assert ("sale_date", "2026-08-31") in [f[1] for f in filters]

    def test_load_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_sales_svc.load_daily_sales("p1", "u1", "tok")

    def test_load_orders_by_sale_date_desc(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_sales_svc.load_daily_sales("p1", "u1", "tok")
        order_calls = [c for c in fake.calls if c[0] == "order"]
        assert order_calls and order_calls[-1][1][0] == "sale_date"


# ===================================================================
# save_daily_sale
# ===================================================================
class TestSaveDailySale:
    def test_save_daily_sale_injects_parlour_id_and_entered_by(self, monkeypatch):
        upserted = {}
        fake = _FakeClient({"amul_daily_sales": [], **_member_rows()})
        orig = fake.upsert

        def _upsert(payload, on_conflict=None):
            upserted.update(payload)
            return orig(payload, on_conflict=on_conflict)

        fake.upsert = _upsert
        _patch_clients(monkeypatch, fake)
        amul_sales_svc.save_daily_sale(
            "p1", "u1",
            {"sale_date": "2026-08-15", "cash_amount": 2750, "online_amount": 5769},
            "tok",
        )
        assert upserted["parlour_id"] == "p1"
        assert upserted["entered_by"] == "u1"

    def test_save_uses_upsert_on_parlour_date_to_avoid_duplicates(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_sales_svc.save_daily_sale(
            "p1", "u1",
            {"sale_date": "2026-08-15", "cash_amount": 2750, "online_amount": 5769},
            "tok",
        )
        upserts = [c for c in fake.calls if c[0] == "upsert"]
        assert upserts, "expected save_daily_sale to upsert"
        assert upserts[0][2] == "parlour_id,sale_date"

    def test_save_daily_sale_for_non_member_raises_data_not_found(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_sales_svc.save_daily_sale(
                "p1", "u1",
                {"sale_date": "2026-08-15", "cash_amount": 10, "online_amount": 0},
                "tok",
            )


# ===================================================================
# update_daily_sale / delete_daily_sale
# ===================================================================
class TestUpdateDelete:
    def test_update_daily_sale(self, monkeypatch):
        fake = _FakeClient(
            {
                "amul_daily_sales": [{"id": "s1", "cash_amount": 999}],
                **_member_rows(),
            }
        )
        _patch_clients(monkeypatch, fake)
        result = amul_sales_svc.update_daily_sale(
            "s1", "p1", "u1", {"cash_amount": 3000}, "tok"
        )
        assert result["cash_amount"] == 999  # fake returns canned row

    def test_update_daily_sale_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_sales_svc.update_daily_sale(
                "s1", "p1", "u1", {"cash_amount": 3000}, "tok"
            )

    def test_delete_daily_sale(self, monkeypatch):
        fake = _FakeClient({"amul_daily_sales": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_sales_svc.delete_daily_sale("s1", "p1", "u1", "tok")  # no raise
        assert any(c[0] == "delete" for c in fake.calls)
