"""Unit tests for amul_other_expenses_svc (operating expenses CRUD).

DB-mocked via _FakeClient + monkeypatch. Membership gate enforced via
parlours_svc._verify_parlour_membership.
"""

import pytest

from app.exceptions import DataNotFoundError
from app.services import amul_other_expenses_svc, parlours_svc


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


def _member_rows(role="owner"):
    return {"parlour_members": [{"parlour_id": "p1", "member_id": "u1", "role": role}]}


def _patch_clients(monkeypatch, fake):
    monkeypatch.setattr(amul_other_expenses_svc, "get_user_client", lambda token: fake)
    monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)


# ===================================================================
# load_other_expenses
# ===================================================================
class TestLoadOtherExpenses:
    def test_load_returns_rows_scoped_to_parlour(self, monkeypatch):
        rows = [
            {"id": "e1", "parlour_id": "p1", "expense_date": "2026-07-01",
             "category": "rent", "amount": 20000}
        ]
        fake = _FakeClient({"amul_other_expenses": rows, **_member_rows()})
        _patch_clients(monkeypatch, fake)
        result = amul_other_expenses_svc.load_other_expenses("p1", "u1", "tok")
        assert result == rows

    def test_load_filters_by_date_and_category(self, monkeypatch):
        fake = _FakeClient({"amul_other_expenses": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_other_expenses_svc.load_other_expenses(
            "p1", "u1", "tok", from_date="2026-07-01", to_date="2026-07-31", category="rent"
        )
        filters = [f[1] for f in fake.calls if f[0] in ("gte", "lte", "eq")]
        assert ("expense_date", "2026-07-01") in filters
        assert ("expense_date", "2026-07-31") in filters
        assert ("category", "rent") in filters

    def test_load_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_other_expenses": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_other_expenses_svc.load_other_expenses("p1", "u1", "tok")


# ===================================================================
# save_other_expense
# ===================================================================
class TestSaveOtherExpense:
    def test_save_injects_parlour_id(self, monkeypatch):
        inserted = {}
        fake = _FakeClient({"amul_other_expenses": [], **_member_rows()})
        orig = fake.insert

        def _insert(payload):
            inserted.update(payload)
            return orig(payload)

        fake.insert = _insert
        _patch_clients(monkeypatch, fake)
        amul_other_expenses_svc.save_other_expense(
            "p1", "u1",
            {"expense_date": "2026-07-01", "category": "electricity", "amount": 4500},
            "tok",
        )
        assert inserted["parlour_id"] == "p1"
        assert inserted["category"] == "electricity"

    def test_save_for_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_other_expenses": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_other_expenses_svc.save_other_expense(
                "p1", "u1", {"expense_date": "2026-07-01", "category": "rent", "amount": 100},
                "tok",
            )


# ===================================================================
# update / delete
# ===================================================================
class TestUpdateDelete:
    def test_update_other_expense(self, monkeypatch):
        fake = _FakeClient(
            {
                "amul_other_expenses": [{"id": "e1", "amount": 5000}],
                **_member_rows(),
            }
        )
        _patch_clients(monkeypatch, fake)
        result = amul_other_expenses_svc.update_other_expense(
            "e1", "p1", "u1", {"amount": 6000}, "tok"
        )
        assert result["amount"] == 5000  # canned row returned

    def test_update_non_member_raises(self, monkeypatch):
        fake = _FakeClient({"amul_other_expenses": [], "parlour_members": []})
        _patch_clients(monkeypatch, fake)
        with pytest.raises(DataNotFoundError):
            amul_other_expenses_svc.update_other_expense("e1", "p1", "u1", {"amount": 1}, "tok")

    def test_delete_other_expense(self, monkeypatch):
        fake = _FakeClient({"amul_other_expenses": [], **_member_rows()})
        _patch_clients(monkeypatch, fake)
        amul_other_expenses_svc.delete_other_expense("e1", "p1", "u1", "tok")
        assert any(c[0] == "delete" for c in fake.calls)
