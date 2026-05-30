# backend/tests/test_alerts.py
import os
from fastapi.testclient import TestClient
from Api.main import app
from Api.routes import alerts

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
    monkeypatch.setattr(alerts.supa, "ok", lambda: False)
    client = TestClient(app)
    r = client.get("/alerts/holdings")
    assert r.status_code == 200
    assert r.json().get("ok") is False

def test_ask_basic(monkeypatch):
    # Sem key → ok False, sem 500
    monkeypatch.setattr(alerts.supa, "ok", lambda: False)
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que tokens a binance tem em holding"})
    assert r.status_code == 200
    assert r.json().get("ok") is False

def test_buy_watchlist_question_detection():
    assert alerts._is_buy_watchlist_question("que moedas me aconselhas a comprar hoje do top100?")
    assert alerts._is_buy_watchlist_question("top 100 crypto buy opportunities")
    assert not alerts._is_buy_watchlist_question("analisa BTC")

def test_top100_buy_question_is_not_answered_from_listings(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 404
        def json(self):
            return []
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que moedas me aconselhas a comprar hoje do top100?"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 0
    assert "top100_technical_rankings" in data["answer"]

def test_top100_buy_question_uses_ranking_table(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "score": 82.5,
                    "signal": "FORTE",
                    "risk": "BAIXO/MODERADO",
                    "change_7d": 4.2,
                    "change_30d": 12.1,
                    "volume_24h": 25000000000,
                    "rationale": "7d 4.2%, volume forte vs market cap",
                }
            ]
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que moedas me aconselhas a comprar hoje do top100?"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 1
    assert "BTC" in data["answer"]
    assert "82.5/100" in data["answer"]
