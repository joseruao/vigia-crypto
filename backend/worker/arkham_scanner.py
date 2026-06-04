"""
Arkham exchange-entity scanner.

Standalone cron:
    python arkham_scanner.py

Detects tokens held by exchange entities that are not yet listed on that
exchange, then stores candidates in Supabase transacted_tokens.
"""
from __future__ import annotations

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
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
).strip()

VALUE_THRESHOLD_USD = 50_000
SMART_MONEY_THRESHOLD_USD = 100_000

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
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")


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


def _extract_token_rows(payload: Any) -> list[dict[str, Any]]:
    """Accept common Arkham portfolio shapes and return raw token rows."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("tokens", "portfolio", "balances", "holdings", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            nested = _extract_token_rows(value)
            if nested:
                return nested

    # Some APIs return {"ethereum": [...], "solana": [...]}.
    rows: list[dict[str, Any]] = []
    for chain, value in payload.items():
        if isinstance(value, list):
            for row in value:
                if isinstance(row, dict):
                    rows.append({"chain": chain, **row})
    return rows


def _normalize_token(row: dict[str, Any]) -> dict[str, Any] | None:
    symbol = _normalize_symbol(
        row.get("symbol")
        or row.get("tokenSymbol")
        or row.get("ticker")
        or row.get("name")
    )
    if not symbol:
        return None

    value_usd = _float_or_zero(
        row.get("value")
        or row.get("valueUsd")
        or row.get("value_usd")
        or row.get("usdValue")
    )
    amount = _float_or_zero(row.get("amount") or row.get("balance") or row.get("quantity"))
    chain = _normalize_chain(row.get("chain") or row.get("network"))
    token_address = str(
        row.get("address")
        or row.get("tokenAddress")
        or row.get("contractAddress")
        or ""
    ).strip()

    return {
        "symbol": symbol,
        "value_usd": value_usd,
        "amount": amount,
        "chain": chain,
        "token_address": token_address,
    }


def fetch_arkham_portfolio(slug: str, min_value_usd: float = VALUE_THRESHOLD_USD) -> list[dict[str, Any]]:
    url = f"{ARKHAM_BASE_URL}/portfolio/entity/{slug}"
    response = requests.get(url, headers=ARKHAM_HEADERS, timeout=30)
    response.raise_for_status()

    raw_rows = _extract_token_rows(response.json())
    tokens: list[dict[str, Any]] = []
    for row in raw_rows:
        token = _normalize_token(row)
        if token and token["value_usd"] > min_value_usd:
            tokens.append(token)
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

    now = datetime.now(timezone.utc).isoformat()
    row = {
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

    # Preferred constraint requested for this scanner. Fallbacks keep the job
    # useful if the database migration has not yet been applied.
    return (
        supabase_upsert("transacted_tokens", row, ["token", "exchange"])
        or supabase_upsert("transacted_tokens", row, ["token_address", "type", "chain", "exchange"])
        or supabase_upsert("transacted_tokens", row, ["token_address", "type", "chain"])
    )


def scan_exchange_candidates() -> tuple[dict[str, set[str]], int, int]:
    start = time.time()
    exchange_holdings: dict[str, list[dict[str, Any]]] = {}
    token_exchanges: dict[str, set[str]] = defaultdict(set)

    for index, item in enumerate(EXCHANGES):
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

        if index < len(EXCHANGES) - 1:
            time.sleep(1.1)

    candidates: list[dict[str, Any]] = []
    exchanges_with_candidates: set[str] = set()

    for exchange, tokens in exchange_holdings.items():
        listed = fetch_listed_tokens(exchange)
        if not listed:
            print(f"   ⚠️ {exchange}: tabela exchange_tokens vazia/inacessivel", flush=True)

        for token in tokens:
            symbol = token["symbol"]
            if symbol in listed:
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
        if save_candidate(candidate):
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

    for index, item in enumerate(SMART_MONEY_FUNDS):
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

        if index < len(SMART_MONEY_FUNDS) - 1:
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
