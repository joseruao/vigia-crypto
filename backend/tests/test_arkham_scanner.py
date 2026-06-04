import importlib.util
import base64
import json
from pathlib import Path
import pytest


def _load_scanner():
    path = Path(__file__).resolve().parents[1] / "worker" / "arkham_scanner.py"
    spec = importlib.util.spec_from_file_location("arkham_scanner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fake_jwt(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


def test_arkham_scanner_score_candidate_value_and_exchange_count():
    scanner = _load_scanner()

    assert scanner.score_candidate(60_000, 1) == 0
    assert scanner.score_candidate(150_000, 1) == 15
    assert scanner.score_candidate(600_000, 2) == 45
    assert scanner.score_candidate(1_500_000, 3) == 95


def test_arkham_scanner_exchange_score_uses_listing_scale():
    scanner = _load_scanner()

    assert scanner.score_exchange_candidate(100_000, 1, exchange="Binance") == 40
    assert scanner.score_exchange_candidate(100_000, 1, exchange="Gate.io", market_cap_usd=1_500_000) == 93
    assert scanner.score_exchange_candidate(100_000, 1, exchange="KuCoin", market_cap_usd=1_500_000) == 93
    assert scanner.score_exchange_candidate(100_000, 1, exchange="Binance", market_cap_usd=1_500_000) == 70
    assert scanner.score_exchange_candidate(1_500_000, 1, exchange="Binance") == 60
    assert scanner.score_exchange_candidate(10_000_000, 2, exchange="Binance") == 88
    assert scanner.score_exchange_candidate(25_000_000, 3, exchange="Coinbase") == 100


def test_arkham_scanner_requires_real_service_role_key(monkeypatch):
    scanner = _load_scanner()
    monkeypatch.setattr(scanner, "ARKHAM_API_KEY", "arkham")
    monkeypatch.setattr(scanner, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(scanner, "SUPABASE_KEY", _fake_jwt({"role": "anon"}))
    monkeypatch.setattr(scanner, "SUPABASE_KEY_SOURCE", "SUPABASE_SERVICE_ROLE_KEY")

    with pytest.raises(RuntimeError, match="jwt_role=anon"):
        scanner._require_env()


def test_arkham_scanner_extracts_common_portfolio_shapes():
    scanner = _load_scanner()

    payload = {
        "tokens": [
            {"symbol": "ABC", "value": 100_000, "amount": 50, "chain": "eth", "marketCapUsd": 1_500_000, "liquidityUsd": 80_000},
            {"tokenSymbol": "LOW", "valueUsd": 10_000, "balance": 10, "network": "sol"},
        ]
    }

    rows = scanner._extract_token_rows(payload)
    tokens = [scanner._normalize_token(row) for row in rows]

    assert tokens[0]["symbol"] == "ABC"
    assert tokens[0]["chain"] == "ethereum"
    assert tokens[0]["value_usd"] == 100_000
    assert tokens[0]["market_cap_usd"] == 1_500_000
    assert tokens[0]["liquidity_usd"] == 80_000
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


def test_arkham_scanner_extracts_list_grouped_balances_with_asset_field():
    scanner = _load_scanner()

    payload = {
        "balances": [
            {
                "chain": "ethereum",
                "assets": [
                    {
                        "asset": {"symbol": "MKR", "name": "maker", "identifier": "maker"},
                        "holdings": 19_501,
                        "marketValueUsd": 30_030_000,
                    }
                ],
            }
        ]
    }

    rows = scanner._extract_token_rows(payload)
    token = scanner._normalize_token(rows[0])

    assert token["symbol"] == "MKR"
    assert token["chain"] == "ethereum"
    assert token["amount"] == 19_501
    assert token["value_usd"] == 30_030_000


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
    assert calls[0][0]["signal_key"] == "holding:binance:ethereum:arkham:holding:binance:ethereum:abc"
    assert calls[0][0]["entity"] == "Binance"
    assert calls[0][0]["entity_type"] == "exchange"
    assert calls[0][0]["exchange_count"] == 1
    assert calls[0][1] == ["signal_key"]


def test_arkham_scanner_signal_direction_is_not_called_sale():
    scanner = _load_scanner()

    assert scanner.signal_direction(100_000, 0) == "new"
    assert scanner.signal_direction(160_000, 100_000) == "increased"
    assert scanner.signal_direction(80_000, 100_000) == "decreased"
    assert scanner.signal_direction(96_000, 100_000) == "flat"
    assert scanner.signal_direction(0, 100_000) == "removed_or_moved"


def test_arkham_scanner_save_candidate_stores_delta_fields(monkeypatch):
    scanner = _load_scanner()
    calls = []
    monkeypatch.setattr(scanner, "supabase_upsert", lambda table, row, cols: calls.append((row, cols)) or True)

    ok = scanner.save_candidate(
        {
            "exchange": "Wintermute",
            "token": "HYPE",
            "chain": "ethereum",
            "amount": 15,
            "value_usd": 1_500_000,
            "score": 65,
            "exchange_count": 1,
            "token_address": "0xhype",
        },
        signal_type="smart_money",
        previous={"value_usd": 1_000_000, "amount": 10},
    )

    row = calls[0][0]
    assert ok is True
    assert row["entity_type"] == "smart_money"
    assert row["previous_value_usd"] == 1_000_000
    assert row["value_delta_usd"] == 500_000
    assert row["value_delta_pct"] == 50
    assert row["previous_amount"] == 10
    assert row["amount_delta"] == 5
    assert row["signal_direction"] == "increased"


def test_arkham_scanner_filters_listed_aliases_and_low_signal_assets():
    scanner = _load_scanner()

    assert scanner.is_listed_on_exchange("sPENDLE", {"PENDLE"})
    assert scanner.is_listed_on_exchange("cbBTC", {"BTC"})
    assert scanner.is_low_signal_exchange_asset("USDT0", {"USDT"})
    assert scanner.is_low_signal_exchange_asset("WETH", {"ETH"})
    assert scanner.is_low_signal_exchange_asset("BSC-USD", set())
    assert scanner.is_low_signal_exchange_asset("XAUT0", set())
    assert scanner.is_low_signal_smart_money_asset("NVDAON")
    assert scanner.is_low_signal_smart_money_asset("USDBC")
    assert not scanner.is_low_signal_exchange_asset("BEAM", {"BTC", "ETH"})
    assert not scanner.is_low_signal_smart_money_asset("HYPE")


def test_arkham_scanner_excludes_prompted_symbols_prefixes_suffixes_and_huge_values():
    scanner = _load_scanner()

    for symbol in ("USYC", "BSC-USD", "WETH", "SPENDLE", "SENA", "BTCB", "PAXG", "SOL"):
        assert scanner.is_excluded_arkham_token(symbol, 100_000)
    for symbol in ("WIF", "CBTOKEN", "STOKEN", "BSCFOO", "USDABC", "EURABC", "FOOBTC", "FOOUSDT"):
        assert scanner.is_excluded_arkham_token(symbol, 100_000)
    assert scanner.is_excluded_arkham_token("ALPHA", 500_000_001)
    assert not scanner.is_excluded_arkham_token("ALPHA", 100_000)


def test_arkham_scanner_static_binance_listed_fallback(monkeypatch):
    scanner = _load_scanner()

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return []

    monkeypatch.setattr(scanner.requests, "get", lambda *args, **kwargs: Response())

    listed = scanner.fetch_listed_tokens("Binance")

    assert "BEAM" in listed
    assert "BABYDOGE" in listed


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


def test_arkham_scanner_smart_money_skips_low_score_noise(monkeypatch):
    scanner = _load_scanner()
    monkeypatch.setattr(
        scanner,
        "fetch_arkham_portfolio",
        lambda slug, min_value_usd: [
            {
                "symbol": "ABC",
                "chain": "ethereum",
                "amount": 10,
                "value_usd": 150_000,
                "token_address": "0xabc",
            },
            {
                "symbol": "NVDAON",
                "chain": "ethereum",
                "amount": 10,
                "value_usd": 900_000,
                "token_address": "0xstock",
            },
        ],
    )
    saved = []
    monkeypatch.setattr(scanner, "save_candidate", lambda candidate, signal_type="holding": saved.append((candidate, signal_type)) or True)
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    monkeypatch.setattr(scanner, "SMART_MONEY_FUNDS", [{"slug": "wintermute", "name": "Wintermute"}])

    count, saved_count = scanner.scan_smart_money({})

    assert count == 0
    assert saved_count == 0
    assert saved == []


def test_arkham_scanner_smart_money_delta_tracks_increase(monkeypatch):
    scanner = _load_scanner()
    old_key = "smart_money:wintermute:ethereum:0xabc"
    monkeypatch.setattr(
        scanner,
        "fetch_existing_signals",
        lambda entity, entity_type: {
            old_key: {
                "signal_key": old_key,
                "token": "ABC",
                "chain": "ethereum",
                "token_address": "0xabc",
                "amount": 10,
                "value_usd": 100_000,
                "exchange_count": 1,
            }
        },
    )
    monkeypatch.setattr(
        scanner,
        "fetch_arkham_portfolio",
        lambda slug, min_value_usd: [{
            "symbol": "ABC",
            "chain": "ethereum",
            "amount": 15,
            "value_usd": 180_000,
            "token_address": "0xabc",
        }],
    )
    saved = []
    monkeypatch.setattr(
        scanner,
        "save_candidate",
        lambda candidate, signal_type="holding", previous=None: saved.append((candidate, signal_type, previous)) or True,
    )
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    monkeypatch.setattr(scanner, "SMART_MONEY_FUNDS", [{"slug": "wintermute", "name": "Wintermute"}])

    count, saved_count = scanner.scan_smart_money_with_deltas({"ABC": {"Binance"}})

    assert count == 1
    assert saved_count == 1
    assert saved[0][1] == "smart_money"
    assert saved[0][2]["value_usd"] == 100_000
    assert saved[0][0]["score"] > scanner.score_candidate(180_000, 1)


def test_arkham_scanner_smart_money_marks_missing_position_as_moved(monkeypatch):
    scanner = _load_scanner()
    old_key = "smart_money:wintermute:ethereum:0xabc"
    monkeypatch.setattr(
        scanner,
        "fetch_existing_signals",
        lambda entity, entity_type: {
            old_key: {
                "signal_key": old_key,
                "token": "ABC",
                "chain": "ethereum",
                "token_address": "0xabc",
                "amount": 10,
                "value_usd": 150_000,
                "exchange_count": 1,
            }
        },
    )
    monkeypatch.setattr(scanner, "fetch_arkham_portfolio", lambda slug, min_value_usd: [])
    saved = []
    monkeypatch.setattr(
        scanner,
        "save_candidate",
        lambda candidate, signal_type="holding", previous=None: saved.append((candidate, signal_type, previous)) or True,
    )
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    monkeypatch.setattr(scanner, "SMART_MONEY_FUNDS", [{"slug": "wintermute", "name": "Wintermute"}])

    count, saved_count = scanner.scan_smart_money_with_deltas({})

    assert count == 1
    assert saved_count == 1
    assert saved[0][0]["token"] == "ABC"
    assert saved[0][0]["value_usd"] == 0
    assert saved[0][2]["value_usd"] == 150_000
    assert scanner.signal_direction(saved[0][0]["value_usd"], saved[0][2]["value_usd"]) == "removed_or_moved"


def test_arkham_scanner_exchange_scan_uses_separate_signal_type(monkeypatch):
    scanner = _load_scanner()
    monkeypatch.setattr(
        scanner,
        "fetch_arkham_portfolio",
        lambda slug, min_value_usd: [{
            "symbol": "ABC",
            "chain": "ethereum",
            "amount": 10,
            "value_usd": 200_000,
            "token_address": "0xabc",
            "market_cap_usd": 2_000_000,
            "liquidity_usd": 250_000,
        }],
    )
    monkeypatch.setattr(scanner, "fetch_listed_tokens", lambda exchange: set())
    monkeypatch.setattr(scanner.time, "sleep", lambda _: None)
    monkeypatch.setattr(scanner, "EXCHANGES", [{"slug": "binance", "exchange": "Binance"}])
    saved = []
    monkeypatch.setattr(scanner, "save_candidate", lambda candidate, signal_type="holding": saved.append((candidate, signal_type)) or True)

    token_exchanges, count, saved_count = scanner.scan_exchange_candidates()

    assert token_exchanges == {"ABC": {"Binance"}}
    assert count == 1
    assert saved_count == 1
    assert saved[0][1] == "arkham_exchange"


def test_arkham_scanner_limits_entities_from_env(monkeypatch):
    scanner = _load_scanner()
    monkeypatch.setenv("ARKHAM_EXCHANGE_SLUGS", "binance")

    filtered = scanner._limit_entities(scanner.EXCHANGES, "ARKHAM_EXCHANGE_SLUGS")

    assert len(filtered) == 1
    assert filtered[0]["slug"] == "binance"
