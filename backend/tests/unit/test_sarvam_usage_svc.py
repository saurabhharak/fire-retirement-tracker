"""Unit tests for sarvam_usage_svc (Sarvam spend tracking).

Owner-only visibility for spend data (RLS + service gate).
"""

import pytest

from app.exceptions import ForbiddenError
from app.services import parlours_svc, sarvam_usage_svc


class _FakeClient:
    def __init__(self, rows_by_table=None):
        self._rows_by_table = rows_by_table or {}
        self._table_name = None

    def table(self, name):
        self._table_name = name
        return self

    def select(self, *args, **kwargs): return self
    def eq(self, *args, **kwargs): return self
    def order(self, *args, **kwargs): return self

    def execute(self):
        class _Resp:
            data = self._rows_by_table.get(self._table_name, [])

        return _Resp()


def _rows(usage=None, members=None):
    return {
        "sarvam_usage": usage or [],
        "parlour_members": members if members is not None
        else [{"parlour_id": "p1", "member_id": "u1", "role": "owner"}],
    }


def _patch_clients(monkeypatch, fake):
    monkeypatch.setattr(sarvam_usage_svc, "get_user_client", lambda token: fake)
    monkeypatch.setattr(parlours_svc, "get_user_client", lambda token: fake)


# ===================================================================
# load_usage
# ===================================================================
class TestLoadUsage:
    def test_load_usage_owner_only(self, monkeypatch):
        usage = [
            {"parlour_id": "p1", "endpoint": "sarvam_ocr", "credits_used": 2},
        ]
        fake = _FakeClient(_rows(usage=usage))
        _patch_clients(monkeypatch, fake)
        result = sarvam_usage_svc.load_usage("p1", "u1", "tok")
        assert result == usage

    def test_load_usage_non_owner_raises_forbidden(self, monkeypatch):
        fake = _FakeClient(
            _rows(
                usage=[],
                members=[{"parlour_id": "p1", "member_id": "u1", "role": "data_entry"}],
            )
        )
        _patch_clients(monkeypatch, fake)
        with pytest.raises(ForbiddenError):
            sarvam_usage_svc.load_usage("p1", "u1", "tok")

# ===================================================================
# get_spend_summary
# ===================================================================
class TestGetSpendSummary:
    def test_returns_totals_and_remaining(self, monkeypatch):
        usage = [
            {"credits_used": 2, "cost_estimate_inr": 0.1},
            {"credits_used": 3, "cost_estimate_inr": 0.15},
        ]
        fake = _FakeClient(
            {
                "sarvam_usage": usage,
                "parlours": [{"sarvam_starting_credits": 10}],
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "owner"}
                ],
            }
        )
        _patch_clients(monkeypatch, fake)
        result = sarvam_usage_svc.get_spend_summary("p1", "u1", "tok")
        assert result["starting"] == 10
        assert result["used"] == 5
        assert result["remaining"] == 5
        assert result["call_count"] == 2

    def test_no_usage_returns_starting(self, monkeypatch):
        fake = _FakeClient(
            {
                "sarvam_usage": [],
                "parlours": [{"sarvam_starting_credits": 50}],
                "parlour_members": [
                    {"parlour_id": "p1", "member_id": "u1", "role": "owner"}
                ],
            }
        )
        _patch_clients(monkeypatch, fake)
        result = sarvam_usage_svc.get_spend_summary("p1", "u1", "tok")
        assert result["remaining"] == 50
        assert result["call_count"] == 0

    def test_non_owner_raises(self, monkeypatch):
        fake = _FakeClient(
            _rows(
                members=[{"parlour_id": "p1", "member_id": "u1", "role": "data_entry"}]
            )
        )
        _patch_clients(monkeypatch, fake)
        with pytest.raises(ForbiddenError):
            sarvam_usage_svc.get_spend_summary("p1", "u1", "tok")
