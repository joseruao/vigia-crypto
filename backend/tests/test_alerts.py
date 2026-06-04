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
    assert alerts._is_buy_watchlist_question("quais as melhores moedas para analisar hoje?")
    assert alerts._is_buy_watchlist_question("quais moedas estao perto do suporte?")
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
        lambda log=None, prompt="": {"ok": True, "answer": "RANKING TOP100 TESTE", "count": 1, "items": []},
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

def test_listing_answer_uses_onchain_signal_language(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(alerts, "_load_listed_tokens_map", lambda log=None: {})

    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {
                    "exchange": "Gate.io",
                    "token": "ALPHA",
                    "token_address": "addr",
                    "chain": "solana",
                    "score": 82,
                    "ts": "2026-06-02T12:00:00+00:00",
                    "value_usd": 250000,
                    "liquidity": 3000000,
                    "volume_24h": 800000,
                    "pair_url": "https://dexscreener.com/solana/example",
                }
            ]

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que tokens achas que vao ser listados?"})

    assert r.status_code == 200
    answer = r.json()["answer"]
    assert "Radar on-chain de possiveis listings" in answer
    assert "Detectado na wallet monitorizada da **Gate.io**" in answer
    assert "Wallet:** $250K" in answer

def test_listing_answer_limits_initial_results_and_supports_more(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(alerts, "_load_listed_tokens_map", lambda log=None: {})

    rows = [
        {
            "exchange": "Gate.io",
            "token": f"TOK{i}",
            "token_address": f"addr{i}",
            "chain": "solana",
            "score": 80 - i,
            "ts": "2026-06-02T12:00:00+00:00",
            "value_usd": 250000 + i,
            "liquidity": 3000000,
            "volume_24h": 800000,
            "pair_url": f"https://dexscreener.com/solana/example{i}",
        }
        for i in range(6)
    ]

    class FakeResponse:
        status_code = 200
        def json(self):
            return rows

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)

    first = client.post("/alerts/ask", json={"prompt": "que tokens achas que vao ser listados?"}).json()["answer"]
    more = client.post("/alerts/ask", json={"prompt": "ver mais listings"}).json()["answer"]

    assert "Mostro 3" in first
    assert "+ 3 sinais ocultos" in first
    assert "Mostro 6" in more

def test_top100_buy_question_uses_ranking_table(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "price": 70000,
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
    assert "Bitcoin" in data["answer"]
    assert "analisa BTC" in data["answer"]

def test_top100_delta_question_does_not_route_to_recent_holdings(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(
        alerts,
        "_answer_top100_buy_watchlist",
        lambda log=None, prompt="": {"ok": True, "answer": "TOP100 DELTA TESTE", "count": 1, "items": []},
    )

    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "O que mudou no top100 desde ontem?"})

    assert r.status_code == 200
    assert r.json()["answer"] == "TOP100 DELTA TESTE"

def test_top100_answer_filters_stablecoins(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"symbol": "USDT", "name": "Tether", "price": 1, "score": 99, "signal": "FORTE", "risk": "BAIXO"},
                {"symbol": "SOL", "name": "Solana", "price": 100, "score": 75, "signal": "BOA", "risk": "MODERADO"},
            ]
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que moedas me aconselhas a analisar hoje do top100?"})
    assert r.status_code == 200
    data = r.json()
    assert "SOL" in data["answer"]
    assert "USDT" not in data["answer"]

def test_predictions_filter_stable_fiat_tokens(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(alerts, "_load_listed_tokens_map", lambda log=None: {})

    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {
                    "exchange": "Upbit",
                    "token": "EURC",
                    "token_address": "0xeurc",
                    "chain": "ethereum",
                    "score": 92,
                    "ts": "2026-06-03T12:00:00+00:00",
                    "value_usd": 1_000_000,
                    "liquidity": 5_000_000,
                },
                {
                    "exchange": "Gate.io",
                    "token": "ALPHA",
                    "token_address": "0xalpha",
                    "chain": "ethereum",
                    "score": 75,
                    "ts": "2026-06-03T12:00:00+00:00",
                    "value_usd": 300_000,
                    "liquidity": 2_000_000,
                },
            ]

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "que tokens vao ser listados?"})
    answer = r.json()["answer"]
    assert "ALPHA" in answer
    assert "EURC" not in answer

def test_predictions_filter_wrapped_and_staked_derivatives():
    rows = [
        {"exchange": "Binance 8", "token": "cbBTC", "token_address": "0xcbbtc", "chain": "ethereum", "score": 90},
        {"exchange": "Binance 8", "token": "sPENDLE", "token_address": "0xspendle", "chain": "ethereum", "score": 90},
        {"exchange": "Binance 8", "token": "ALPHA", "token_address": "0xalpha", "chain": "ethereum", "score": 80},
    ]

    filtered = alerts._filter_prediction_rows(rows, {"Binance": set()})

    assert [row["token"] for row in filtered] == ["ALPHA"]

def test_predictions_endpoint_does_not_backfill_old_rows(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(alerts, "_load_listed_tokens_map", lambda log=None: {})

    calls = {"count": 0}

    class FakeResponse:
        status_code = 200
        def __init__(self, rows):
            self._rows = rows
        def json(self):
            return self._rows

    def fake_rest_get(table, params=None, timeout=8):
        calls["count"] += 1
        assert params and "ts" in params
        return FakeResponse([])

    monkeypatch.setattr(alerts.supa, "rest_get", fake_rest_get)
    client = TestClient(app)

    r = client.get("/alerts/predictions")

    assert r.status_code == 200
    assert r.json() == []
    assert calls["count"] == 1

def test_listing_ask_does_not_backfill_old_rows_by_default(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    monkeypatch.setattr(alerts, "_load_listed_tokens_map", lambda log=None: {})

    calls = {"count": 0}

    class FakeResponse:
        status_code = 200
        def json(self):
            return []

    def fake_rest_get(table, params=None, timeout=8):
        calls["count"] += 1
        assert params and "ts" in params
        return FakeResponse()

    monkeypatch.setattr(alerts.supa, "rest_get", fake_rest_get)
    client = TestClient(app)

    r = client.post("/alerts/ask", json={"prompt": "que tokens vao ser listados?"})

    assert r.status_code == 200
    assert "Nao encontrei tokens com potencial" in r.json()["answer"]
    assert calls["count"] == 1

def test_top100_endpoint_filters_zero_price(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)

    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"symbol": "FLR", "name": "Flare", "price": 0, "score": 90, "current_position": 20},
                {"symbol": "TAO", "name": "Bittensor", "price": 227, "score": 80, "current_position": 25},
            ]

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)

    r = client.get("/alerts/top100?mode=near_support&limit=5")

    assert r.status_code == 200
    data = r.json()
    assert [row["symbol"] for row in data["items"]] == ["TAO"]

def test_top100_risk_question_sorts_by_low_risk(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"symbol": "RISKY", "name": "Risky", "price": 10, "score": 95, "risk": "ELEVADO", "signal": "FORTE"},
                {"symbol": "SAFE", "name": "Safe", "price": 10, "score": 70, "risk": "BAIXO/MODERADO", "signal": "BOA"},
            ]
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "quais moedas do top100 têm menos risco?"})
    assert r.status_code == 200
    answer = r.json()["answer"]
    assert answer.index("SAFE") < answer.index("RISKY")

def test_top100_support_question_sorts_by_current_position(monkeypatch):
    monkeypatch.setattr(alerts.supa, "ok", lambda: True)
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"symbol": "HIGH", "name": "High", "price": 10, "score": 90, "current_position": 90, "risk": "MODERADO"},
                {"symbol": "SUP", "name": "Support", "price": 10, "score": 70, "current_position": 24, "risk": "MODERADO"},
            ]
    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    r = client.post("/alerts/ask", json={"prompt": "quais do top100 estão perto do suporte?"})
    assert r.status_code == 200
    answer = r.json()["answer"]
    assert answer.index("SUP") < answer.index("HIGH")

def test_predictions_backfill_merges_recent_and_historical():
    recent = [{"exchange": "Gate.io", "token": "AAA", "chain": "solana", "score": 80}]
    fallback = [
        {"exchange": "Gate.io", "token": "AAA", "chain": "solana", "score": 80},
        {"exchange": "Binance 2", "token": "BBB", "chain": "solana", "score": 75},
        {"exchange": "Binance 2", "token": "CCC", "chain": "solana", "score": 74},
    ]

    merged = alerts._merge_prediction_backfill(recent, fallback)
    assert [row["token"] for row in merged] == ["AAA", "BBB", "CCC"]

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

def test_top100_technical_enrichment_reorders_by_setup(monkeypatch):
    import asyncio
    from dailyworker import top100_rankings_worker as worker

    def fake_analyze(row):
        if row["symbol"] == "GOOD":
            return {
                "rsi": 34,
                "trend": "UPTREND",
                "trend_strength": 2.1,
                "volatility": 3.2,
                "volume_ratio_20d": 1.4,
                "support": 8,
                "resistance": 12,
                "current_position": 30,
                "entry_zone": "ZONA_DE_COMPRA",
                "stop_loss": "7.5",
                "targets": ["11 - 12 (30%)"],
                "technical_action": "COMPRA",
                "technical_confidence": "ALTA",
            }
        return {
            "rsi": 78,
            "trend": "UPTREND",
            "trend_strength": 8,
            "volatility": 6,
            "volume_ratio_20d": 1,
            "support": 5,
            "resistance": 10,
            "current_position": 90,
            "entry_zone": "ZONA_DE_VENDA",
            "technical_action": "AGUARDAR",
            "technical_confidence": "MEDIA",
        }

    monkeypatch.setattr(worker, "_analyze_symbol_technical_sync", fake_analyze)
    rows = [
        {"symbol": "PUMP", "rank": 10, "score": 90, "rationale": "pump"},
        {"symbol": "GOOD", "rank": 50, "score": 60, "rationale": "base"},
    ]

    enriched = asyncio.run(worker.enrich_rows_with_technical(rows, max_symbols=2))
    assert enriched[0]["symbol"] == "GOOD"
    assert enriched[0]["rsi"] == 34
    assert enriched[1]["signal"] == "AGUARDAR"

def test_daily_holdings_upsert_keeps_exchange_dimension(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    calls = []
    monkeypatch.setattr(worker, "supabase_upsert", lambda *args, **kwargs: calls.append(args) or True)

    ok = worker.save_holding_to_supabase(
        {
            "symbol": "MEW",
            "balance": 10,
            "value_usd": 1000,
            "address": "MEW1",
            "liquidity": 5000000,
            "volume_24h": 100000,
            "price": 0.1,
            "pair_url": "https://dexscreener.com/solana/example",
            "score": 84,
            "chain": "solana",
        },
        "Bitget",
    )

    assert ok is True
    assert calls
    assert calls[0][2] == ["token_address", "type", "chain", "exchange"]

def test_daily_holdings_upsert_falls_back_before_schema_migration(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    calls = []
    monkeypatch.setattr(
        worker,
        "supabase_upsert",
        lambda *args, **kwargs: calls.append(args) or len(calls) > 1,
    )

    ok = worker.save_holding_to_supabase(
        {
            "symbol": "MEW",
            "balance": 10,
            "value_usd": 1000,
            "address": "MEW1",
            "liquidity": 5000000,
            "volume_24h": 100000,
            "price": 0.1,
            "pair_url": "https://dexscreener.com/solana/example",
            "score": 84,
            "chain": "solana",
        },
        "Bitget",
    )

    assert ok is True
    assert calls[0][2] == ["token_address", "type", "chain", "exchange"]
    assert calls[1][2] == ["token_address", "type", "chain"]

def test_daily_holdings_has_bnb_and_avax_wallets_configured():
    from dailyworker import daily_holdings_worker as worker

    assert worker.MIN_SCORE_SAVE == 50
    assert worker.MIN_SCORE_ALERT == 70
    assert worker.BNB_WALLETS["Binance BNB 51"].lower() == "0x8894e0a0c962cb723c1976a4421c95949be2d4e3"
    assert worker.BNB_WALLETS["Binance BNB 7"].lower() == "0xbe0eb53f3423e596e0c4977b08c8dcfff7b2404d33e8"
    assert worker.BNB_WALLETS["Gate BNB Deposit Funder"].lower() == "0x8ef254930467ad31ce808139f43d88f08f340699"
    assert worker.AVALANCHE_WALLETS["Binance AVAX 74"].lower() == "0xa7c0d36c4698981fab42a7d8c783674c6fe2592d"
    assert worker.AVALANCHE_WALLETS["Binance AVAX Hot Wallet 10"].lower() == "0x9f8e59d4a052f9ed22d2d10db0fe18328248ac8b"
    assert worker.EXCHANGE_NORMALIZE["Binance 8"] == "Binance"
    assert worker.EXCHANGE_NORMALIZE["Binance BNB 51"] == "Binance"
    assert worker.EXCHANGE_NORMALIZE["Binance AVAX 74"] == "Binance"

def test_daily_holdings_etherscan_v2_chainids_are_configured(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    monkeypatch.setattr(worker, "ETHERSCAN_API_KEY", "test-key")
    monkeypatch.setattr(worker, "BSCSCAN_API_KEY", "bsc-key")
    monkeypatch.setattr(worker, "SNOWSCAN_API_KEY", "snow-key")

    assert worker._evm_api_config("ethereum") == ("https://api.etherscan.io/v2/api", "test-key", "1")
    assert worker._evm_api_config("bsc") == ("https://api.bscscan.com/api", "bsc-key", None)
    assert worker._evm_api_config("avalanche") == ("https://api.snowscan.xyz/api", "snow-key", None)
    assert worker._evm_api_configs("bsc")[1] == ("https://api.etherscan.io/v2/api", "test-key", "56")
    assert worker._evm_api_configs("avalanche")[1] == ("https://api.etherscan.io/v2/api", "test-key", "43114")

def test_daily_holdings_dexscreener_handles_null_pairs(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    class Response:
        status_code = 200
        def json(self):
            return {"pairs": None}

    monkeypatch.setattr(worker.requests, "get", lambda *args, **kwargs: Response())

    data = worker.get_token_data_dexscreener("0xabc", chain="ethereum")
    assert data["symbol"] == "UNKNOWN"
    assert data["price"] == 0

def test_daily_holdings_filters_stable_fiat_symbols():
    from dailyworker import daily_holdings_worker as worker

    assert worker.is_stable_or_wrapped_token("EURC") is True
    assert worker.is_stable_or_wrapped_token("USD1") is True
    assert worker.is_stable_or_wrapped_token("ALPHA") is False

def test_daily_holdings_binance_live_listing_fallback(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    worker._LIVE_LISTING_CACHE.clear()
    monkeypatch.setattr(worker, "supabase_query", lambda *args, **kwargs: [])
    monkeypatch.setattr(worker, "_fetch_live_exchange_tokens", lambda exchange: {"TRUMP", "BTC", "BEAM"})

    assert worker.is_token_listed_on_exchange("TRUMP", "Binance 2") is True
    assert worker.is_token_listed_on_exchange("BEAM", "Binance 8") is True

def test_daily_holdings_filters_wrapped_and_staked_derivatives():
    from dailyworker import daily_holdings_worker as worker

    assert worker.is_stable_or_wrapped_token("cbBTC") is True
    assert worker.is_stable_or_wrapped_token("sPENDLE") is True
    assert worker.is_stable_or_wrapped_token("ALPHA") is False

def test_evm_chain_disables_after_unsupported_provider(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    worker.EVM_CHAIN_DISABLED_REASON.clear()
    calls = {"count": 0}

    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "status": "0",
                "message": "NOTOK",
                "result": "Free API access is not supported for this chain.",
            }

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(worker, "BSCSCAN_API_KEY", "bsc-key")
    monkeypatch.setattr(worker, "ETHERSCAN_API_KEY", "")
    monkeypatch.setattr(worker.requests, "get", fake_get)

    import asyncio
    assert asyncio.run(worker.get_ethereum_holdings("0xabc", "Binance BNB 7", "bsc")) == []
    assert asyncio.run(worker.get_ethereum_holdings("0xdef", "Binance BNB 51", "bsc")) == []
    assert calls["count"] == 1
    worker.EVM_CHAIN_DISABLED_REASON.clear()

def test_daily_holdings_skips_telegram_for_listed_token(monkeypatch):
    import asyncio
    from dailyworker import daily_holdings_worker as worker

    sent = []
    saved = []
    monkeypatch.setattr(
        worker,
        "get_solana_holdings",
        lambda wallet, name: [{
            "symbol": "TRUMP",
            "balance": 1,
            "value_usd": 1_000_000,
            "address": "TRUMPADDR",
            "liquidity": 5_000_000,
            "volume_24h": 1_000_000,
            "price": 1,
            "pair_url": "",
            "score": 91,
            "chain": "solana",
        }],
    )
    monkeypatch.setattr(worker, "save_holding_to_supabase", lambda holding, wallet: saved.append(holding) or True)
    monkeypatch.setattr(worker, "is_token_listed_on_exchange", lambda symbol, wallet: True)
    monkeypatch.setattr(worker, "send_telegram_alert", lambda holding, wallet: sent.append(holding))

    result = asyncio.run(worker.analyze_wallet_holdings("Binance 2", "wallet", "solana"))

    assert result == 1
    assert saved
    assert sent == []

def test_daily_holdings_sends_telegram_for_unlisted_score_70(monkeypatch):
    import asyncio
    from dailyworker import daily_holdings_worker as worker

    sent = []
    monkeypatch.setattr(
        worker,
        "get_solana_holdings",
        lambda wallet, name: [{
            "symbol": "DOGEBALL",
            "balance": 1,
            "value_usd": 250000,
            "address": "DOGEBALLADDR",
            "liquidity": 5000000,
            "volume_24h": 1000000,
            "price": 1,
            "pair_url": "",
            "score": 73.9,
            "chain": "solana",
        }],
    )
    monkeypatch.setattr(worker, "save_holding_to_supabase", lambda holding, wallet: True)
    monkeypatch.setattr(worker, "is_token_listed_on_exchange", lambda symbol, wallet: False)
    monkeypatch.setattr(worker, "send_telegram_alert", lambda holding, wallet: sent.append((holding, wallet)))

    result = asyncio.run(worker.analyze_wallet_holdings("Bitget", "wallet", "solana"))

    assert result == 1
    assert sent[0][0]["symbol"] == "DOGEBALL"

def test_predictions_filter_uses_live_binance_fallback(monkeypatch):
    monkeypatch.setattr(alerts, "_load_live_listing_fallbacks", lambda log=None: {"Binance": {"TRUMP"}})

    class FakeResponse:
        status_code = 200
        def json(self):
            return []

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    listed = alerts._load_listed_tokens_map()
    rows = [{
        "exchange": "Binance 8",
        "token": "TRUMP",
        "token_address": "TRUMPADDR",
        "chain": "solana",
        "score": 95,
        "value_usd": 1000000,
        "liquidity": 5000000,
    }]

    assert listed["Binance"] == {"TRUMP"}
    assert alerts._filter_prediction_rows(rows, listed) == []

def test_predictions_filter_live_binance_blocks_missing_table_token(monkeypatch):
    monkeypatch.setattr(alerts, "_load_live_listing_fallbacks", lambda log=None: {"Binance": {"BEAM"}})

    rows = [{
        "exchange": "Binance 8",
        "token": "BEAM",
        "token_address": "BEAMADDR",
        "chain": "ethereum",
        "score": 95,
        "value_usd": 14_000_000,
        "liquidity": 2_600_000,
    }]

    assert alerts._filter_prediction_rows(rows, {"Binance": set()}) == []

def test_predictions_filter_only_blocks_own_exchange_listing():
    listed = {
        "Binance": {"TRUMP"},
        "Gate.io": {"BTC"},
    }
    rows = [{
        "exchange": "Gate.io",
        "token": "TRUMP",
        "token_address": "TRUMPGATE",
        "chain": "solana",
        "score": 95,
        "value_usd": 1000000,
        "liquidity": 5000000,
    }]

    assert len(alerts._filter_prediction_rows(rows, listed)) == 1

def test_predictions_listing_map_falls_back_when_supabase_fails(monkeypatch):
    monkeypatch.setattr(alerts, "_load_live_listing_fallbacks", lambda log=None: {"Binance": {"BTC", "TRUMP"}})

    class FakeResponse:
        status_code = 500
        text = "boom"
        def json(self):
            return []

    monkeypatch.setattr(alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    assert alerts._load_listed_tokens_map()["Binance"] == {"BTC", "TRUMP"}

def test_daily_holdings_telegram_alert_has_richer_listing_format(monkeypatch):
    from dailyworker import daily_holdings_worker as worker

    posted = {}
    monkeypatch.setattr(worker, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(worker, "TELEGRAM_CHAT_ID", "chat")

    def fake_post(url, json, timeout):
        posted["url"] = url
        posted["json"] = json
        posted["timeout"] = timeout
        class Response:
            status_code = 200
        return Response()

    monkeypatch.setattr(worker.requests, "post", fake_post)

    worker.send_telegram_alert(
        {
            "symbol": "DOOD",
            "score": 86,
            "value_usd": 226762,
            "liquidity": 1134402,
            "volume_24h": 619714,
            "price": 0.00862,
            "price_change_24h": 7.38,
            "chain": "bsc",
            "address": "0xabc",
            "pair_url": "https://dexscreener.com/bsc/example",
        },
        "Bybit BNB 17",
    )

    text = posted["json"]["text"]
    assert "EXCHANGE WALLET ALERT" in text
    assert "Exchange:* Bybit" in text
    assert "Token:* DOOD" in text
    assert "BNB Chain" in text
    assert "Preço atual" in text
    assert "+7.38%" in text
    assert "Score:* 86/100" in text
    assert "bscscan.com/token/0xabc" in text
