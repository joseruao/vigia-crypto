# backend/tests/test_alerts.py
import os
from fastapi.testclient import TestClient
from Api.main import app

def test_health_env_flags(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://dummy.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "dummy_key")
    client = TestClient(app)
    r = client.get("/alerts/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["supabase_url"] is True
    assert data["has_key"] is True

def test_holdings_does_not_500(monkeypatch):
    # Sem key → deve devolver ok=False, não 500
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://dummy.supabase.co")
    client = TestClient(app)
    r = client.get("/alerts/holdings")
    assert r.status_code == 200
    assert r.json().get("ok") is False

def test_ask_basic(monkeypatch):
    # Sem key → ok False, sem 500
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://dummy.supabase.co")
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que tokens a binance tem em holding"})
    assert r.status_code == 200
    assert r.json().get("ok") is False
