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

def test_top100_question_is_not_coin_analysis():
    from Api import main

    assert main._should_use_coin_analysis("analisa BTC")
    assert not main._should_use_coin_analysis("Que moedas me aconselhas a analisar hoje do top100?")

def test_chat_stream_routes_top100_to_alerts(monkeypatch):
    from Api import main

    monkeypatch.setattr(
        main,
        "answer_top100_buy_watchlist",
        lambda log=None: {"ok": True, "answer": "RANKING TOP100 TESTE", "count": 1, "items": []},
    )
    client = TestClient(app)
    r = client.post("/chat/stream", json={"prompt": "Que moedas me aconselhas a analisar hoje do top100?", "history": []})
    assert r.status_code == 200
    assert "RANKING TOP100 TESTE" in r.text

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

def test_top100_answer_filters_stablecoins(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"symbol": "USDT", "name": "Tether", "score": 99, "signal": "FORTE", "risk": "BAIXO"},
                {"symbol": "SOL", "name": "Solana", "score": 75, "signal": "BOA", "risk": "MODERADO"},
            ]
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que moedas me aconselhas a analisar hoje do top100?"})
    assert r.status_code == 200
    data = r.json()
    assert "SOL" in data["answer"]
    assert "USDT" not in data["answer"]

def test_coinpaprika_top100_mapping():
    from dailyworker.top100_rankings_worker import build_top100_rows, fetch_top100_market_data_coinpaprika

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "id": "btc-bitcoin",
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "rank": 1,
                    "quotes": {
                        "USD": {
                            "price": 70000,
                            "market_cap": 1000000000,
                            "volume_24h": 90000000,
                            "percent_change_24h": 1.0,
                            "percent_change_7d": 5.0,
                            "percent_change_30d": 12.0,
                        }
                    },
                }
            ]

    monkeypatch = __import__("pytest").MonkeyPatch()
    try:
        import requests
        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())
        items = fetch_top100_market_data_coinpaprika()
        rows = build_top100_rows(items)
        assert rows[0]["symbol"] == "BTC"
        assert rows[0]["score"] > 0
    finally:
        monkeypatch.undo()

def test_top100_rows_deduplicate_symbols():
    from dailyworker.top100_rankings_worker import build_top100_rows

    rows = build_top100_rows([
        {
            "id": "abc-first",
            "symbol": "ABC",
            "name": "ABC First",
            "market_cap_rank": 80,
            "market_cap": 1000000,
            "total_volume": 50000,
        },
        {
            "id": "abc-better-rank",
            "symbol": "abc",
            "name": "ABC Better Rank",
            "market_cap_rank": 40,
            "market_cap": 2000000,
            "total_volume": 70000,
        },
        {
            "id": "xyz",
            "symbol": "XYZ",
            "name": "XYZ",
            "market_cap_rank": 41,
            "market_cap": 2000000,
            "total_volume": 70000,
        },
    ])

    assert [row["symbol"] for row in rows].count("ABC") == 1
    assert len(rows) == 2
    assert next(row for row in rows if row["symbol"] == "ABC")["coin_id"] == "abc-better-rank"

def test_top100_rows_skip_stablecoins():
    from dailyworker.top100_rankings_worker import build_top100_rows

    rows = build_top100_rows([
        {"id": "tether", "symbol": "USDT", "name": "Tether", "market_cap_rank": 3},
        {
            "id": "solana",
            "symbol": "SOL",
            "name": "Solana",
            "market_cap_rank": 6,
            "market_cap": 1000000000,
            "total_volume": 100000000,
            "price_change_percentage_24h": 1,
            "price_change_percentage_7d_in_currency": 4,
            "price_change_percentage_30d_in_currency": 12,
        },
    ])

    assert [row["symbol"] for row in rows] == ["SOL"]
