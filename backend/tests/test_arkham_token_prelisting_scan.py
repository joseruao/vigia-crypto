import importlib.util
from datetime import datetime, timezone
from pathlib import Path


def _load_prelisting():
    path = Path(__file__).resolve().parents[1] / "worker" / "arkham_token_prelisting_scan.py"
    spec = importlib.util.spec_from_file_location("arkham_token_prelisting_scan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_prelisting_aggregates_large_recipient_transfers(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "MIN_TRANSFER_USD", 50_000)
    monkeypatch.setattr(scan, "SKIP_INFRA_SOURCES", False)

    transfers = [
        {
            "fromAddress": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "arkhamEntity": {"name": "Project Treasury"}},
            "toAddress": {"address": "0x1111111111111111111111111111111111111111", "chain": "ethereum"},
            "chain": "ethereum",
            "historicalUSD": 125_000,
            "blockTimestamp": "2026-04-20T00:00:00Z",
            "tokenSymbol": "AIGENSYN",
            "transactionHash": "0xabc",
        },
        {
            "fromAddress": {"address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "arkhamEntity": {"name": "Market Maker"}},
            "toAddress": {"address": "0x1111111111111111111111111111111111111111", "chain": "ethereum"},
            "chain": "ethereum",
            "historicalUSD": 75_000,
            "blockTimestamp": "2026-04-21T00:00:00Z",
            "tokenSymbol": "AIGENSYN",
            "transactionHash": "0xdef",
        },
    ]

    candidates = scan.aggregate_accumulation(transfers)

    row = candidates["0x1111111111111111111111111111111111111111"]
    assert row["total_in_usd"] == 200_000
    assert row["max_transfer_usd"] == 125_000
    assert row["tx_count"] == 2
    assert row["first_seen"] == datetime(2026, 4, 20, tzinfo=timezone.utc)
    assert "Project Treasury" in row["source_entities"]
    assert "Market Maker" in row["source_entities"]


def test_prelisting_skips_exchange_or_pool_destinations(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "MIN_TRANSFER_USD", 50_000)

    candidates = scan.aggregate_accumulation([
        {
            "fromAddress": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            "toAddress": {
                "address": "0x1111111111111111111111111111111111111111",
                "arkhamEntity": {"name": "Binance", "type": "cex"},
            },
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            "toAddress": {
                "address": "0x2222222222222222222222222222222222222222",
                "arkhamLabel": {"name": "V3 Pool"},
            },
            "historicalUSD": 1_000_000,
        },
    ])

    assert candidates == {}


def test_prelisting_skips_infra_sources_by_default(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "MIN_TRANSFER_USD", 50_000)
    monkeypatch.setattr(scan, "SKIP_INFRA_SOURCES", True)
    monkeypatch.setattr(scan, "SKIP_DISTRIBUTION_SOURCES", True)

    candidates = scan.aggregate_accumulation([
        {
            "fromAddress": {
                "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "arkhamEntity": {"name": "Wintermute", "type": "fund"},
            },
            "toAddress": {"address": "0x1111111111111111111111111111111111111111"},
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {
                "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "arkhamEntity": {"name": "KuCoin", "type": "cex"},
            },
            "toAddress": {"address": "0x2222222222222222222222222222222222222222"},
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {
                "address": "0xcccccccccccccccccccccccccccccccccccccccc",
                "arkhamEntity": {"name": "Uniswap", "type": "dex"},
            },
            "toAddress": {"address": "0x3333333333333333333333333333333333333333"},
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {
                "address": "0xdddddddddddddddddddddddddddddddddddddddd",
                "arkhamEntity": {"name": "EdgeDistributor (Proxy)"},
            },
            "toAddress": {"address": "0x4444444444444444444444444444444444444444"},
            "historicalUSD": 1_000_000,
        },
    ])

    assert candidates == {}


def test_prelisting_can_keep_distribution_sources_when_requested(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "MIN_TRANSFER_USD", 50_000)
    monkeypatch.setattr(scan, "SKIP_INFRA_SOURCES", True)
    monkeypatch.setattr(scan, "SKIP_DISTRIBUTION_SOURCES", False)

    candidates = scan.aggregate_accumulation([{
        "fromAddress": {
            "address": "0xdddddddddddddddddddddddddddddddddddddddd",
            "arkhamEntity": {"name": "EdgeDistributor (Proxy)"},
        },
        "toAddress": {"address": "0x4444444444444444444444444444444444444444"},
        "historicalUSD": 1_000_000,
    }])

    assert "0x4444444444444444444444444444444444444444" in candidates


def test_prelisting_skips_null_or_burn_routes(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "MIN_TRANSFER_USD", 50_000)

    candidates = scan.aggregate_accumulation([
        {
            "fromAddress": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            "toAddress": {"address": "0x0000000000000000000000000000000000000000"},
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {
                "address": "0x0000000000000000000000000000000000000000",
                "arkhamEntity": {"name": "Null Address"},
            },
            "toAddress": {"address": "0x2222222222222222222222222222222222222222"},
            "historicalUSD": 1_000_000,
        },
        {
            "fromAddress": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            "toAddress": {"address": "0x000000000000000000000000000000000000dead"},
            "historicalUSD": 1_000_000,
        },
    ])

    assert candidates == {}


def test_prelisting_balance_ignores_raw_token_amount_fields():
    scan = _load_prelisting()

    payload = {
        "balance": 10**27,
        "tokenBalance": 10**24,
        "totalBalanceUsd": 250_000,
        "chains": {"ethereum": {"balance": 10**18, "usd": 125_000}},
    }

    assert scan._balance_usd(payload) == 250_000


def test_prelisting_scores_accumulation_that_did_not_exit(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "LISTING_TS", "2026-05-22T07:00:00Z")
    candidate = {
        "total_in_usd": 1_200_000,
        "max_transfer_usd": 600_000,
        "tx_count": 4,
        "first_seen": datetime(2026, 4, 20, tzinfo=timezone.utc),
        "pre_listing_out_usd": 0,
        "post_listing_out_usd": 0,
        "source_entities": {"Project Treasury"},
        "labels": set(),
    }

    assert scan.score_candidate(candidate) >= 90


def test_prelisting_score_penalizes_pre_listing_exit(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "LISTING_TS", "2026-05-22T07:00:00Z")
    base = {
        "total_in_usd": 600_000,
        "max_transfer_usd": 300_000,
        "tx_count": 2,
        "first_seen": datetime(2026, 5, 20, tzinfo=timezone.utc),
        "post_listing_out_usd": 0,
        "source_entities": set(),
        "labels": set(),
    }

    held = dict(base, pre_listing_out_usd=0)
    exited = dict(base, pre_listing_out_usd=500_000)

    assert scan.score_candidate(held) > scan.score_candidate(exited)
    assert scan.score_candidate(exited) <= 35


def test_prelisting_classifies_distribution_routes():
    scan = _load_prelisting()

    assert scan.classify_candidate({
        "source_entities": {"EdgeDistributor (Proxy)", "Gnosis Safe Proxy"},
        "labels": set(),
    }) == "distribution_route"


def test_prelisting_supabase_row_is_serializable(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "TOKEN_SYMBOL", "AIGENSYN")
    monkeypatch.setattr(scan, "TOKEN_DISPLAY", "AIGENSYN")
    monkeypatch.setattr(scan, "TOKEN_ID", "aigensyn")

    row = scan.row_for_supabase({
        "address": "0x1111111111111111111111111111111111111111",
        "chains": {"ethereum"},
        "first_seen": datetime(2026, 4, 20, tzinfo=timezone.utc),
        "last_seen": datetime(2026, 4, 21, tzinfo=timezone.utc),
        "total_in_usd": 200_000,
        "max_transfer_usd": 125_000,
        "pre_listing_out_usd": 0,
        "post_listing_out_usd": 50_000,
        "balance_usd": 100_000,
        "tx_count": 2,
        "score": 70,
        "classification": "project_source",
        "source_entities": {"Project Treasury"},
        "labels": set(),
        "sample_txs": [{"hash": "0xabc"}],
    })

    assert row["token"] == "AIGENSYN"
    assert row["chains"] == ["ethereum"]
    assert row["first_seen"] == "2026-04-20T00:00:00Z"
    assert row["source_entities"] == ["Project Treasury"]
    assert row["raw"]["sample_txs"] == [{"hash": "0xabc"}]


def test_prelisting_resolves_token_filters_with_addresses(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "TOKEN_FILTER", [])
    monkeypatch.setattr(scan, "TOKEN_ID", "gensyn")
    monkeypatch.setattr(scan, "TOKEN_SYMBOL", "AI")
    monkeypatch.setattr(scan, "TOKEN_DISPLAY", "AIGENSYN")
    monkeypatch.setattr(scan, "_RESOLVED_TOKEN_FILTERS", None)
    monkeypatch.setattr(scan, "fetch_token_addresses", lambda: ["0x1111111111111111111111111111111111111111"])

    assert scan.resolve_token_filters() == [
        "gensyn",
        "AI",
        "AIGENSYN",
        "0x1111111111111111111111111111111111111111",
    ]


def test_prelisting_extracts_matching_search_token_filters(monkeypatch):
    scan = _load_prelisting()
    monkeypatch.setattr(scan, "TOKEN_SYMBOL", "MEGA")
    monkeypatch.setattr(scan, "TOKEN_DISPLAY", "MEGA")
    monkeypatch.setattr(scan, "TOKEN_ID", "megaeth")

    payload = {
        "tokens": [
            {"symbol": "MEGA", "id": "megaeth", "address": "0x1111111111111111111111111111111111111111"},
            {"symbol": "MEGA2", "id": "wrong", "address": "0x2222222222222222222222222222222222222222"},
            {"symbol": "ABC", "name": "MegaETH", "contractAddress": "0x3333333333333333333333333333333333333333"},
        ]
    }

    assert scan._extract_search_token_filters(payload) == [
        "megaeth",
        "0x1111111111111111111111111111111111111111",
        "0x3333333333333333333333333333333333333333",
    ]
