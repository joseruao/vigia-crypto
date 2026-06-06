"""
Arkham pre-listing token study.

Objectivo:
    Encontrar wallets que receberam/compraram forte ANTES de um listing ou
    evento relevante, nao sairam antes do listing, e depois podem ter vendido,
    movido para outra wallet, ou depositado numa exchange.

Metodo mental:
    1. Escolher token + janela antes do listing.
    2. Buscar grandes transferencias do token nessa janela.
    3. Remover ruido: exchanges, DEX/pools, market makers, distributors,
       airdrops, presales, claims e burn/null addresses.
    4. Para as melhores wallets, verificar:
       - in: valor recebido antes do listing;
       - pre-out: valor que saiu antes do listing;
       - post-out: valor que saiu depois do listing;
       - post-listing destinations: para onde saiu depois.
    5. So investigar a fundo unknown_accumulation com in alto e pre-out baixo.

Dry-run recomendado antes de gravar:
    $env:ARKHAM_PRELISTING_SAVE="0"
    $env:ARKHAM_PRELISTING_FILTER_DISTRIBUTION_ROUTES="1"
    $env:ARKHAM_PRELISTING_FILTER_EXITED="1"
    $env:ARKHAM_PRELISTING_TRACE_POST="1"
    python backend/worker/arkham_token_prelisting_scan.py

Guardar no Supabase so depois do output parecer limpo:
    $env:SUPABASE_URL="https://qynnajpvxnqcmkzrhpde.supabase.co"
    $env:SUPABASE_SERVICE_ROLE="SERVICE_ROLE_KEY"
    $env:ARKHAM_PRELISTING_SAVE="1"
    python backend/worker/arkham_token_prelisting_scan.py

Exemplo SPX:
    $env:ARKHAM_PRELISTING_TOKEN_SYMBOL="SPX"
    $env:ARKHAM_PRELISTING_TOKEN_DISPLAY="SPX"
    $env:ARKHAM_PRELISTING_TOKEN_ID="spx6900"
    $env:ARKHAM_PRELISTING_START="2024-06-01T00:00:00Z"
    $env:ARKHAM_PRELISTING_END="2025-01-01T00:00:00Z"
    $env:ARKHAM_PRELISTING_LISTING_TS="2025-01-01T00:00:00Z"

Nota:
    Este script e standalone e com SAVE=0 nao grava nada. Mantem o custo
    controlado porque so enriquece os top candidatos depois do primeiro filtro.
"""
from __future__ import annotations

import base64
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
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
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

TOKEN_SYMBOL = os.getenv("ARKHAM_PRELISTING_TOKEN_SYMBOL", "AI").strip().upper()
TOKEN_DISPLAY = os.getenv("ARKHAM_PRELISTING_TOKEN_DISPLAY", "AIGENSYN").strip().upper()
TOKEN_ID = os.getenv("ARKHAM_PRELISTING_TOKEN_ID", "gensyn").strip()
TOKEN_FILTER = [
    part.strip()
    for part in os.getenv("ARKHAM_PRELISTING_TOKEN_FILTER", "").replace(";", ",").split(",")
    if part.strip()
]
LISTING_EXCHANGE = os.getenv("ARKHAM_PRELISTING_EXCHANGE", "OKX").strip()
WINDOW_START = os.getenv("ARKHAM_PRELISTING_START", "2026-04-15T00:00:00Z").strip()
WINDOW_END = os.getenv("ARKHAM_PRELISTING_END", "2026-05-22T07:00:00Z").strip()
LISTING_TS = os.getenv("ARKHAM_PRELISTING_LISTING_TS", WINDOW_END).strip()

MIN_TRANSFER_USD = float(os.getenv("ARKHAM_PRELISTING_MIN_USD", "50000"))
TRANSFER_LIMIT = int(os.getenv("ARKHAM_PRELISTING_TRANSFER_LIMIT", "100"))
MAX_OFFSETS = int(os.getenv("ARKHAM_PRELISTING_MAX_OFFSETS", "1"))
ENRICH_LIMIT = int(os.getenv("ARKHAM_PRELISTING_ENRICH_LIMIT", "20"))
SELL_CHECK_LIMIT = int(os.getenv("ARKHAM_PRELISTING_SELL_CHECK_LIMIT", "10"))
SELL_CHECK_MIN_USD = float(os.getenv("ARKHAM_PRELISTING_SELL_MIN_USD", "25000"))
MAX_PRELISTING_OUT_RATIO = float(os.getenv("ARKHAM_PRELISTING_MAX_PRE_OUT_RATIO", "0.5"))
FILTER_EXITED_BEFORE_LISTING = os.getenv("ARKHAM_PRELISTING_FILTER_EXITED", "1").strip().lower() in {"1", "true", "yes"}
FILTER_DISTRIBUTION_ROUTES = os.getenv("ARKHAM_PRELISTING_FILTER_DISTRIBUTION_ROUTES", "1").strip().lower() in {"1", "true", "yes"}
TRACE_POST_DESTINATIONS = os.getenv("ARKHAM_PRELISTING_TRACE_POST", "1").strip().lower() in {"1", "true", "yes"}
TRACE_DESTINATION_LIMIT = int(os.getenv("ARKHAM_PRELISTING_TRACE_DEST_LIMIT", "3"))
SAVE_TO_SUPABASE = os.getenv("ARKHAM_PRELISTING_SAVE", "0").strip().lower() in {"1", "true", "yes"}
SUPABASE_TABLE = os.getenv("ARKHAM_PRELISTING_TABLE", "token_prelisting_wallets")
REQUEST_TIMEOUT = int(os.getenv("ARKHAM_PRELISTING_TIMEOUT", "45"))
TOKEN_ADDRESS_LOOKUP = os.getenv("ARKHAM_PRELISTING_LOOKUP_ADDRESSES", "1").strip().lower() in {"1", "true", "yes"}
TOKEN_SEARCH_LOOKUP = os.getenv("ARKHAM_PRELISTING_SEARCH_TOKEN", "1").strip().lower() in {"1", "true", "yes"}
SKIP_INFRA_SOURCES = os.getenv("ARKHAM_PRELISTING_SKIP_INFRA_SOURCES", "1").strip().lower() in {"1", "true", "yes"}
SKIP_DISTRIBUTION_SOURCES = os.getenv("ARKHAM_PRELISTING_SKIP_DISTRIBUTION_SOURCES", "1").strip().lower() in {"1", "true", "yes"}

EXCHANGE_OR_POOL_TYPES = {"cex", "dex", "bridge", "service", "pool"}
EXCHANGE_OR_POOL_WORDS = {
    "binance", "coinbase", "okx", "bybit", "gate", "gate.io", "kraken", "bitget",
    "mexc", "kucoin", "upbit", "htx", "crypto.com", "uniswap", "pancakeswap",
    "raydium", "aerodrome", "curve", "balancer", "pool", "bridge",
}
MARKET_MAKER_WORDS = {
    "wintermute", "gsr", "jump", "cumberland", "flowdesk", "flow desk",
    "flow traders", "market maker", "amber", "keyrock", "b2c2", "falconx",
}
INFRA_SOURCE_WORDS = EXCHANGE_OR_POOL_WORDS | MARKET_MAKER_WORDS
DISTRIBUTION_SOURCE_WORDS = {
    "distributor", "airdrop", "claim", "gnosis safe", "proxy", "presale",
    "pre-sale", "sale", "vesting", "token distributor",
}
ZERO_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
    "11111111111111111111111111111111",
}


def _headers() -> dict[str, str]:
    return {
        "API-Key": ARKHAM_API_KEY,
        "Accept": "application/json",
        "User-Agent": "vigia-crypto-arkham-prelisting/0.1",
    }


def _supabase_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _jwt_role(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return str(data.get("role") or "").strip()
    except Exception:
        return ""


def _require_env() -> None:
    if not ARKHAM_API_KEY:
        raise RuntimeError("Missing ARKHAM_API_KEY")
    if SAVE_TO_SUPABASE and (not SUPABASE_URL or not SUPABASE_KEY):
        raise RuntimeError("ARKHAM_PRELISTING_SAVE=1 needs SUPABASE_URL and SUPABASE_SERVICE_ROLE")
    if SAVE_TO_SUPABASE and _jwt_role(SUPABASE_KEY) != "service_role":
        raise RuntimeError(
            "ARKHAM_PRELISTING_SAVE=1 needs a Supabase service_role key. "
            f"Detected jwt_role={_jwt_role(SUPABASE_KEY) or 'unknown'}."
        )


def _arkham_get_json(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        f"{ARKHAM_BASE_URL}{endpoint}",
        headers=_headers(),
        params=params or {},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code >= 400:
        raise requests.HTTPError(f"{response.status_code} {endpoint}: {response.text[:400]}", response=response)
    if not response.content:
        return {}
    return response.json()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _dt_text(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _address_obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {"address": value}


def _entity_name(value: dict[str, Any]) -> str:
    entity = value.get("arkhamEntity") if isinstance(value.get("arkhamEntity"), dict) else {}
    predicted = value.get("predictedEntity") if isinstance(value.get("predictedEntity"), dict) else {}
    label = value.get("arkhamLabel") if isinstance(value.get("arkhamLabel"), dict) else {}
    return str(
        entity.get("name")
        or predicted.get("name")
        or label.get("name")
        or value.get("label")
        or ""
    ).strip()


def _entity_type(value: dict[str, Any]) -> str:
    entity = value.get("arkhamEntity") if isinstance(value.get("arkhamEntity"), dict) else {}
    predicted = value.get("predictedEntity") if isinstance(value.get("predictedEntity"), dict) else {}
    return str(entity.get("type") or predicted.get("type") or "").strip().lower()


def _is_service_destination(value: dict[str, Any]) -> bool:
    name = _entity_name(value).lower()
    entity_type = _entity_type(value)
    if entity_type in EXCHANGE_OR_POOL_TYPES:
        return True
    return any(word in name for word in EXCHANGE_OR_POOL_WORDS)


def _is_infra_source(value: dict[str, Any]) -> bool:
    name = _entity_name(value).lower()
    entity_type = _entity_type(value)
    if entity_type in EXCHANGE_OR_POOL_TYPES:
        return True
    return any(word in name for word in INFRA_SOURCE_WORDS)


def _is_distribution_source(value: dict[str, Any]) -> bool:
    name = _entity_name(value).lower()
    return any(word in name for word in DISTRIBUTION_SOURCE_WORDS)


def _is_null_or_burn_address(address: str, obj: dict[str, Any] | None = None) -> bool:
    normalized = _normalize_address(address)
    if normalized in ZERO_ADDRESSES:
        return True
    name = _entity_name(obj or {}).lower()
    return "null address" in name or "burn" in name


def _extract_transfer_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("transfers", "data", "items", "results"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def transfer_usd(row: dict[str, Any]) -> float:
    return max(
        _to_float(row.get("historicalUSD")),
        _to_float(row.get("usdValue")),
        _to_float(row.get("valueUsd")),
        _to_float(row.get("value_usd")),
        _to_float(row.get("usd")),
    )


def transfer_time(row: dict[str, Any]) -> datetime | None:
    return _parse_dt(
        row.get("blockTimestamp")
        or row.get("timestamp")
        or row.get("time")
        or row.get("date")
    )


def transfer_token_symbol(row: dict[str, Any]) -> str:
    return str(
        row.get("tokenSymbol")
        or row.get("token_symbol")
        or row.get("symbol")
        or ""
    ).strip().upper()


def fetch_prelisting_transfers(offset: int = 0) -> list[dict[str, Any]]:
    token_filters = resolve_token_filters()
    params = {
        "tokens": token_filters,
        "timeGte": WINDOW_START,
        "timeLte": WINDOW_END,
        "usdGte": str(MIN_TRANSFER_USD),
        "sortKey": "usd",
        "sortDir": "desc",
        "limit": TRANSFER_LIMIT,
        "offset": offset,
    }
    payload = _arkham_get_json("/transfers", params=params)
    return _extract_transfer_list(payload)


def fetch_wallet_outflows(address: str, start: str, end: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "base": address,
        "flow": "out",
        "tokens": resolve_token_filters(),
        "timeGte": start,
        "usdGte": str(SELL_CHECK_MIN_USD),
        "sortKey": "usd",
        "sortDir": "desc",
        "limit": SELL_CHECK_LIMIT,
    }
    if end:
        params["timeLte"] = end
    payload = _arkham_get_json("/transfers", params=params)
    return _extract_transfer_list(payload)


_RESOLVED_TOKEN_FILTERS: list[str] | None = None


def _extract_token_addresses(payload: Any) -> list[str]:
    addresses: list[str] = []

    def add(value: Any, chain_hint: str = "") -> None:
        text = str(value or "").strip()
        if not text:
            return
        if text.startswith("0x") and len(text) == 42:
            addresses.append(text.lower())
        elif chain_hint and text:
            addresses.append(text)

    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, str):
                if key.startswith("0x") and len(key) == 42:
                    add(key)
                add(value, str(key))
            elif isinstance(value, dict):
                chain = str(value.get("chain") or key)
                add(value.get("address") or value.get("tokenAddress") or value.get("contractAddress"), chain)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        chain = str(item.get("chain") or key)
                        add(item.get("address") or item.get("tokenAddress") or item.get("contractAddress"), chain)
                    else:
                        add(item, str(key))
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                add(item.get("address") or item.get("tokenAddress") or item.get("contractAddress"), str(item.get("chain") or ""))
            else:
                add(item)

    return sorted(set(addresses))


def fetch_token_addresses() -> list[str]:
    if not TOKEN_ADDRESS_LOOKUP:
        return []
    try:
        payload = _arkham_get_json(f"/token/addresses/{TOKEN_ID}")
    except Exception as exc:
        print(f"  Token address lookup failed for {TOKEN_ID}: {exc}", flush=True)
        return []
    return _extract_token_addresses(payload)


def _extract_search_token_filters(payload: Any) -> list[str]:
    filters: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in filters:
            filters.append(text)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            symbol = str(value.get("symbol") or value.get("ticker") or "").strip().upper()
            name = str(value.get("name") or value.get("label") or "").strip().lower()
            pricing_id = value.get("id") or value.get("pricingId") or value.get("coinGeckoId")
            address = value.get("address") or value.get("tokenAddress") or value.get("contractAddress")
            if (
                symbol in {TOKEN_SYMBOL, TOKEN_DISPLAY}
                or TOKEN_ID.lower() in {str(pricing_id or "").lower(), name}
                or TOKEN_DISPLAY.lower() in name
            ):
                add(pricing_id)
                add(address)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return filters


def fetch_token_search_filters() -> list[str]:
    if not TOKEN_SEARCH_LOOKUP:
        return []
    queries = [TOKEN_DISPLAY, TOKEN_SYMBOL, TOKEN_ID]
    found: list[str] = []
    for query in dict.fromkeys(q for q in queries if q):
        try:
            payload = _arkham_get_json("/intelligence/search", params={"query": query, "tokens": 10})
        except Exception as exc:
            print(f"  Token search failed for {query}: {exc}", flush=True)
            continue
        for value in _extract_search_token_filters(payload):
            if value and value not in found:
                found.append(value)
        time.sleep(0.25)
    return found


def resolve_token_filters() -> list[str]:
    global _RESOLVED_TOKEN_FILTERS
    if _RESOLVED_TOKEN_FILTERS is not None:
        return _RESOLVED_TOKEN_FILTERS
    filters: list[str] = []
    for value in [*TOKEN_FILTER, TOKEN_ID, TOKEN_SYMBOL, TOKEN_DISPLAY]:
        if value and value not in filters:
            filters.append(value)
    for address in fetch_token_addresses():
        if address not in filters:
            filters.append(address)
    for value in fetch_token_search_filters():
        if value not in filters:
            filters.append(value)
    _RESOLVED_TOKEN_FILTERS = filters
    return filters


def fetch_wallet_balance_usd(address: str) -> float:
    payload = _arkham_get_json(f"/balances/address/{address}")
    return _balance_usd(payload)


def _balance_usd(payload: Any) -> float:
    values: list[float] = []
    usd_markers = ("usd", "totalbalanceusd", "valueusd", "historicalusd")

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = str(key).lower()
                if any(marker in lowered for marker in usd_markers):
                    parsed = _to_float(child, -1)
                    if parsed >= 0:
                        values.append(parsed)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return max(values) if values else 0.0


def aggregate_accumulation(transfers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for row in transfers:
        to_obj = _address_obj(row.get("toAddress") or row.get("to") or row.get("recipient"))
        from_obj = _address_obj(row.get("fromAddress") or row.get("from") or row.get("sender"))
        address = _normalize_address(to_obj.get("address") or to_obj.get("id"))
        from_address = _normalize_address(from_obj.get("address") or from_obj.get("id"))
        if (
            not address
            or _is_null_or_burn_address(address, to_obj)
            or _is_null_or_burn_address(from_address, from_obj)
            or _is_service_destination(to_obj)
            or (SKIP_INFRA_SOURCES and _is_infra_source(from_obj))
            or (SKIP_DISTRIBUTION_SOURCES and _is_distribution_source(from_obj))
        ):
            continue
        usd = transfer_usd(row)
        if usd < MIN_TRANSFER_USD:
            continue
        ts = transfer_time(row)
        token_symbol = transfer_token_symbol(row)
        chain = str(row.get("chain") or to_obj.get("chain") or from_obj.get("chain") or "").strip().lower()
        source = _entity_name(from_obj) or _normalize_address(from_obj.get("address") or from_obj.get("id"))
        candidate = candidates.setdefault(address, {
            "token": TOKEN_DISPLAY or TOKEN_SYMBOL,
            "token_id": TOKEN_ID,
            "listing_exchange": LISTING_EXCHANGE,
            "address": address,
            "chains": set(),
            "first_seen": ts,
            "last_seen": ts,
            "total_in_usd": 0.0,
            "max_transfer_usd": 0.0,
            "tx_count": 0,
            "source_entities": set(),
            "labels": set(),
            "sample_txs": [],
            "token_symbols": set(),
        })
        if chain:
            candidate["chains"].add(chain)
        if source:
            candidate["source_entities"].add(source)
        label = _entity_name(to_obj)
        if label:
            candidate["labels"].add(label)
        if token_symbol:
            candidate["token_symbols"].add(token_symbol)
        candidate["total_in_usd"] += usd
        candidate["max_transfer_usd"] = max(candidate["max_transfer_usd"], usd)
        candidate["tx_count"] += 1
        if ts and (not candidate["first_seen"] or ts < candidate["first_seen"]):
            candidate["first_seen"] = ts
        if ts and (not candidate["last_seen"] or ts > candidate["last_seen"]):
            candidate["last_seen"] = ts
        if len(candidate["sample_txs"]) < 5:
            candidate["sample_txs"].append({
                "hash": row.get("transactionHash") or row.get("hash"),
                "ts": _dt_text(ts),
                "usd": usd,
                "from": source,
                "chain": chain,
            })
    return candidates


def classify_candidate(candidate: dict[str, Any]) -> str:
    text = " ".join(sorted(candidate.get("source_entities") or [])) + " " + " ".join(sorted(candidate.get("labels") or []))
    lower = text.lower()
    if any(word in lower for word in MARKET_MAKER_WORDS):
        return "market_maker_route"
    if any(word in lower for word in DISTRIBUTION_SOURCE_WORDS):
        return "distribution_route"
    if any(word in lower for word in ("treasury", "foundation", "deploy", "team")):
        return "project_source"
    if any(word in lower for word in ("custody", "anchorage", "bitgo", "fireblocks")):
        return "custody_route"
    return "unknown_accumulation"


def score_candidate(candidate: dict[str, Any]) -> int:
    score = 0
    total = float(candidate.get("total_in_usd") or 0)
    max_transfer = float(candidate.get("max_transfer_usd") or 0)
    tx_count = int(candidate.get("tx_count") or 0)
    pre_out = float(candidate.get("pre_listing_out_usd") or 0)
    post_out = float(candidate.get("post_listing_out_usd") or 0)
    first_seen = candidate.get("first_seen")
    listing_dt = _parse_dt(LISTING_TS)

    if total >= 1_000_000:
        score += 35
    elif total >= 500_000:
        score += 25
    elif total >= 100_000:
        score += 15
    elif total >= MIN_TRANSFER_USD:
        score += 10

    if max_transfer >= 250_000:
        score += 10
    if tx_count >= 3:
        score += 10
    if isinstance(first_seen, datetime) and listing_dt and (listing_dt - first_seen).days >= 7:
        score += 15
    if pre_out <= max(SELL_CHECK_MIN_USD, total * 0.2):
        score += 20
    if post_out == 0:
        score += 5

    classification = classify_candidate(candidate)
    if classification in {"market_maker_route", "project_source", "custody_route"}:
        score += 10
    if pre_out >= total * 1.2 and total > 0:
        score -= 35
    elif pre_out >= total * 0.8 and total > 0:
        score -= 25
    elif pre_out >= total * 0.5 and total > 0:
        score -= 15

    return max(0, min(100, int(score)))


def held_through_listing(candidate: dict[str, Any]) -> bool:
    if not FILTER_EXITED_BEFORE_LISTING:
        return True
    total = float(candidate.get("total_in_usd") or 0)
    if total <= 0:
        return False
    pre_out = float(candidate.get("pre_listing_out_usd") or 0)
    return pre_out <= max(SELL_CHECK_MIN_USD, total * MAX_PRELISTING_OUT_RATIO)


def is_investigable_candidate(candidate: dict[str, Any]) -> bool:
    classification = candidate.get("classification") or classify_candidate(candidate)
    if FILTER_DISTRIBUTION_ROUTES and classification == "distribution_route":
        return False
    return held_through_listing(candidate)


def summarize_outflows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for row in sorted(rows, key=transfer_usd, reverse=True)[:TRACE_DESTINATION_LIMIT]:
        to_obj = _address_obj(row.get("toAddress") or row.get("to") or row.get("recipient"))
        destination = _entity_name(to_obj) or _normalize_address(to_obj.get("address") or to_obj.get("id"))
        summary.append({
            "destination": destination,
            "usd": round(transfer_usd(row), 2),
            "ts": _dt_text(transfer_time(row)),
            "tx": row.get("transactionHash") or row.get("hash"),
        })
    return summary


def enrich_candidates(candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(candidates.values(), key=lambda row: float(row.get("total_in_usd") or 0), reverse=True)
    enriched: list[dict[str, Any]] = []
    for index, candidate in enumerate(ranked[:ENRICH_LIMIT], start=1):
        address = candidate["address"]
        print(f"  [{index}/{min(len(ranked), ENRICH_LIMIT)}] checking {address[:18]}...", flush=True)
        try:
            pre_outflows = fetch_wallet_outflows(address, WINDOW_START, LISTING_TS)
            time.sleep(1.05)
            post_outflows = fetch_wallet_outflows(address, LISTING_TS, None)
            time.sleep(1.05)
            balance_usd = fetch_wallet_balance_usd(address)
            time.sleep(1.05)
        except Exception as exc:
            candidate["enrich_error"] = str(exc)
            pre_outflows = []
            post_outflows = []
            balance_usd = 0.0

        candidate["pre_listing_out_usd"] = sum(transfer_usd(row) for row in pre_outflows)
        candidate["post_listing_out_usd"] = sum(transfer_usd(row) for row in post_outflows)
        candidate["post_listing_destinations"] = summarize_outflows(post_outflows)
        candidate["balance_usd"] = balance_usd
        candidate["classification"] = classify_candidate(candidate)
        candidate["score"] = score_candidate(candidate)
        if is_investigable_candidate(candidate):
            enriched.append(candidate)
        elif candidate["classification"] == "distribution_route":
            print("    skipped: distribution/presale/claim route", flush=True)
        else:
            print(
                f"    skipped: exited before listing "
                f"(pre-out ${candidate['pre_listing_out_usd']:,.0f} vs in ${candidate['total_in_usd']:,.0f})",
                flush=True,
            )
    return sorted(enriched, key=lambda row: (int(row.get("score") or 0), float(row.get("total_in_usd") or 0)), reverse=True)


def row_for_supabase(candidate: dict[str, Any]) -> dict[str, Any]:
    total_in = float(candidate.get("total_in_usd") or 0)
    pre_out = float(candidate.get("pre_listing_out_usd") or 0)
    retention_pct = max(0.0, min(100.0, ((total_in - pre_out) / total_in) * 100)) if total_in > 0 else 0.0
    return {
        "token": TOKEN_DISPLAY or TOKEN_SYMBOL,
        "token_id": TOKEN_ID,
        "listing_exchange": LISTING_EXCHANGE,
        "listing_ts": LISTING_TS,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "address": candidate["address"],
        "chains": sorted(candidate.get("chains") or []),
        "first_seen": _dt_text(candidate.get("first_seen")),
        "last_seen": _dt_text(candidate.get("last_seen")),
        "total_in_usd": round(float(candidate.get("total_in_usd") or 0), 2),
        "max_transfer_usd": round(float(candidate.get("max_transfer_usd") or 0), 2),
        "pre_listing_out_usd": round(float(candidate.get("pre_listing_out_usd") or 0), 2),
        "post_listing_out_usd": round(float(candidate.get("post_listing_out_usd") or 0), 2),
        "pre_listing_retention_pct": round(retention_pct, 2),
        "post_listing_destinations": candidate.get("post_listing_destinations") or [],
        "balance_usd": round(float(candidate.get("balance_usd") or 0), 2),
        "tx_count": int(candidate.get("tx_count") or 0),
        "score": int(candidate.get("score") or 0),
        "classification": candidate.get("classification") or classify_candidate(candidate),
        "source_entities": sorted(candidate.get("source_entities") or []),
        "labels": sorted(candidate.get("labels") or []),
        "raw": {
            "sample_txs": candidate.get("sample_txs") or [],
            "post_listing_destinations": candidate.get("post_listing_destinations") or [],
            "token_symbols": sorted(candidate.get("token_symbols") or []),
            "enrich_error": candidate.get("enrich_error"),
        },
    }


def save_candidate(candidate: dict[str, Any]) -> bool:
    if not SAVE_TO_SUPABASE:
        return False
    row = row_for_supabase(candidate)
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
        headers=_supabase_headers(),
        params={"on_conflict": "token_id,address"},
        data=json.dumps(row),
        timeout=30,
    )
    if response.status_code >= 400:
        print(f"  Supabase save failed for {candidate['address'][:10]}...: HTTP {response.status_code} {response.text[:300]}", flush=True)
        return False
    return True


def run_scan() -> list[dict[str, Any]]:
    _require_env()
    print(
        f"ARKHAM PRE-LISTING TOKEN SCAN - {TOKEN_DISPLAY or TOKEN_SYMBOL} ({TOKEN_ID}) "
        f"{WINDOW_START} -> {WINDOW_END}, min ${MIN_TRANSFER_USD:,.0f}",
        flush=True,
    )
    print(
        "Filters: "
        f"skip_infra={SKIP_INFRA_SOURCES}, "
        f"skip_distribution_sources={SKIP_DISTRIBUTION_SOURCES}, "
        f"filter_distribution_routes={FILTER_DISTRIBUTION_ROUTES}, "
        f"filter_exited={FILTER_EXITED_BEFORE_LISTING}, "
        f"max_pre_out_ratio={MAX_PRELISTING_OUT_RATIO}",
        flush=True,
    )
    print(f"Token filters: {', '.join(resolve_token_filters())}", flush=True)
    all_transfers: list[dict[str, Any]] = []
    for page in range(MAX_OFFSETS):
        offset = page * TRANSFER_LIMIT
        print(f"Fetching transfers offset={offset}...", flush=True)
        rows = fetch_prelisting_transfers(offset)
        all_transfers.extend(rows)
        if len(rows) < TRANSFER_LIMIT:
            break
        time.sleep(1.05)

    candidates = aggregate_accumulation(all_transfers)
    print(f"Large transfers: {len(all_transfers)}; recipient candidates: {len(candidates)}", flush=True)
    enriched = enrich_candidates(candidates)

    saved = 0
    print(f"\nTop pre-listing wallets for {TOKEN_DISPLAY or TOKEN_SYMBOL}:", flush=True)
    for row in enriched[:20]:
        if SAVE_TO_SUPABASE and save_candidate(row):
            saved += 1
        print(
            f"- {row['address']} | score={row.get('score', 0)} | "
            f"in=${float(row.get('total_in_usd') or 0):,.0f} | "
            f"pre-out=${float(row.get('pre_listing_out_usd') or 0):,.0f} | "
            f"post-out=${float(row.get('post_listing_out_usd') or 0):,.0f} | "
            f"balance=${float(row.get('balance_usd') or 0):,.0f} | "
            f"class={row.get('classification')}",
            flush=True,
        )
        sources = ", ".join(sorted(row.get("source_entities") or []))
        if sources:
            print(f"  sources: {sources[:220]}", flush=True)
        if TRACE_POST_DESTINATIONS and row.get("post_listing_destinations"):
            destinations = "; ".join(
                f"{item.get('destination') or '?'} (${float(item.get('usd') or 0):,.0f})"
                for item in row["post_listing_destinations"]
            )
            print(f"  post-listing out: {destinations[:260]}", flush=True)
    if SAVE_TO_SUPABASE:
        print(f"\nSaved pre-listing wallets: {saved}/{len(enriched[:20])}", flush=True)
    return enriched


if __name__ == "__main__":
    run_scan()
