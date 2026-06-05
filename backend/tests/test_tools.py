import asyncio
import sys
from types import SimpleNamespace

from Api.services import tools


def test_parse_tool_arguments_handles_valid_json():
    assert tools.parse_tool_arguments('{"symbol":"BTC"}') == {"symbol": "BTC"}


def test_parse_tool_arguments_handles_invalid_json():
    assert tools.parse_tool_arguments("{bad") == {}


def test_parse_tool_arguments_handles_non_object_json():
    assert tools.parse_tool_arguments('["BTC"]') == {}


def test_get_top100_rankings_calls_existing_alerts_code(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools.alerts,
        "_answer_top100_buy_watchlist",
        lambda log=None, prompt="": calls.append(prompt) or {"ok": True, "answer": "TOP100"},
    )

    result = tools.get_top100_rankings("low_risk")

    assert result["answer"] == "TOP100"
    assert "menos risco" in calls[0]


def test_get_top100_delta_calls_existing_alerts_code(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "_answer_top100_buy_watchlist",
        lambda log=None, prompt="": {"ok": True, "answer": prompt},
    )

    result = tools.get_top100_delta()

    assert "mudou no top100" in result["answer"]


def test_get_listing_predictions_uses_existing_ask_formatter(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "get_predictions",
        lambda: [{
            "token": "MEW",
            "exchange": "Gate.io",
            "chain": "solana",
            "score": 80,
            "value_usd": 250000,
            "liquidity": 1000000,
            "pair_url": "https://dexscreener.com/search?q=MEW",
        }],
    )

    result = tools.get_listing_predictions()

    assert result["count"] == 1
    assert "MEW" in result["answer"]


def test_get_listing_predictions_preserves_empty_ask_response(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "get_predictions",
        lambda: [],
    )

    result = tools.get_listing_predictions()

    assert result["ok"] is True
    assert "No fresh unlisted-token signals" in result["answer"]


def test_get_recent_holdings_uses_existing_ask_formatter(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tools.alerts,
        "ask_alerts",
        lambda payload: calls.append(payload.prompt) or {"ok": True, "answer": "ALCH Gate.io", "count": 1},
    )

    result = tools.get_recent_holdings()

    assert result["count"] == 1
    assert "ALCH" in result["answer"]
    assert calls == ["mostra holdings recentes"]


def test_get_recent_holdings_preserves_empty_ask_response(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "ask_alerts",
        lambda payload: {"ok": True, "answer": "Nao encontrei holdings", "count": 0, "items": []},
    )

    result = tools.get_recent_holdings()

    assert result["count"] == 0
    assert "Nao encontrei" in result["answer"]


def test_get_smart_money_formats_supabase_rows(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        def json(self):
            return [{
                "token": "ABC",
                "entity": "Wintermute",
                "chain": "ethereum",
                "score": 88,
                "value_usd": 1_250_000,
                "value_delta_usd": 250_000,
                "signal_direction": "increased",
                "pair_url": "https://dexscreener.com/search?q=ABC",
            }]

    def fake_rest_get(table, params=None, **kwargs):
        calls.append((table, params or {}))
        return FakeResponse()

    monkeypatch.setattr(tools.alerts.supa, "rest_get", fake_rest_get)

    result = tools.get_smart_money()

    assert result["count"] == 1
    assert "ABC" in result["answer"]
    assert "Wintermute" in result["answer"]
    assert "$1,250,000" in result["answer"]
    assert "Delta $250,000" in result["answer"]
    assert calls[0][0] == "arkham_signals"
    assert calls[0][1]["signal_direction"] == "in.(new,increased,decreased)"


def test_get_smart_money_orders_by_delta(monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return [
                {"token": "LOW", "entity": "Wintermute", "chain": "ethereum", "score": 99, "value_usd": 10_000_000, "value_delta_usd": 20_000, "signal_direction": "increased"},
                {"token": "HIGH", "entity": "Galaxy", "chain": "ethereum", "score": 50, "value_usd": 1_000_000, "value_delta_usd": 500_000, "signal_direction": "increased"},
            ]

    monkeypatch.setattr(tools.alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    result = tools.get_smart_money()

    assert result["answer"].find("HIGH") < result["answer"].find("LOW")


def test_get_smart_money_formats_portuguese_response(monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return [{
                "token": "HYPE",
                "entity": "Wintermute",
                "chain": "hyperevm",
                "score": 60,
                "value_usd": 1_000_000,
                "value_delta_usd": 120_000,
                "signal_direction": "increased",
            }]

    monkeypatch.setattr(tools.alerts.supa, "rest_get", lambda *args, **kwargs: FakeResponse())

    result = tools.get_smart_money("pt")

    assert "Movimentos de whales" in result["answer"]
    assert "aumentou" in result["answer"]
    assert "Variacao $120,000" in result["answer"]


def test_execute_tool_dispatches_known_sync_tool(monkeypatch):
    monkeypatch.setattr(tools, "get_listing_predictions", lambda: {"ok": True, "answer": "LISTINGS"})

    result = asyncio.run(tools.execute_tool("get_listing_predictions"))

    assert result["answer"] == "LISTINGS"


def test_execute_tool_rejects_unknown_tool():
    result = asyncio.run(tools.execute_tool("missing_tool"))

    assert result["ok"] is False
    assert "desconhecida" in result["answer"]


def test_analyze_coin_wraps_existing_analysis_tool(monkeypatch):
    async def fake_analyze(symbol):
        return {
            "snapshot_only": True,
            "current_price": 10,
            "chain": "solana",
            "dex": "raydium",
            "liquidity_usd": 100000,
            "volume_24h": 10000,
            "pair_url": "https://dexscreener.com/solana/test",
        }

    monkeypatch.setitem(
        sys.modules,
        "Api.services.crypto_tools",
        SimpleNamespace(analyze_coin_tool=fake_analyze),
    )

    result = asyncio.run(tools.analyze_coin("btc"))

    assert result["symbol"] == "BTC"
    assert "BTC" in result["answer"]
    assert result["result"]["snapshot_only"] is True


def test_analyze_coin_returns_tool_error(monkeypatch):
    async def fake_analyze(symbol):
        return {"error": "sem dados"}

    monkeypatch.setitem(
        sys.modules,
        "Api.services.crypto_tools",
        SimpleNamespace(analyze_coin_tool=fake_analyze),
    )

    result = asyncio.run(tools.analyze_coin("BTC"))

    assert result["error"] == "sem dados"
    assert "Erro ao analisar BTC" in result["answer"]
