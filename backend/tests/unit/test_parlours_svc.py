"""Unit tests for parlours_svc (multi-tenant parlour + membership CRUD).

Uses the _FakeClient + monkeypatch pattern from test_svc_regressions.py.
The service layer enforces membership (role gate) in addition to RLS.
"""

import pytest

from app.exceptions import DataNotFoundError, ForbiddenError
from app.services import parlours_svc


class _FakeClient:
    """Minimal stand-in for the Supabase query chain."""

    def __init__(self, rows_by_table=None):
        self._rows_by_table = rows_by_table or {}
        self._table_name = None
        self.calls = []

    def table(self, name):
        self._table_name = name
        self.calls.append(("table", name))
        return self

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args))
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

    def execute(self):
        class _Resp:
            data = self._rows_by_table.get(self._table_name, [])

        return _Resp()


def _make_rows(parlours=None, members=None):
    return {
        "parlours": parlours or [],
        "parlour_members": members or [],
    }


# ===================================================================
# _verify_parlour_membership
# ===================================================================
class TestVerifyMembership:
    def test_member_returns_role(self, monkeypatch):
        fake = _FakeClient(
            _make_rows(members=[{"parlour_id": "p1", "member_id": "u1", "role": "owner"}])
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        role = parlours_svc._verify_parlour_membership("p1", "u1", "tok")
        assert role == "owner"

    def test_non_member_raises(self, monkeypatch):
        fake = _FakeClient(_make_rows(members=[]))
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(DataNotFoundError):
            parlours_svc._verify_parlour_membership("p1", "u1", "tok")


# ===================================================================
# _require_owner
# ===================================================================
class TestRequireOwner:
    def test_owner_passes(self, monkeypatch):
        fake = _FakeClient(
            _make_rows(members=[{"parlour_id": "p1", "member_id": "u1", "role": "owner"}])
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        parlours_svc._require_owner("p1", "u1", "tok")  # no raise

    def test_data_entry_raises_forbidden(self, monkeypatch):
        fake = _FakeClient(
            _make_rows(members=[{"parlour_id": "p1", "member_id": "u1", "role": "data_entry"}])
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(ForbiddenError):
            parlours_svc._require_owner("p1", "u1", "tok")


# ===================================================================
# create_parlour / list_user_parlours / get_parlour / update_parlour
# ===================================================================
class TestParlourCrud:
    def test_create_parlour_returns_parlour_with_owner_id(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlours": [
                    {"id": "p1", "name": "Vrindavan", "owner_id": "u1",
                     "sarvam_starting_credits": 100}
                ]
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        result = parlours_svc.create_parlour(
            "u1", {"name": "Vrindavan", "sarvam_starting_credits": 100}, "tok"
        )
        assert result["owner_id"] == "u1"
        assert result["name"] == "Vrindavan"

    def test_create_parlour_injects_owner_id(self, monkeypatch):
        inserted = {}
        fake = _FakeClient(_make_rows())

        orig_insert = fake.insert

        def _insert(payload):
            inserted.update(payload)
            return orig_insert(payload)

        fake.insert = _insert
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        parlours_svc.create_parlour(
            "u1", {"name": "Vrindavan", "sarvam_starting_credits": 100}, "tok"
        )
        assert inserted.get("owner_id") == "u1"

    def test_list_user_parlours_returns_member_parlours(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlour_members": [
                    {
                        "parlour_id": "p1", "member_id": "u1", "role": "owner",
                        "parlours": {"id": "p1", "name": "Vrindavan"},
                    },
                    {
                        "parlour_id": "p2", "member_id": "u1", "role": "data_entry",
                        "parlours": {"id": "p2", "name": "Second Parlour"},
                    },
                ]
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        result = parlours_svc.list_user_parlours("u1", "tok")
        assert len(result) == 2
        assert result[0]["name"] == "Vrindavan"
        assert result[0]["role"] == "owner"

    def test_get_parlour_for_non_member_raises_data_not_found(self, monkeypatch):
        fake = _FakeClient(_make_rows(members=[]))
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(DataNotFoundError):
            parlours_svc.get_parlour("p1", "u1", "tok")

    def test_update_parlour_owner_only(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlours": [{"id": "p1", "name": "Renamed", "owner_id": "u1"}],
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "owner"}
                ],
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        result = parlours_svc.update_parlour("p1", "u1", {"name": "Renamed"}, "tok")
        assert result["name"] == "Renamed"

    def test_update_parlour_non_owner_raises_forbidden(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlours": [],
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "data_entry"}
                ],
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(ForbiddenError):
            parlours_svc.update_parlour("p1", "u1", {"name": "Renamed"}, "tok")


# ===================================================================
# members management
# ===================================================================
class TestMembers:
    def test_list_members_owner_only(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "owner"},
                    {"parlour_id": "p1", "member_id": "u2", "role": "data_entry"},
                ]
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        result = parlours_svc.list_members("p1", "u1", "tok")
        assert len(result) == 2

    def test_add_member_resolves_email_to_user_id(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "owner"}
                ]
            }
        )
        # service-role client resolves email -> user_id
        service_fake = _FakeClient(
            {"auth.users": [{"id": "u2", "email": "swapnil@example.com"}]}
        )
        monkeypatch.setattr(parlours_svc, "get_service_client", lambda: service_fake)
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        monkeypatch.setattr(parlours_svc, "log_audit", lambda *a, **k: None)

        # Simulate insert returning the created row
        created = {
            "id": "m2", "parlour_id": "p1", "member_id": "u2", "role": "data_entry"
        }
        orig_insert = fake.insert

        def _insert(payload):
            fake._rows_by_table["parlour_members"] = [created]
            return orig_insert(payload)

        fake.insert = _insert

        result = parlours_svc.add_member(
            "p1", "swapnil@example.com", "data_entry", "u1", "tok"
        )
        assert result["member_id"] == "u2"
        assert result["role"] == "data_entry"

    def test_add_member_non_owner_raises(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "data_entry"}
                ]
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(ForbiddenError):
            parlours_svc.add_member("p1", "a@b.com", "data_entry", "u1", "tok")

    def test_remove_member_cannot_remove_owner(self, monkeypatch):
        fake = _FakeClient(
            {
                "parlour_members": [
                    {"id": "m1", "parlour_id": "p1", "member_id": "u2", "role": "owner"},
                    {"id": "m2", "parlour_id": "p1", "member_id": "u1", "role": "owner"},
                ]
            }
        )
        monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)
        with pytest.raises(ForbiddenError):
            parlours_svc.remove_member("p1", "m1", "u1", "tok")
