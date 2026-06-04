"""
Arkham exchange-entity scanner.

Standalone cron:
    python arkham_scanner.py

Detects tokens held by exchange entities that are not yet listed on that
exchange, then stores candidates in Supabase transacted_tokens.
"""
from __future__ import annotations

import os
import json
import time
import base64
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
SUPABASE_KEY_SOURCE = ""
SUPABASE_KEY = ""
for _key_name in ("SUPABASE_SERVICE_ROLE", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY"):
    _key_value = os.getenv(_key_name, "").strip()
    if _key_value:
        SUPABASE_KEY_SOURCE = _key_name
        SUPABASE_KEY = _key_value
        break

VALUE_THRESHOLD_USD = float(os.getenv("ARKHAM_MIN_VALUE_USD", "50000"))
SMART_MONEY_THRESHOLD_USD = float(os.getenv("ARKHAM_SMART_MONEY_MIN_VALUE_USD", "100000"))
ARKHAM_SIGNALS_TABLE = os.getenv("ARKHAM_SIGNALS_TABLE", "arkham_signals")

LOW_SIGNAL_SYMBOLS = {
    "USDT", "USDT0", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDE", "USDS", "USD1",
    "EUR", "EURC", "EURS", "PYUSD",
    "BTC", "WBTC", "BTCB", "CBBTC", "TBTC",
    "ETH", "WETH", "STETH", "WSTETH", "RETH", "CBETH",
    "BNB", "WBNB", "SOL", "WSOL", "AVAX", "WAVAX", "MATIC", "WMATIC",
}

EXCHANGES = [
    {"slug": "binance", "exchange": "Binance"},
    {"slug": "coinbase", "exchange": "Coinbase"},
    {"slug": "gate-io", "exchange": "Gate.io"},
    {"slug": "okx", "exchange": "OKX"},
    {"slug": "bybit", "exchange": "Bybit"},
    {"slug": "kraken", "exchange": "Kraken"},
    {"slug": "bitget", "exchange": "Bitget"},
    {"slug": "mexc", "exchange": "MEXC"},
]

SMART_MONEY_FUNDS = [
    {"slug": "wintermute", "name": "Wintermute"},
    {"slug": "jump-trading", "name": "Jump Trading"},
    {"slug": "paradigm", "name": "Paradigm"},
    {"slug": "a16z", "name": "a16z"},
    {"slug": "multicoin-capital", "name": "Multicoin Capital"},
    {"slug": "drw-cumberland", "name": "DRW Cumberland"},
    {"slug": "galaxy-digital", "name": "Galaxy Digital"},
    {"slug": "pantera-capital", "name": "Pantera Capital"},
    {"slug": "dwr-cumberland", "name": "DWR Cumberland"},
]


def _limit_entities(items: list[dict[str, str]], env_name: str, slug_key: str = "slug") -> list[dict[str, str]]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return items

    allowed = {part.strip().lower() for part in raw.split(",") if part.strip()}
    if not allowed:
        return items

    filtered = [
        item for item in items
        if str(item.get(slug_key) or "").lower() in allowed
        or str(item.get("exchange") or item.get("name") or "").lower() in allowed
    ]
    if not filtered:
        print(f"{env_name} definido, mas sem matches: {raw}. A usar lista completa.", flush=True)
        return items
    print(f"{env_name}: limitado a {len(filtered)} entidade(s): {raw}", flush=True)
    return filtered

ARKHAM_HEADERS = {
    "API-Key": ARKHAM_API_KEY,
    "Accept": "application/json",
    "User-Agent": "vigia-crypto-arkham-scanner/1.0",
}

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


def _require_env() -> None:
    missing = []
    if not ARKHAM_API_KEY:
        missing.append("ARKHAM_API_KEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE or SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")
    role = _supabase_jwt_role(SUPABASE_KEY)
    if SUPABASE_KEY_SOURCE == "SUPABASE_ANON_KEY" or role != "service_role":
        raise RuntimeError(
            "ARKHAM scanner needs a real Supabase service_role key in Render "
            "(SUPABASE_SERVICE_ROLE or SUPABASE_SERVICE_ROLE_KEY). "
            f"Detected env={SUPABASE_KEY_SOURCE or 'missing'}, jwt_role={role or 'unknown'}. "
            "Anon/authenticated keys cannot insert into arkham_signals with RLS."
        )


def _supabase_jwt_role(token: str) -> str:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return ""
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
        return str(data.get("role") or "").strip()
    except Exception:
        return ""


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_chain(value: Any) -> str:
    chain = str(value or "unknown").strip().lower()
    aliases = {
        "eth": "ethereum",
        "ethereum": "ethereum",
        "sol": "solana",
        "solana": "solana",
        "bsc": "bsc",
        "bnb": "bsc",
        "bnb chain": "bsc",
        "avalanche": "avalanche",
        "avax": "avalanche",
    }
    return aliases.get(chain, chain or "unknown")


def _float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _extract_token_rows(payload: Any, chain_hint: str | None = None) -> list[dict[str, Any]]:
    """Accept common Arkham portfolio shapes and return raw token rows."""
    if isinstance(payload, list):
        rows = []
        for row in payload:
            if isinstance(row, dict):
                rows.append({"chain": chain_hint, **row} if chain_hint and not row.get("chain") else row)
        return rows

    if not isinstance(payload, dict):
        return []

    balances = payload.get("balances")
    if isinstance(balances, list):
        rows: list[dict[str, Any]] = []
        for item in balances:
            if not isinstance(item, dict):
                continue
            chain = item.get("chain") or item.get("network") or item.get("chainName") or chain_hint
            nested = []
            for key in ("tokens", "balances", "holdings", "assets", "tokenBalances", "token_balances"):
                value = item.get(key)
                if isinstance(value, list):
                    nested = value
                    break
            if nested:
                for row in nested:
                    if isinstance(row, dict):
                        rows.append({"chain": chain, **row})
            elif any(k in item for k in ("symbol", "usd", "value", "balance", "token", "asset")):
                rows.append(item)
        return rows

    if isinstance(balances, dict):
        rows: list[dict[str, Any]] = []
        for chain, value in balances.items():
            if isinstance(value, list):
                for row in value:
                    if isinstance(row, dict):
                        rows.append({"chain": chain, **row})
            elif isinstance(value, dict):
                for token_id, row in value.items():
                    if isinstance(row, dict):
                        rows.append({"chain": chain, "pricingID": token_id, **row})
                    else:
                        rows.append({"chain": chain, "pricingID": token_id, "balance": row})
        return rows

    for key in ("tokens", "portfolio", "balances", "holdings", "assets", "tokenBalances", "token_balances", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return _extract_token_rows(value, chain_hint=chain_hint)
        if isinstance(value, dict):
            nested = _extract_token_rows(value, chain_hint=chain_hint)
            if nested:
                return nested

    # Some APIs return {"ethereum": [...], "solana": [...]}.
    rows: list[dict[str, Any]] = []
    for chain, value in payload.items():
        if isinstance(value, list):
            for row in value:
                if isinstance(row, dict):
                    rows.append({"chain": chain, **row})
        elif isinstance(value, dict) and any(k in value for k in ("symbol", "usd", "value", "balance", "token")):
            rows.append({"chain": chain_hint, "pricingID": chain, **value})
    return rows


def _normalize_token(row: dict[str, Any]) -> dict[str, Any] | None:
    token_meta = {}
    for meta_key in ("token", "asset", "currency", "arkhamToken", "tokenInfo", "metadata"):
        if isinstance(row.get(meta_key), dict):
            token_meta = row[meta_key]
            break
    symbol = _normalize_symbol(
        row.get("symbol")
        or row.get("tokenSymbol")
        or row.get("token_symbol")
        or row.get("ticker")
        or row.get("assetSymbol")
        or row.get("currencySymbol")
        or token_meta.get("symbol")
        or token_meta.get("ticker")
        or token_meta.get("assetSymbol")
        or row.get("name")
        or token_meta.get("name")
        or row.get("pricingID")
        or row.get("id")
    )
    if not symbol:
        return None

    value_usd = _float_or_zero(
        row.get("value")
        or row.get("valueUsd")
        or row.get("value_usd")
        or row.get("usdValue")
        or row.get("usd")
        or row.get("balanceUsd")
        or row.get("balance_usd")
        or row.get("totalValue")
        or row.get("totalValueUsd")
        or row.get("balanceUSD")
        or row.get("marketValue")
        or row.get("marketValueUsd")
        or row.get("holdingValue")
        or row.get("holdingValueUsd")
    )
    amount = _float_or_zero(
        row.get("amount")
        or row.get("balance")
        or row.get("quantity")
        or row.get("holdings")
        or row.get("tokenBalance")
        or row.get("holdingsAmount")
        or row.get("tokenAmount")
    )
    chain = _normalize_chain(row.get("chain") or row.get("network") or row.get("chainName"))
    token_address = str(
        row.get("address")
        or row.get("tokenAddress")
        or row.get("token_address")
        or row.get("contractAddress")
        or row.get("contract_address")
        or row.get("identifier")
        or row.get("tokenIdentifier")
        or token_meta.get("address")
        or token_meta.get("tokenAddress")
        or token_meta.get("identifier")
        or ""
    ).strip()

    return {
        "symbol": symbol,
        "value_usd": value_usd,
        "amount": amount,
        "chain": chain,
        "token_address": token_address,
    }


def _raise_arkham_error(response: requests.Response, endpoint: str) -> None:
    body = response.text[:500].replace("\n", " ")
    raise requests.HTTPError(
        f"{response.status_code} Client Error for {endpoint}: {body}",
        response=response,
    )


def _arkham_get_json(endpoint: str) -> Any:
    url = f"{ARKHAM_BASE_URL}{endpoint}"
    response = requests.get(url, headers=ARKHAM_HEADERS, timeout=30)
    if response.status_code >= 400:
        _raise_arkham_error(response, endpoint)
    return response.json()


def _payload_debug(payload: Any) -> str:
    try:
        if isinstance(payload, dict):
            keys = list(payload.keys())[:12]
            sample = json.dumps(payload, ensure_ascii=False, default=str)[:900]
            return f"type=dict keys={keys} sample={sample}"
        if isinstance(payload, list):
            sample = json.dumps(payload[:2], ensure_ascii=False, default=str)[:900]
            return f"type=list len={len(payload)} sample={sample}"
        return f"type={type(payload).__name__} value={str(payload)[:300]}"
    except Exception as exc:
        return f"debug_failed={exc}"


def fetch_arkham_portfolio(slug: str, min_value_usd: float = VALUE_THRESHOLD_USD) -> list[dict[str, Any]]:
    # Balances is the current-token-holdings endpoint. Portfolio is kept as a
    # fallback because some API docs/examples still mention it for entities.
    errors: list[str] = []
    payload = None
    for endpoint in (f"/balances/entity/{slug}", f"/portfolio/entity/{slug}"):
        try:
            payload = _arkham_get_json(endpoint)
            break
        except Exception as exc:
            errors.append(str(exc))

    if payload is None:
        raise RuntimeError(" | ".join(errors))

    raw_rows = _extract_token_rows(payload)
    tokens: list[dict[str, Any]] = []
    normalized_seen = 0
    for row in raw_rows:
        token = _normalize_token(row)
        if token:
            normalized_seen += 1
            if token["value_usd"] > min_value_usd:
                tokens.append(token)
    if not tokens:
        print(
            f"   Arkham debug {slug}: raw_rows={len(raw_rows)} normalized={normalized_seen} "
            f"threshold=${min_value_usd:,.0f} {_payload_debug(payload)}",
            flush=True,
        )
    return tokens


def fetch_listed_tokens(exchange: str) -> set[str]:
    url = f"{SUPABASE_URL}/rest/v1/exchange_tokens"
    params = {
        "select": "token",
        "exchange": f"eq.{exchange}",
        "limit": "10000",
    }
    response = requests.get(url, params=params, headers=SUPABASE_HEADERS, timeout=20)
    if response.status_code >= 400:
        print(
            f"⚠️ Supabase exchange_tokens falhou para {exchange}: "
            f"HTTP {response.status_code} - {response.text[:200]}",
            flush=True,
        )
        return set()
    return {_normalize_symbol(row.get("token")) for row in response.json() if row.get("token")}


def listing_symbol_candidates(symbol: str) -> set[str]:
    normalized = _normalize_symbol(symbol)
    candidates = {normalized}
    prefix_rules = (
        ("CB", 4),
        ("ST", 4),
        ("W", 3),
        ("S", 4),
    )
    for prefix, min_len in prefix_rules:
        if normalized.startswith(prefix) and len(normalized) > min_len:
            candidates.add(normalized[len(prefix):])
    return {candidate for candidate in candidates if candidate}


def is_low_signal_exchange_asset(symbol: str, listed: set[str] | None = None) -> bool:
    candidates = listing_symbol_candidates(symbol)
    if candidates & LOW_SIGNAL_SYMBOLS:
        return True
    if listed and len(candidates) > 1 and any(candidate in listed for candidate in candidates if candidate != _normalize_symbol(symbol)):
        return True
    return False


def is_listed_on_exchange(symbol: str, listed: set[str]) -> bool:
    return any(candidate in listed for candidate in listing_symbol_candidates(symbol))


def score_candidate(value_usd: float, exchange_count: int) -> int:
    score = 0
    if value_usd > 1_000_000:
        score += 40
    elif value_usd > 500_000:
        score += 25
    elif value_usd > 100_000:
        score += 15

    if exchange_count >= 2:
        score += 20
    if exchange_count >= 3:
        score += 35

    return min(score, 100)


def supabase_upsert(table: str, row: dict[str, Any], conflict_cols: list[str]) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {"on_conflict": ",".join(conflict_cols)}
    response = requests.post(url, json=row, params=params, headers=SUPABASE_HEADERS, timeout=20)
    if response.status_code in (200, 201):
        return True
    print(
        f"⚠️ Supabase upsert {table} por {conflict_cols} falhou: "
        f"HTTP {response.status_code} - {response.text[:240]}",
        flush=True,
    )
    return False


def save_candidate(candidate: dict[str, Any], signal_type: str = "holding") -> bool:
    token = candidate["token"]
    exchange = candidate["exchange"]
    chain = candidate["chain"]
    # Arkham may not return token addresses for every chain; keep a stable
    # synthetic key so NOT NULL / legacy unique constraints do not break.
    token_address = candidate.get("token_address") or f"arkham:{signal_type}:{exchange.lower()}:{chain}:{token}"
    entity_type = "smart_money" if signal_type == "smart_money" else "exchange"
    signal_key = f"{signal_type}:{exchange.lower()}:{chain}:{token_address or token}".lower()

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "signal_key": signal_key,
        "entity": exchange,
        "entity_type": entity_type,
        "exchange": exchange,
        "token": token,
        "token_address": token_address,
        "chain": chain,
        "amount": candidate.get("amount", 0),
        "value_usd": candidate["value_usd"],
        "score": candidate["score"],
        "ts": now,
        "type": signal_type,
        "signature": f"arkham-{signal_type}-{exchange.lower()}-{chain}-{token}",
        "pair_url": f"https://dexscreener.com/search?q={token}",
        "analysis_text": (
            f"{token} detected in Arkham {exchange} entity portfolio. "
            f"Value: ${candidate['value_usd']:,.0f}. "
            f"Seen across {candidate['exchange_count']} monitored exchange(s)."
        ),
    }

    saved = supabase_upsert(ARKHAM_SIGNALS_TABLE, row, ["signal_key"])
    if saved:
        return True

    if os.getenv("ARKHAM_LEGACY_TRANSACTED_TOKENS", "").strip() == "1":
        return (
            supabase_upsert("transacted_tokens", row, ["token_address", "type", "chain", "exchange"])
            or supabase_upsert("transacted_tokens", row, ["token_address", "type", "chain"])
        )
    return False


def scan_exchange_candidates() -> tuple[dict[str, set[str]], int, int]:
    start = time.time()
    exchange_holdings: dict[str, list[dict[str, Any]]] = {}
    token_exchanges: dict[str, set[str]] = defaultdict(set)

    exchanges = _limit_entities(EXCHANGES, "ARKHAM_EXCHANGE_SLUGS")
    for index, item in enumerate(exchanges):
        slug = item["slug"]
        exchange = item["exchange"]
        try:
            print(f"🏦 Arkham portfolio: {exchange} ({slug})", flush=True)
            tokens = fetch_arkham_portfolio(slug, VALUE_THRESHOLD_USD)
            exchange_holdings[exchange] = tokens
            for token in tokens:
                token_exchanges[token["symbol"]].add(exchange)
            print(f"   ✅ {len(tokens)} tokens acima de ${VALUE_THRESHOLD_USD:,.0f}", flush=True)
        except Exception as exc:
            exchange_holdings[exchange] = []
            print(f"   ⚠️ Arkham falhou para {exchange}: {exc}", flush=True)

        if index < len(exchanges) - 1:
            time.sleep(1.1)

    candidates: list[dict[str, Any]] = []
    exchanges_with_candidates: set[str] = set()

    for exchange, tokens in exchange_holdings.items():
        listed = fetch_listed_tokens(exchange)
        if not listed:
            print(f"   ⚠️ {exchange}: tabela exchange_tokens vazia/inacessivel", flush=True)

        for token in tokens:
            symbol = token["symbol"]
            if is_low_signal_exchange_asset(symbol, listed) or is_listed_on_exchange(symbol, listed):
                continue

            exchange_count = len(token_exchanges[symbol])
            score = score_candidate(token["value_usd"], exchange_count)
            if score <= 0:
                continue

            candidates.append({
                "exchange": exchange,
                "token": symbol,
                "chain": token["chain"],
                "amount": token["amount"],
                "value_usd": token["value_usd"],
                "token_address": token["token_address"],
                "exchange_count": exchange_count,
                "score": score,
            })
            exchanges_with_candidates.add(exchange)

    saved = 0
    for candidate in sorted(candidates, key=lambda row: row["score"], reverse=True):
        if save_candidate(candidate, signal_type="arkham_exchange"):
            saved += 1
            print(
                f"💾 {candidate['token']} · {candidate['exchange']} · "
                f"${candidate['value_usd']:,.0f} · score {candidate['score']}",
                flush=True,
            )

    elapsed = round(time.time() - start, 1)
    print(
        f"✅ {len(candidates)} candidatos encontrados em "
        f"{len(exchanges_with_candidates)} exchanges; {saved} guardados. "
        f"Duração: {elapsed}s",
        flush=True,
    )
    return token_exchanges, len(candidates), saved


def scan_smart_money(token_exchanges: dict[str, set[str]]) -> tuple[int, int]:
    print("🧠 ARKHAM SMART MONEY TRACKER — iniciado", flush=True)
    candidates: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()

    funds = _limit_entities(SMART_MONEY_FUNDS, "ARKHAM_SMART_MONEY_SLUGS")
    for index, item in enumerate(funds):
        slug = item["slug"]
        fund_name = item["name"]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        try:
            print(f"🐋 Arkham portfolio: {fund_name} ({slug})", flush=True)
            tokens = fetch_arkham_portfolio(slug, SMART_MONEY_THRESHOLD_USD)
            print(f"   ✅ {len(tokens)} tokens acima de ${SMART_MONEY_THRESHOLD_USD:,.0f}", flush=True)
        except Exception as exc:
            print(f"   ⚠️ Arkham falhou para {fund_name}: {exc}", flush=True)
            tokens = []

        for token in tokens:
            symbol = token["symbol"]
            exchange_count = len(token_exchanges.get(symbol, set()))
            score = score_candidate(token["value_usd"], 1)
            if exchange_count >= 1:
                score += 30
            score = min(score, 100)
            if score <= 0:
                continue

            candidates.append({
                "exchange": fund_name,
                "token": symbol,
                "chain": token["chain"],
                "amount": token["amount"],
                "value_usd": token["value_usd"],
                "token_address": token["token_address"],
                "exchange_count": max(exchange_count, 1),
                "score": score,
            })

        if index < len(funds) - 1:
            time.sleep(1.1)

    saved = 0
    for candidate in sorted(candidates, key=lambda row: row["score"], reverse=True):
        if save_candidate(candidate, signal_type="smart_money"):
            saved += 1
            print(
                f"💾 smart_money {candidate['token']} · {candidate['exchange']} · "
                f"${candidate['value_usd']:,.0f} · score {candidate['score']}",
                flush=True,
            )

    print(f"✅ Smart money: {len(candidates)} candidatos; {saved} guardados.", flush=True)
    return len(candidates), saved


def main() -> None:
    _require_env()
    print("🔎 ARKHAM EXCHANGE SCANNER — iniciado", flush=True)
    start = time.time()

    token_exchanges, exchange_candidates, exchange_saved = scan_exchange_candidates()
    smart_candidates, smart_saved = scan_smart_money(token_exchanges)

    print(
        f"🏁 Arkham concluido: exchange={exchange_candidates}/{exchange_saved}, "
        f"smart_money={smart_candidates}/{smart_saved}. "
        f"Duracao total: {round(time.time() - start, 1)}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
