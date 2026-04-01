"""API health and auth tests for FIRE Retirement Tracker."""

from fastapi.testclient import TestClient
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_protected_endpoint_requires_auth():
    response = client.get("/api/fire-inputs")
    assert response.status_code == 401  # No Bearer token

def test_protected_endpoint_rejects_invalid_token():
    response = client.get("/api/fire-inputs", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
