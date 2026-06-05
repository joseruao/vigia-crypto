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
        "to_entity": "",
        "to_predicted_entity": "",
        "to_predicted_type": "",
        "to_entity_type": "",
        "to_label": "",
        "to_is_contract": "False",
        "token_symbol": "",
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


def test_cluster_parses_manual_seed_addresses():
    cluster = _load_cluster()

    seeds = cluster._parse_seed_addresses(
        "0x1111111111111111111111111111111111111111|ethereum|known side wallet;"
        "bad;0x2222222222222222222222222222222222222222|base"
    )

    assert seeds == [
        {
            "address": "0x1111111111111111111111111111111111111111",
            "chain": "ethereum",
            "label": "known side wallet",
        },
        {
            "address": "0x2222222222222222222222222222222222222222",
            "chain": "base",
            "label": "manual seed",
        },
    ]


def test_cluster_entities_from_env_preserves_single_entity(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "ENTITY_ID", "wintermute")

    assert cluster._cluster_entities_from_env("") == ["wintermute"]


def test_cluster_entities_from_env_supports_all_and_lists():
    cluster = _load_cluster()

    assert "multicoin-capital" in cluster._cluster_entities_from_env("all")
    assert cluster._cluster_entities_from_env("wintermute, multicoin-capital;wintermute") == [
        "wintermute",
        "multicoin-capital",
    ]


def test_cluster_identifies_pool_or_service_transfers():
    cluster = _load_cluster()

    assert cluster._is_pool_or_service_transfer({"to_entity_type": "dex"})
    assert cluster._is_pool_or_service_transfer({"to_label": "V3 Pool"})
    assert cluster._is_pool_or_service_transfer({"to_entity": "PancakeSwap"})
    assert not cluster._is_pool_or_service_transfer({"to_entity": "", "to_label": ""})


def test_cluster_candidate_notes_explain_routes():
    cluster = _load_cluster()

    notes = cluster._candidate_notes(
        "0xabc",
        {"multicoin-capital -> Anchorage Digital Custody -> 0xabc"},
        {"to_predicted_entity": "GSR Markets", "token_symbol": "USDC"},
    )

    assert "custody counterparty seen" in notes
    assert "market-maker route seen" in notes


def test_cluster_classifies_candidates_from_notes_and_paths():
    cluster = _load_cluster()

    assert cluster.classify_candidate({"notes": ["custody counterparty seen"], "paths": []}) == "custody_cluster"
    assert cluster.classify_candidate({"notes": ["market-maker route seen"], "paths": []}) == "market_maker_route"
    assert cluster.classify_candidate({"notes": ["exchange route seen"], "paths": []}) == "exchange_route"
    assert cluster.classify_candidate({"notes": [], "paths": ["multicoin -> GSR Markets -> wallet"]}) == "market_maker_route"
    assert cluster.classify_candidate({"notes": [], "paths": []}) == "unknown"


def test_cluster_save_candidate_wallet_posts_to_supabase(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "SAVE_TO_SUPABASE", True)
    monkeypatch.setattr(cluster, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(cluster, "SUPABASE_KEY", "service-role")
    calls = []

    class Response:
        status_code = 204
        text = ""

    def fake_post(url, headers=None, params=None, data=None, timeout=None):
        calls.append((url, headers, params, data, timeout))
        return Response()

    monkeypatch.setattr(cluster.requests, "post", fake_post)

    ok = cluster.save_candidate_wallet({
        "entity": "multicoin-capital",
        "address": "0xabc",
        "chains": ["ethereum"],
        "score": 65,
        "balance_usd": 1_000_000,
        "notes": ["custody counterparty seen"],
        "paths": ["multicoin -> custody -> 0xabc"],
    })

    assert ok is True
    assert calls[0][0] == "https://example.supabase.co/rest/v1/candidate_wallets"
    assert calls[0][2] == {"on_conflict": "entity,address"}
    assert '"classification": "custody_cluster"' in calls[0][3]


def test_cluster_skips_predicted_entity_candidates(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "ARKHAM_API_KEY", "arkham")
    monkeypatch.setattr(cluster, "fetch_entity_addresses", lambda entity: [])
    monkeypatch.setattr(cluster, "fetch_entity_outgoing_transfers", lambda entity: [{
        "address": "0xfb19085ac3951cb0af7b5a6126f4bff8e2d1f8ee",
        "chain": "ethereum",
        "found_via": entity,
        "transfer_value_usd": "100000",
        "to_predicted_entity": "GSR Markets",
        "to_predicted_type": "fund",
        "to_entity": "",
        "to_label": "",
    }])
    monkeypatch.setattr(cluster, "fetch_address_label", lambda address: "")
    monkeypatch.setattr(cluster, "fetch_address_balance", lambda address: 5_000_000)
    monkeypatch.setattr(cluster.time, "sleep", lambda _: None)

    assert cluster.cluster_entity("multicoin-capital") == []


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


def test_cluster_boosts_shared_intermediary_fanout(monkeypatch):
    cluster = _load_cluster()
    monkeypatch.setattr(cluster, "ARKHAM_API_KEY", "arkham")
    monkeypatch.setattr(cluster, "fetch_entity_addresses", lambda entity: [])

    first_hop = "0x1111111111111111111111111111111111111111"
    wallets = [
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
        "0x5555555555555555555555555555555555555555",
    ]

    def fake_entity_transfers(entity):
        return [{
            "address": first_hop,
            "chain": "ethereum",
            "found_via": entity,
            "transfer_value_usd": "100000",
        }]

    def fake_outgoing(address):
        assert address == first_hop
        return [{
            "address": wallet,
            "chain": "ethereum",
            "found_via": first_hop,
            "transfer_value_usd": "100000",
        } for wallet in wallets]

    monkeypatch.setattr(cluster, "fetch_entity_outgoing_transfers", fake_entity_transfers)
    monkeypatch.setattr(cluster, "fetch_outgoing_transfers", fake_outgoing)
    monkeypatch.setattr(cluster, "fetch_address_label", lambda address: "")
    monkeypatch.setattr(cluster, "fetch_address_balance", lambda address: 500_000)
    monkeypatch.setattr(cluster.time, "sleep", lambda _: None)
    monkeypatch.setattr(cluster, "MAX_DEPTH", 2)

    results = cluster.cluster_entity("multicoin-capital")

    assert len(results) == 3
    assert all("fan-out from same intermediary (3 candidates)" in row["notes"] for row in results)
    assert all(row["score"] == 55 for row in results)
