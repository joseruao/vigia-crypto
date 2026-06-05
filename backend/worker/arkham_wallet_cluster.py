"""
Arkham wallet clustering prototype.

Standalone local run:
    python backend/worker/arkham_wallet_cluster.py

Goal:
    Discover unlabeled wallets that may belong to a known entity by following
    outgoing transfers from labeled entity addresses.

This first version is intentionally read-only: it prints candidates and does
not write to Supabase yet.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


for _env in (
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
):
    if _env.exists():
        load_dotenv(_env, override=False)
        break


ARKHAM_BASE_URL = "https://api.arkm.com"
ARKHAM_API_KEY = os.getenv("ARKHAM_API_KEY", "").strip()

ENTITY_ID = os.getenv("ARKHAM_CLUSTER_ENTITY", "wintermute").strip() or "wintermute"
MIN_BALANCE_USD = float(os.getenv("ARKHAM_CLUSTER_MIN_BALANCE_USD", "100000"))
MAX_SEED_ADDRESSES = int(os.getenv("ARKHAM_CLUSTER_MAX_SEED_ADDRESSES", "10"))
TRANSFER_LIMIT = int(os.getenv("ARKHAM_CLUSTER_TRANSFER_LIMIT", "50"))
CHECK_EXCHANGE_LINKS = os.getenv("ARKHAM_CLUSTER_CHECK_EXCHANGES", "0").strip().lower() in {"1", "true", "yes"}
DEBUG = os.getenv("ARKHAM_CLUSTER_DEBUG", "0").strip().lower() in {"1", "true", "yes"}

EXCHANGE_NAMES = {
    "binance", "coinbase", "gate.io", "gate", "okx", "bybit", "kraken",
    "bitget", "mexc", "kucoin", "upbit", "crypto.com", "robinhood",
}


def _headers() -> dict[str, str]:
    return {
        "API-Key": ARKHAM_API_KEY,
        "Accept": "application/json",
        "User-Agent": "vigia-crypto-arkham-cluster/0.1",
    }


def _require_env() -> None:
    if not ARKHAM_API_KEY:
        raise RuntimeError("Missing ARKHAM_API_KEY")


def _arkham_get_json(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        f"{ARKHAM_BASE_URL}{endpoint}",
        headers=_headers(),
        params=params or {},
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.text[:400]
        raise requests.HTTPError(f"{response.status_code} {endpoint}: {detail}", response=response)
    if not response.content:
        return {}
    return response.json()


def _walk_values(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def _normalize_address(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("address", "id", "hash"):
            if value.get(key):
                value = value[key]
                break
    text = str(value or "").strip()
    if text.startswith("0x") and len(text) == 42:
        return text.lower()
    return text


def _looks_like_address(value: Any) -> bool:
    text = str(value or "").strip()
    if text.startswith("0x") and len(text) == 42:
        return True
    # Solana/Base58-ish addresses. Keep broad, then Arkham label/balance calls
    # decide if the candidate is useful.
    return 32 <= len(text) <= 64 and " " not in text


def _first_address(*values: Any) -> str:
    for value in values:
        if isinstance(value, dict):
            nested = _first_address(
                value.get("address"),
                value.get("id"),
                value.get("hash"),
                value.get("account"),
            )
            if nested:
                return nested
        elif _looks_like_address(value):
            return _normalize_address(value)
    return ""


def _payload_summary(payload: Any) -> str:
    if isinstance(payload, list):
        keys = sorted(payload[0].keys()) if payload and isinstance(payload[0], dict) else []
        return f"list len={len(payload)} first_keys={keys[:20]}"
    if isinstance(payload, dict):
        parts = [f"dict keys={sorted(payload.keys())[:20]}"]
        for key in ("transfers", "items", "data", "results"):
            if isinstance(payload.get(key), list):
                first = payload[key][0] if payload[key] and isinstance(payload[key][0], dict) else {}
                parts.append(f"{key}.len={len(payload[key])} first_keys={sorted(first.keys())[:20]}")
        return " ".join(parts)
    return type(payload).__name__


def _extract_addresses(payload: Any) -> list[dict[str, str]]:
    """Extract labeled addresses from flexible Arkham entity payloads."""
    seen: set[str] = set()
    addresses: list[dict[str, str]] = []
    address_keys = {"address", "wallet", "account", "id"}
    chain_keys = {"chain", "network", "blockchain"}
    label_keys = {"label", "name", "arkhamLabel"}

    for node in _walk_values(payload):
        address = ""
        chain = ""
        label = ""
        for key, value in node.items():
            key_l = str(key).lower()
            if key_l in address_keys and _looks_like_address(value):
                address = _normalize_address(value)
            elif key_l in chain_keys and value:
                chain = str(value).strip().lower()
            elif key_l in label_keys and value:
                label = str(value).strip()
        if address and address not in seen:
            seen.add(address)
            addresses.append({"address": address, "chain": chain, "label": label})
    return addresses


def _extract_transfer_addresses(payload: Any, source_address: str) -> list[dict[str, str]]:
    """Extract destination addresses from flexible transfer payloads."""
    candidates: list[dict[str, str]] = []
    source = _normalize_address(source_address)
    rows = []

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        for key in ("transfers", "items", "data", "results"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        if not rows:
            rows = [node for node in _walk_values(payload) if isinstance(node, dict)]

    for row in rows:
        if not isinstance(row, dict):
            continue
        from_addr = _first_address(
            row.get("fromAddress")
            or row.get("from_address")
            or row.get("from")
            or row.get("fromArkhamAddress")
            or row.get("fromEntity")
            or row.get("fromArkhamEntity")
        )
        to_addr = _first_address(
            row.get("toAddress")
            or row.get("to_address")
            or row.get("to")
            or row.get("toArkhamAddress")
            or row.get("toEntity")
            or row.get("toArkhamEntity")
        )
        if source and from_addr and from_addr != source:
            continue
        if not to_addr or to_addr == source or not _looks_like_address(to_addr):
            continue
        chain = str(row.get("chain") or row.get("network") or "").strip().lower()
        value = _float(row.get("usdValue") or row.get("valueUsd") or row.get("value") or 0)
        to_obj = row.get("toAddress") if isinstance(row.get("toAddress"), dict) else {}
        to_entity = to_obj.get("arkhamEntity") if isinstance(to_obj.get("arkhamEntity"), dict) else {}
        to_label = to_obj.get("arkhamLabel") if isinstance(to_obj.get("arkhamLabel"), dict) else {}
        candidates.append({
            "address": to_addr,
            "chain": chain or str(to_obj.get("chain") or "").strip().lower(),
            "found_via": source,
            "transfer_value_usd": str(value or _float(row.get("historicalUSD"))),
            "to_entity": str(to_entity.get("name") or "").strip(),
            "to_entity_type": str(to_entity.get("type") or "").strip(),
            "to_label": str(to_label.get("name") or "").strip(),
            "to_is_contract": str(bool(row.get("toIsContract") or to_obj.get("contract"))),
            "token_symbol": str(row.get("tokenSymbol") or "").strip(),
        })
    return candidates


def _float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").strip()
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _extract_entity_name(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    entity = payload.get("entity") if isinstance(payload.get("entity"), dict) else payload
    for key in ("name", "label", "arkhamLabel", "slug"):
        if entity.get(key):
            return str(entity[key]).strip()
    return ""


def _is_exchange_label(label: str) -> bool:
    normalized = label.strip().lower()
    return any(name in normalized for name in EXCHANGE_NAMES)


def _balance_usd(payload: Any) -> float:
    best = 0.0
    for node in _walk_values(payload):
        for key, value in node.items():
            if str(key).lower() in {
                "totalbalance", "totalbalanceusd", "balanceusd", "usd", "valueusd",
                "marketvalueusd", "portfolio", "totalvalueusd",
            }:
                best = max(best, _float(value))
    return best


def fetch_entity_addresses(entity_id: str) -> list[dict[str, str]]:
    payload = _arkham_get_json(f"/intelligence/entity/{entity_id}")
    addresses = _extract_addresses(payload)
    if not addresses:
        print("Entity payload debug:", json.dumps(payload, ensure_ascii=False)[:800], flush=True)
    return addresses


def fetch_outgoing_transfers(address: str) -> list[dict[str, str]]:
    payload = _arkham_get_json("/transfers", params={"base": address, "flow": "out", "limit": TRANSFER_LIMIT})
    transfers = _extract_transfer_addresses(payload, address)
    if DEBUG:
        print(f"Transfer payload debug for {address[:18]}: {_payload_summary(payload)} parsed={len(transfers)}", flush=True)
        print(json.dumps(payload, ensure_ascii=False)[:1200], flush=True)
    return transfers


def fetch_entity_outgoing_transfers(entity_id: str) -> list[dict[str, str]]:
    payload = _arkham_get_json("/transfers", params={"base": entity_id, "flow": "out", "limit": TRANSFER_LIMIT})
    transfers = _extract_transfer_addresses(payload, "")
    if DEBUG:
        print(f"Transfer payload debug for entity {entity_id}: {_payload_summary(payload)} parsed={len(transfers)}", flush=True)
        print(json.dumps(payload, ensure_ascii=False)[:1200], flush=True)
    return transfers


def fetch_address_label(address: str) -> str:
    try:
        payload = _arkham_get_json(f"/intelligence/address/{address}")
    except Exception:
        return ""
    return _extract_entity_name(payload)


def fetch_address_balance(address: str) -> float:
    payload = _arkham_get_json(f"/balances/address/{address}")
    return _balance_usd(payload)


def address_has_exchange_link(address: str) -> bool:
    """Optional expensive check: does this wallet send to a labeled exchange?"""
    try:
        transfers = fetch_outgoing_transfers(address)
    except Exception:
        return False
    for transfer in transfers:
        label = fetch_address_label(transfer["address"])
        time.sleep(0.25)
        if label and _is_exchange_label(label):
            return True
    return False


def score_candidate(candidate: dict[str, Any]) -> int:
    score = 0
    entity_sources = int(candidate.get("entity_source_count") or 0)
    if entity_sources >= 1:
        score += 35
    if entity_sources >= 2:
        score += 25
    if candidate.get("exchange_connected"):
        score += 20
    balance = _float(candidate.get("balance_usd"))
    if balance >= 1_000_000:
        score += 20
    elif balance >= 250_000:
        score += 10
    return min(score, 100)


def cluster_entity(entity_id: str = ENTITY_ID) -> list[dict[str, Any]]:
    _require_env()
    print(f"ARKHAM WALLET CLUSTER - entity={entity_id}", flush=True)

    labeled = fetch_entity_addresses(entity_id)
    seed_addresses = labeled[:MAX_SEED_ADDRESSES]
    known_addresses = {row["address"] for row in labeled}
    print(f"Found {len(labeled)} labeled addresses; scanning {len(seed_addresses)} seeds", flush=True)

    candidate_sources: dict[str, set[str]] = defaultdict(set)
    candidate_chains: dict[str, set[str]] = defaultdict(set)
    filtered_destinations: list[dict[str, str]] = []

    if seed_addresses:
        scan_targets = [(row["address"], row["address"]) for row in seed_addresses]
    else:
        scan_targets = [(entity_id, entity_id)]
        print("No labeled addresses in entity payload; falling back to entity-level transfers.", flush=True)

    for index, (target, source_label) in enumerate(scan_targets, 1):
        print(f"[{index}/{len(scan_targets)}] transfers out from {target[:18]}...", flush=True)
        try:
            transfers = (
                fetch_outgoing_transfers(target)
                if target in known_addresses
                else fetch_entity_outgoing_transfers(target)
            )
        except Exception as exc:
            print(f"  transfer fetch failed: {exc}", flush=True)
            transfers = []

        for transfer in transfers:
            candidate = transfer["address"]
            if candidate in known_addresses:
                continue
            filtered_destinations.append(transfer)
            candidate_sources[candidate].add(source_label)
            if transfer.get("chain"):
                candidate_chains[candidate].add(transfer["chain"])

        time.sleep(1.05)

    results: list[dict[str, Any]] = []
    for address, sources in sorted(candidate_sources.items(), key=lambda item: len(item[1]), reverse=True):
        label = fetch_address_label(address)
        time.sleep(0.25)
        if label:
            # This prototype is looking for unlabeled satellite wallets. A
            # labeled address, even an exchange hot wallet, is context rather
            # than a candidate cluster wallet.
            continue

        try:
            balance = fetch_address_balance(address)
        except Exception as exc:
            print(f"  balance fetch failed for {address[:10]}...: {exc}", flush=True)
            balance = 0
        time.sleep(0.25)

        if balance < MIN_BALANCE_USD:
            continue

        candidate = {
            "address": address,
            "entity": entity_id,
            "score": 0,
            "balance_usd": balance,
            "chains": sorted(candidate_chains.get(address) or []),
            "found_via": sorted(sources),
            "entity_source_count": len(sources),
            "label": label,
            "exchange_connected": address_has_exchange_link(address) if CHECK_EXCHANGE_LINKS else False,
        }
        candidate["score"] = score_candidate(candidate)
        results.append(candidate)

    results.sort(key=lambda row: (row["score"], row["balance_usd"], row["entity_source_count"]), reverse=True)
    if DEBUG and not results and filtered_destinations:
        print("\nNo unlabeled balance candidates. Top transfer destinations seen:", flush=True)
        for row in filtered_destinations[:10]:
            meta = row.get("to_entity") or row.get("to_label") or "unlabeled/unknown"
            kind = row.get("to_entity_type") or ("contract" if row.get("to_is_contract") == "True" else "wallet")
            print(
                f"- {row['address']} | {meta} | {kind} | {row.get('chain') or 'unknown'} | "
                f"{row.get('token_symbol') or 'token'} | transfer=${_float(row.get('transfer_value_usd')):,.0f}",
                flush=True,
            )
    return results


def main() -> None:
    results = cluster_entity(ENTITY_ID)
    print(f"\nCandidate wallets: {len(results)}", flush=True)
    for row in results[:25]:
        chains = ",".join(row["chains"]) or "unknown"
        print(
            f"- {row['address']} | score={row['score']} | balance=${row['balance_usd']:,.0f} | "
            f"sources={row['entity_source_count']} | chains={chains} | label={row.get('label') or 'unlabeled'}",
            flush=True,
        )


if __name__ == "__main__":
    main()
