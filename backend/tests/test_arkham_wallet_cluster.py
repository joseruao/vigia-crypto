import importlib.util
from pathlib import Path


def _load_cluster():
    path = Path(__file__).resolve().parents[1] / "worker" / "arkham_wallet_cluster.py"
    spec = importlib.util.spec_from_file_location("arkham_wallet_cluster", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cluster_extracts_entity_addresses_from_nested_payload():
    cluster = _load_cluster()
    payload = {
        "entity": {"name": "Wintermute"},
        "addresses": [
            {"address": "0x1111111111111111111111111111111111111111", "chain": "ethereum", "label": "Wintermute 1"},
            {"wallet": "0x2222222222222222222222222222222222222222", "network": "base"},
        ],
    }

    addresses = cluster._extract_addresses(payload)

    assert addresses == [
        {
            "address": "0x1111111111111111111111111111111111111111",
            "chain": "ethereum",
            "label": "Wintermute 1",
        },
        {
            "address": "0x2222222222222222222222222222222222222222",
            "chain": "base",
            "label": "",
        },
    ]


def test_cluster_extracts_outgoing_transfer_destinations():
    cluster = _load_cluster()
    source = "0x1111111111111111111111111111111111111111"
    payload = {
        "transfers": [
            {
                "fromAddress": source,
                "toAddress": "0x3333333333333333333333333333333333333333",
                "chain": "ethereum",
                "usdValue": "125000",
            },
            {
                "fromAddress": "0x9999999999999999999999999999999999999999",
                "toAddress": "0x4444444444444444444444444444444444444444",
            },
        ]
    }

    transfers = cluster._extract_transfer_addresses(payload, source)

    assert transfers == [{
        "address": "0x3333333333333333333333333333333333333333",
        "chain": "ethereum",
        "found_via": source,
        "transfer_value_usd": "125000.0",
    }]


def test_cluster_extracts_nested_transfer_address_objects():
    cluster = _load_cluster()
    source = "0x1111111111111111111111111111111111111111"
    payload = {
        "transfers": [
            {
                "fromAddress": {"address": source},
                "toAddress": {"address": "0x3333333333333333333333333333333333333333"},
                "network": "base",
                "valueUsd": 250000,
            }
        ]
    }

    transfers = cluster._extract_transfer_addresses(payload, source)

    assert transfers[0]["address"] == "0x3333333333333333333333333333333333333333"
    assert transfers[0]["chain"] == "base"
    assert transfers[0]["transfer_value_usd"] == "250000.0"


def test_cluster_scores_repeated_entity_connections_and_balance():
    cluster = _load_cluster()

    assert cluster.score_candidate({
        "entity_source_count": 1,
        "balance_usd": 150_000,
        "exchange_connected": False,
    }) == 35
    assert cluster.score_candidate({
        "entity_source_count": 2,
        "balance_usd": 1_500_000,
        "exchange_connected": True,
    }) == 100


def test_cluster_balance_uses_largest_usd_field():
    cluster = _load_cluster()
    payload = {
        "totalBalance": 120_000,
        "chains": {
            "ethereum": {"totalBalanceUsd": 300_000},
            "base": {"usd": 50_000},
        },
    }

    assert cluster._balance_usd(payload) == 300_000


def test_cluster_skips_labeled_candidate_wallets(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "ARKHAM_API_KEY", "arkham")
    monkeypatch.setattr(cluster, "fetch_entity_addresses", lambda entity: [{
        "address": "0x1111111111111111111111111111111111111111",
        "chain": "ethereum",
        "label": "Wintermute 1",
    }])
    monkeypatch.setattr(cluster, "fetch_outgoing_transfers", lambda address: [{
        "address": "0x3333333333333333333333333333333333333333",
        "chain": "ethereum",
        "found_via": address,
        "transfer_value_usd": "100000",
    }])
    monkeypatch.setattr(cluster, "fetch_address_label", lambda address: "Some Known Fund")
    monkeypatch.setattr(cluster, "fetch_address_balance", lambda address: 500_000)
    monkeypatch.setattr(cluster.time, "sleep", lambda _: None)

    assert cluster.cluster_entity("wintermute") == []


def test_cluster_falls_back_to_entity_level_transfers(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "ARKHAM_API_KEY", "arkham")
    monkeypatch.setattr(cluster, "fetch_entity_addresses", lambda entity: [])
    monkeypatch.setattr(cluster, "fetch_entity_outgoing_transfers", lambda entity: [{
        "address": "0x3333333333333333333333333333333333333333",
        "chain": "ethereum",
        "found_via": entity,
        "transfer_value_usd": "100000",
    }])
    monkeypatch.setattr(cluster, "fetch_address_label", lambda address: "")
    monkeypatch.setattr(cluster, "fetch_address_balance", lambda address: 500_000)
    monkeypatch.setattr(cluster.time, "sleep", lambda _: None)

    results = cluster.cluster_entity("wintermute")

    assert len(results) == 1
    assert results[0]["address"] == "0x3333333333333333333333333333333333333333"
    assert results[0]["found_via"] == ["wintermute"]
    assert results[0]["score"] == 45
