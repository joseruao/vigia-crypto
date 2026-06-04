import importlib.util
from pathlib import Path


def _load_scanner():
    path = Path(__file__).resolve().parents[1] / "worker" / "arkham_scanner.py"
    spec = importlib.util.spec_from_file_location("arkham_scanner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_arkham_scanner_score_candidate_value_and_exchange_count():
    scanner = _load_scanner()

    assert scanner.score_candidate(60_000, 1) == 0
    assert scanner.score_candidate(150_000, 1) == 15
    assert scanner.score_candidate(600_000, 2) == 45
    assert scanner.score_candidate(1_500_000, 3) == 95


def test_arkham_scanner_extracts_common_portfolio_shapes():
    scanner = _load_scanner()

    payload = {
        "tokens": [
            {"symbol": "ABC", "value": 100_000, "amount": 50, "chain": "eth"},
            {"tokenSymbol": "LOW", "valueUsd": 10_000, "balance": 10, "network": "sol"},
        ]
    }

    rows = scanner._extract_token_rows(payload)
    tokens = [scanner._normalize_token(row) for row in rows]

    assert tokens[0]["symbol"] == "ABC"
    assert tokens[0]["chain"] == "ethereum"
    assert tokens[0]["value_usd"] == 100_000
    assert tokens[1]["symbol"] == "LOW"
    assert tokens[1]["chain"] == "solana"


def test_arkham_scanner_extracts_chain_grouped_balances_with_usd_field():
    scanner = _load_scanner()

    payload = {
        "balances": {
            "hyperliquid": [
                {
                    "token": {"symbol": "WHYPE", "name": "wrapped-hype"},
                    "balance": 4_473_000,
                    "price": 66.29,
                    "usd": 296_510_000,
                }
            ]
        },
        "totalBalance": {"hyperliquid": 296_510_000},
    }

    rows = scanner._extract_token_rows(payload)
    token = scanner._normalize_token(rows[0])

    assert token["symbol"] == "WHYPE"
    assert token["chain"] == "hyperliquid"
    assert token["amount"] == 4_473_000
    assert token["value_usd"] == 296_510_000


def test_arkham_scanner_builds_stable_synthetic_token_address(monkeypatch):
    scanner = _load_scanner()
    calls = []
    monkeypatch.setattr(scanner, "supabase_upsert", lambda table, row, cols: calls.append((row, cols)) or True)

    ok = scanner.save_candidate({
        "exchange": "Binance",
        "token": "ABC",
        "chain": "ethereum",
        "amount": 10,
        "value_usd": 200_000,
        "score": 15,
        "exchange_count": 1,
        "token_address": "",
    })

    assert ok is True
    assert calls[0][0]["token_address"] == "arkham:holding:binance:ethereum:ABC"
    assert calls[0][1] == ["token", "exchange"]


def test_arkham_scanner_smart_money_gets_overlap_bonus(monkeypatch):
    scanner = _load_scanner()
    monkeypatch.setattr(
        scanner,
        "fetch_arkham_portfolio",
        lambda slug, min_value_usd: [{
            "symbol": "ABC",
            "chain": "ethereum",
            "amount": 10,
            "value_usd": 150_000,
            "token_address": "0xabc",
        }],
    )
    saved = []
    monkeypatch.setattr(scanner, "save_candidate", lambda candidate, signal_type="holding": saved.append((candidate, signal_type)) or True)
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    monkeypatch.setattr(scanner, "SMART_MONEY_FUNDS", [{"slug": "wintermute", "name": "Wintermute"}])

    count, saved_count = scanner.scan_smart_money({"ABC": {"Binance"}})

    assert count == 1
    assert saved_count == 1
    assert saved[0][1] == "smart_money"
    assert saved[0][0]["score"] == 45
