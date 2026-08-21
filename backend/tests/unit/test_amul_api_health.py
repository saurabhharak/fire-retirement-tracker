"""Auth smoke tests for the Amul parlour + parlours API endpoints.

Mirrors test_api_health.py: env vars set before importing app.main,
asserts every new endpoint returns 401 without a Bearer token.
"""
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_parlours_endpoints_require_auth():
    assert client.get("/api/parlours").status_code == 401
    assert client.post("/api/parlours", json={"name": "X"}).status_code == 401


def test_parlour_detail_and_members_require_auth():
    assert client.get("/api/parlours/11111111-1111-1111-1111-111111111111").status_code == 401
    assert client.get("/api/parlours/11111111-1111-1111-1111-111111111111/members").status_code == 401


def test_amul_sales_endpoints_require_auth():
    assert client.get("/api/amul/sales", params={"parlour_id": "p1"}).status_code == 401
    assert client.post("/api/amul/sales", params={"parlour_id": "p1"}, json={}).status_code == 401


def test_amul_invoices_endpoints_require_auth():
    assert client.get("/api/amul/invoices", params={"parlour_id": "p1"}).status_code == 401
    assert client.get("/api/amul/invoices/11111111-1111-1111-1111-111111111111", params={"parlour_id": "p1"}).status_code == 401


def test_amul_analytics_requires_auth():
    assert client.get("/api/amul/analytics", params={"parlour_id": "p1"}).status_code == 401


def test_amul_sarvam_usage_requires_auth():
    assert client.get("/api/amul/sarvam-usage", params={"parlour_id": "p1"}).status_code == 401


def test_amul_invoice_upload_requires_auth():
    assert client.post("/api/amul/invoices/upload").status_code == 401
