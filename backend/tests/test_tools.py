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


def test_get_listing_predictions_formats_existing_predictions(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "get_predictions",
        lambda: [{"token": "MEW", "exchange": "Gate.io", "score": 82, "value_usd": 1000, "liquidity": 2000000}],
    )

    result = tools.get_listing_predictions()

    assert result["count"] == 1
    assert "MEW" in result["answer"]
    assert "Gate.io" in result["answer"]


def test_get_listing_predictions_handles_empty_list(monkeypatch):
    monkeypatch.setattr(tools.alerts, "get_predictions", lambda: [])

    result = tools.get_listing_predictions()

    assert result["count"] == 0
    assert "Nao encontrei" in result["answer"]


def test_get_recent_holdings_formats_existing_holdings(monkeypatch):
    monkeypatch.setattr(
        tools.alerts,
        "get_holdings",
        lambda: {"items": [{"token": "ALCH", "exchange": "Gate.io", "score": 91, "value_usd": 18000000}]},
    )

    result = tools.get_recent_holdings()

    assert result["count"] == 1
    assert "ALCH" in result["answer"]


def test_get_recent_holdings_handles_empty_list(monkeypatch):
    monkeypatch.setattr(tools.alerts, "get_holdings", lambda: {"items": []})

    result = tools.get_recent_holdings()

    assert result["count"] == 0
    assert "Nao encontrei" in result["answer"]


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

