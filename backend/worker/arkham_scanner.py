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

TELEGRAM_BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN_ETH")
    or os.getenv("TELEGRAM_BOT_TOKEN_SOL")
    or os.getenv("TELEGRAM_BOT_TOKEN_1")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or ""
)
TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_CHAT_ID_ETH")
    or os.getenv("TELEGRAM_CHAT_ID_SOL")
    or os.getenv("TELEGRAM_CHAT_ID_1")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
)
EXCHANGE_MIN_SAVE_SCORE = int(os.getenv("ARKHAM_EXCHANGE_MIN_SAVE_SCORE", "50"))
SMART_MONEY_MIN_SAVE_SCORE = int(os.getenv("ARKHAM_SMART_MONEY_MIN_SAVE_SCORE", "25"))

LOW_SIGNAL_SYMBOLS = {
    "USDT", "USDT0", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDE", "USDS", "USD1",
    "USDTE", "BSC-USD", "USYC", "EUR", "EURC", "EURS", "PYUSD", "IDRT",
    "BTC", "WBTC", "BTCB", "CBBTC", "TBTC", "BBTC", "HBTC",
    "ETH", "WETH", "STETH", "WSTETH", "RETH", "CBETH", "BETH",
    "BNB", "WBNB", "SOL", "WSOL", "AVAX", "WAVAX", "MATIC", "WMATIC",
    "XAUT", "XAUT0", "PAXG",
}

STABLE_OR_FIAT_SYMBOLS = {
    "USDT", "USDT0", "USDC", "USDC.E", "BUSD", "DAI", "TUSD", "FDUSD", "USDE", "USDS",
    "USD1", "USDB", "USDX", "USDTE", "BSC-USD", "USYC", "PYUSD", "GUSD", "LUSD",
    "FRAX", "SUSD", "USDBC", "USDH",
    "EUR", "EURC", "EUROC", "EURI", "EURT", "EURQ", "EURS",
    "IDRT",
}

EXCLUDED_SYMBOLS = {
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD",
    "USD1", "USDB", "USDX", "BUSD", "GUSD", "LUSD", "FRAX", "SUSD",
    "EURC", "EUROC", "EURI", "EURT", "EURQ", "BSC-USD", "USYC",
    "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "RETH", "BETH",
    "CBBTC", "SPENDLE", "SENA", "BBTC", "BTCB", "PAXG", "XAUT",
    "BNB", "ETH", "BTC", "SOL", "XRP", "ADA", "DOGE", "TRX", "MATIC",
}
EXCLUDED_PREFIXES = ("W", "CB", "S", "BSC", "USD", "EUR")
EXCLUDED_SUFFIXES = ("BTC", "ETH", "SOL", "USD", "EUR", "USDT", "BNB")
MAX_SIGNAL_VALUE_USD = 500_000_000

CANDIDATE_WALLETS_TABLE = os.getenv("CANDIDATE_WALLETS_TABLE", "candidate_wallets")
INSIDER_MIN_VALUE_USD = float(os.getenv("ARKHAM_INSIDER_MIN_VALUE_USD", "25000"))
INSIDER_WALLET_LIMIT = int(os.getenv("ARKHAM_ACTIVITY_LIMIT", "100"))
TRANSFER_LOOKBACK_LIMIT = int(os.getenv("ARKHAM_ACTIVITY_TRANSFER_LIMIT", "25"))
REQUEST_TIMEOUT_ACTIVITY = int(os.getenv("ARKHAM_ACTIVITY_TIMEOUT", "45"))

LOW_SIGNAL_SMART_MONEY_SYMBOLS = STABLE_OR_FIAT_SYMBOLS | {
    # Tokenized funds / cash-like assets. Wrapped majors are intentionally not
    # here: for smart money, WETH/WBTC/WHYPE can be useful exposure signals.
    "BUIDL",
}

EXCHANGES = [
    {"slug": "binance", "exchange": "Binance"},
    {"slug": "coinbase", "exchange": "Coinbase"},
    {"slug": "gate-io", "exchange": "Gate.io"},
    {"slug": "kucoin", "exchange": "KuCoin"},
    {"slug": "okx", "exchange": "OKX"},
    {"slug": "bybit", "exchange": "Bybit"},
    {"slug": "kraken", "exchange": "Kraken"},
    {"slug": "bitget", "exchange": "Bitget"},
    {"slug": "mexc", "exchange": "MEXC"},
]

EXCHANGE_PROFILES = {
    "binance": {"tier": "major", "bonus": 5, "min_mcap": 20_000_000, "small_cap_penalty": 25},
    "coinbase": {"tier": "major", "bonus": 5, "min_mcap": 20_000_000, "small_cap_penalty": 25},
    "okx": {"tier": "large", "bonus": 3, "min_mcap": 5_000_000, "small_cap_penalty": 12},
    "bybit": {"tier": "large", "bonus": 3, "min_mcap": 5_000_000, "small_cap_penalty": 12},
    "gate.io": {"tier": "listing", "bonus": 3, "min_mcap": 1_000_000, "small_cap_penalty": 5},
    "gate": {"tier": "listing", "bonus": 3, "min_mcap": 1_000_000, "small_cap_penalty": 5},
    "kucoin": {"tier": "listing", "bonus": 3, "min_mcap": 1_000_000, "small_cap_penalty": 5},
    "kraken": {"tier": "listing", "bonus": 2, "min_mcap": 1_000_000, "small_cap_penalty": 5},
    "bitget": {"tier": "listing", "bonus": 2, "min_mcap": 1_000_000, "small_cap_penalty": 5},
    "mexc": {"tier": "listing", "bonus": 2, "min_mcap": 1_000_000, "small_cap_penalty": 5},
}

KNOWN_LISTED_BY_EXCHANGE = {
    # Safety net for Arkham entity portfolios when exchange_tokens is stale or
    # incomplete. Keep this conservative: only obvious already-listed assets.
    "binance": {
        "BABYDOGE", "BEAM", "BTT", "CAT", "CHEEMS", "EOS", "WNXM",
    },
}

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


def _parse_related_wallets(raw: str | None = None) -> list[dict[str, str]]:
    """Parse optional related wallets.

    Env format examples:
      ARKHAM_RELATED_WALLETS="Multicoin Capital|ethereum|0xabc|Multicoin related"
      ARKHAM_RELATED_WALLETS='[{"entity":"Multicoin Capital","chain":"ethereum","address":"0xabc"}]'
    """
    raw = (raw if raw is not None else os.getenv("ARKHAM_RELATED_WALLETS", "")).strip()
    if not raw:
        return []

    parsed: list[dict[str, str]] = []
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            value = [value]
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                entity = str(item.get("entity") or item.get("name") or "").strip()
                address = str(item.get("address") or item.get("wallet") or "").strip()
                chain = str(item.get("chain") or "").strip()
                label = str(item.get("label") or "").strip()
                if entity and address:
                    parsed.append({"entity": entity, "address": address, "chain": chain, "label": label})
            return parsed
    except Exception:
        pass

    for chunk in raw.split(";"):
        parts = [part.strip() for part in chunk.split("|")]
        if len(parts) < 3:
            continue
        entity, chain, address = parts[:3]
        label = parts[3] if len(parts) > 3 else ""
        if entity and address:
            parsed.append({"entity": entity, "address": address, "chain": chain, "label": label})
    return parsed


def _related_wallets_for(entity_name: str) -> list[dict[str, str]]:
    wanted = str(entity_name or "").strip().lower()
    return [
        wallet for wallet in _parse_related_wallets()
        if str(wallet.get("entity") or "").strip().lower() == wanted
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


def _fmt_val(v: Any) -> str:
    v = float(v or 0)
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


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


def _first_number(*values: Any) -> float:
    for value in values:
        number = _float_or_zero(value)
        if number > 0:
            return number
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
    market_cap_usd = _first_number(
        row.get("marketCap"),
        row.get("marketCapUsd"),
        row.get("market_cap"),
        row.get("market_cap_usd"),
        row.get("mcap"),
        row.get("mcapUsd"),
        row.get("fdv"),
        row.get("fdvUsd"),
        token_meta.get("marketCap"),
        token_meta.get("marketCapUsd"),
        token_meta.get("fdv"),
        token_meta.get("fdvUsd"),
    )
    liquidity_usd = _first_number(
        row.get("liquidity"),
        row.get("liquidityUsd"),
        row.get("liquidity_usd"),
        token_meta.get("liquidity"),
        token_meta.get("liquidityUsd"),
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
        "market_cap_usd": market_cap_usd,
        "liquidity_usd": liquidity_usd,
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


def fetch_arkham_address_portfolio(
    address: str,
    chain_hint: str | None = None,
    min_value_usd: float = SMART_MONEY_THRESHOLD_USD,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    payload = None
    for endpoint in (f"/balances/address/{address}", f"/portfolio/address/{address}"):
        try:
            payload = _arkham_get_json(endpoint)
            break
        except Exception as exc:
            errors.append(str(exc))

    if payload is None:
        raise RuntimeError(" | ".join(errors))

    raw_rows = _extract_token_rows(payload, chain_hint=chain_hint)
    tokens: list[dict[str, Any]] = []
    normalized_seen = 0
    for row in raw_rows:
        token = _normalize_token(row)
        if token:
            normalized_seen += 1
            if chain_hint and (not token.get("chain") or token.get("chain") == "unknown"):
                token["chain"] = _normalize_chain(chain_hint)
            if token["value_usd"] > min_value_usd:
                tokens.append(token)
    if not tokens:
        print(
            f"   Arkham address debug {address[:10]}...: raw_rows={len(raw_rows)} normalized={normalized_seen} "
            f"threshold=${min_value_usd:,.0f} {_payload_debug(payload)}",
            flush=True,
        )
    return tokens


def fetch_listed_tokens(exchange: str) -> set[str]:
    exchange_key = _normalize_symbol(exchange).replace(".", "").replace(" ", "").replace("-", "").lower()
    fallback = set(KNOWN_LISTED_BY_EXCHANGE.get(exchange_key, set()))
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
        return fallback
    return fallback | {_normalize_symbol(row.get("token")) for row in response.json() if row.get("token")}


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
    normalized = _normalize_symbol(symbol)
    candidates = listing_symbol_candidates(symbol)
    if candidates & LOW_SIGNAL_SYMBOLS:
        return True
    if any(part in normalized for part in ("-USD", "USD.", ".USD")):
        return True
    if normalized.endswith("0") and normalized[:-1] in LOW_SIGNAL_SYMBOLS:
        return True
    if listed and len(candidates) > 1 and any(candidate in listed for candidate in candidates if candidate != _normalize_symbol(symbol)):
        return True
    return False


def is_excluded_arkham_token(symbol: str, value_usd: float = 0) -> bool:
    normalized = _normalize_symbol(symbol)
    if not normalized:
        return True
    if normalized in EXCLUDED_SYMBOLS:
        return True
    if normalized.startswith(EXCLUDED_PREFIXES):
        return True
    if normalized.endswith(EXCLUDED_SUFFIXES):
        return True
    if value_usd > MAX_SIGNAL_VALUE_USD:
        return True
    return False


def is_excluded_smart_money_token(symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)
    if not normalized:
        return True
    if not normalized.isascii() or not normalized.replace("-", "").replace(".", "").isalnum():
        return True
    if len(normalized) <= 1:
        return True
    if normalized in LOW_SIGNAL_SMART_MONEY_SYMBOLS:
        return True
    if any(part in normalized for part in ("-USD", "USD.", ".USD")):
        return True
    if normalized.startswith(("USD", "EUR")):
        return True
    # Arkham can return tokenized stock/ETF tickers like NVDAON, TSLAON, QQQON.
    if normalized.endswith("ON") and len(normalized) > 4:
        return True
    return False


def is_listed_on_exchange(symbol: str, listed: set[str]) -> bool:
    return any(candidate in listed for candidate in listing_symbol_candidates(symbol))


def is_low_signal_smart_money_asset(symbol: str) -> bool:
    return is_excluded_smart_money_token(symbol)


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


def score_exchange_candidate(
    value_usd: float,
    exchange_count: int,
    exchange: str = "",
    market_cap_usd: float = 0,
    liquidity_usd: float = 0,
) -> int:
    mcap_pct = (value_usd / market_cap_usd * 100) if market_cap_usd > 0 else 0
    liquidity_pct = (value_usd / liquidity_usd * 100) if liquidity_usd > 0 else 0
    exchange_norm = str(exchange or "").strip().lower()
    profile = EXCHANGE_PROFILES.get(exchange_norm, {"bonus": 0, "min_mcap": 2_000_000, "small_cap_penalty": 8})

    if mcap_pct >= 10:
        score = 95
    elif mcap_pct >= 5:
        score = 90
    elif mcap_pct >= 2:
        score = 80
    elif mcap_pct >= 1:
        score = 70
    elif mcap_pct >= 0.5:
        score = 60
    elif mcap_pct >= 0.1:
        score = 50
    elif liquidity_pct >= 100:
        score = 70
    elif liquidity_pct >= 50:
        score = 60
    elif liquidity_pct >= 20:
        score = 50
    else:
        # Conservative fallback: absolute wallet value alone is a weak listing
        # signal without token-size context.
        if value_usd >= 25_000_000:
            score = 85
        elif value_usd >= 10_000_000:
            score = 75
        elif value_usd >= 5_000_000:
            score = 68
        elif value_usd >= 1_000_000:
            score = 55
        elif value_usd >= 500_000:
            score = 45
        elif value_usd >= 100_000:
            score = 35
        elif value_usd >= VALUE_THRESHOLD_USD:
            score = 25
        else:
            score = 0

    score += int(profile.get("bonus", 0))

    min_mcap = float(profile.get("min_mcap", 0) or 0)
    if market_cap_usd > 0 and min_mcap > 0 and market_cap_usd < min_mcap:
        score -= int(profile.get("small_cap_penalty", 0))

    if exchange_count >= 2:
        score += 8
    if exchange_count >= 3:
        score += 7

    return max(0, min(score, 100))


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


def candidate_signal_key(candidate: dict[str, Any], signal_type: str) -> str:
    token = candidate["token"]
    exchange = candidate["exchange"]
    chain = candidate["chain"]
    token_address = candidate.get("token_address") or f"arkham:{signal_type}:{exchange.lower()}:{chain}:{token}"
    return f"{signal_type}:{exchange.lower()}:{chain}:{token_address or token}".lower()


def signal_direction(
    current_value: float,
    previous_value: float,
    current_amount: float = 0.0,
    previous_amount: float = 0.0,
) -> str:
    # Entry/exit based on value (amount may be zero on first scan)
    if previous_value <= 0 and current_value > 0:
        return "new"
    if current_value <= 0 and previous_value > 0:
        return "removed_or_moved"

    # Prefer amount-based direction: price swings don't trigger false signals.
    # Fall back to value-based only when amounts are unavailable.
    if current_amount > 0 and previous_amount > 0:
        amount_threshold = max(previous_amount * 0.03, previous_amount * 0.001)
        amount_delta = current_amount - previous_amount
        if amount_delta >= amount_threshold:
            return "increased"
        if amount_delta <= -amount_threshold:
            return "decreased"
        return "flat"

    # Fallback: value-based (less reliable — price moves pollute the signal)
    delta = current_value - previous_value
    threshold = max(10_000, previous_value * 0.05)
    if delta >= threshold:
        return "increased"
    if delta <= -threshold:
        return "decreased"
    return "flat"


def fetch_existing_signals(entity: str, entity_type: str) -> dict[str, dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{ARKHAM_SIGNALS_TABLE}"
    params = {
        "select": "signal_key,token,chain,token_address,value_usd,amount,score,pair_url,exchange_count",
        "entity": f"eq.{entity}",
        "entity_type": f"eq.{entity_type}",
        "limit": "10000",
    }
    response = requests.get(url, params=params, headers=SUPABASE_HEADERS, timeout=20)
    if response.status_code >= 400:
        print(
            f"âš ï¸ Supabase existing {ARKHAM_SIGNALS_TABLE} falhou para {entity}: "
            f"HTTP {response.status_code} - {response.text[:200]}",
            flush=True,
        )
        return {}
    return {str(row.get("signal_key") or ""): row for row in response.json() if row.get("signal_key")}


def smart_money_score(value_usd: float, exchange_overlap_count: int = 0, direction: str = "new") -> int:
    score = score_candidate(value_usd, 1)
    if exchange_overlap_count >= 1:
        score += 25
    if exchange_overlap_count >= 3:
        score += 10
    if direction == "increased":
        score += 15
    elif direction == "new":
        score += 10
    elif direction in {"decreased", "removed_or_moved"}:
        score = max(20, score - 15)
    return max(0, min(score, 100))


def save_candidate(candidate: dict[str, Any], signal_type: str = "holding", previous: dict[str, Any] | None = None) -> bool:
    token = candidate["token"]
    exchange = candidate["exchange"]
    chain = candidate["chain"]
    # Arkham may not return token addresses for every chain; keep a stable
    # synthetic key so NOT NULL / legacy unique constraints do not break.
    token_address = candidate.get("token_address") or f"arkham:{signal_type}:{exchange.lower()}:{chain}:{token}"
    entity_type = "smart_money" if signal_type == "smart_money" else "exchange"
    signal_key = candidate_signal_key({**candidate, "token_address": token_address}, signal_type)
    previous = previous or {}
    previous_value = _float_or_zero(previous.get("value_usd"))
    previous_amount = _float_or_zero(previous.get("amount"))
    current_value = _float_or_zero(candidate.get("value_usd"))
    current_amount = _float_or_zero(candidate.get("amount"))
    value_delta = current_value - previous_value
    amount_delta = current_amount - previous_amount
    value_delta_pct = (value_delta / previous_value * 100) if previous_value > 0 else None
    direction = signal_direction(current_value, previous_value, current_amount, previous_amount)

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
        "value_usd": current_value,
        "previous_value_usd": previous_value,
        "value_delta_usd": value_delta,
        "value_delta_pct": value_delta_pct,
        "previous_amount": previous_amount,
        "amount_delta": amount_delta,
        "signal_direction": direction,
        "market_cap_usd": candidate.get("market_cap_usd") or 0,
        "liquidity_usd": candidate.get("liquidity_usd") or 0,
        "position_pct": candidate.get("position_pct") or 0,
        "liquidity_pct": candidate.get("liquidity_pct") or 0,
        "exchange_count": candidate.get("exchange_count", 1),
        "score": candidate["score"],
        "ts": now,
        "type": signal_type,
        "signature": f"arkham-{signal_type}-{exchange.lower()}-{chain}-{token}",
        "pair_url": f"https://dexscreener.com/search?q={token}",
        "analysis_text": (
            f"{token} detected in Arkham {exchange} entity portfolio. "
            f"Value: ${current_value:,.0f}. "
            f"Delta: ${value_delta:,.0f} ({direction}). "
            f"Position: {candidate.get('position_pct') or 0:.2f}% of market cap. "
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
            if is_excluded_arkham_token(symbol, token["value_usd"]):
                continue
            if is_low_signal_exchange_asset(symbol, listed) or is_listed_on_exchange(symbol, listed):
                continue

            exchange_count = len(token_exchanges[symbol])
            score = score_exchange_candidate(
                token["value_usd"],
                exchange_count,
                exchange=exchange,
                market_cap_usd=token.get("market_cap_usd", 0),
                liquidity_usd=token.get("liquidity_usd", 0),
            )
            if score < EXCHANGE_MIN_SAVE_SCORE:
                continue

            candidates.append({
                "exchange": exchange,
                "token": symbol,
                "chain": token["chain"],
                "amount": token["amount"],
                "value_usd": token["value_usd"],
                "market_cap_usd": token.get("market_cap_usd", 0),
                "liquidity_usd": token.get("liquidity_usd", 0),
                "position_pct": (
                    token["value_usd"] / token.get("market_cap_usd", 0) * 100
                    if token.get("market_cap_usd", 0) > 0 else 0
                ),
                "liquidity_pct": (
                    token["value_usd"] / token.get("liquidity_usd", 0) * 100
                    if token.get("liquidity_usd", 0) > 0 else 0
                ),
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
            if is_excluded_smart_money_token(symbol):
                continue

            exchange_count = len(token_exchanges.get(symbol, set()))
            score = score_candidate(token["value_usd"], 1)
            if exchange_count >= 1:
                score += 30
            score = min(score, 100)
            if score < SMART_MONEY_MIN_SAVE_SCORE:
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


def scan_smart_money_with_deltas(token_exchanges: dict[str, set[str]]) -> tuple[int, int]:
    print("ARKHAM SMART MONEY TRACKER — iniciado", flush=True)
    candidates: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    seen_slugs: set[str] = set()

    funds = _limit_entities(SMART_MONEY_FUNDS, "ARKHAM_SMART_MONEY_SLUGS")
    for index, item in enumerate(funds):
        slug = item["slug"]
        fund_name = item["name"]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        existing = fetch_existing_signals(fund_name, "smart_money")
        is_initial_snapshot = len(existing) == 0
        seen_keys: set[str] = set()

        try:
            print(f"Arkham portfolio: {fund_name} ({slug})", flush=True)
            tokens = fetch_arkham_portfolio(slug, SMART_MONEY_THRESHOLD_USD)
            print(f"   {len(tokens)} tokens acima de ${SMART_MONEY_THRESHOLD_USD:,.0f}", flush=True)
        except Exception as exc:
            print(f"   Arkham falhou para {fund_name}: {exc}", flush=True)
            tokens = []

        for token in tokens:
            symbol = token["symbol"]
            if is_excluded_smart_money_token(symbol):
                continue

            exchange_count = len(token_exchanges.get(symbol, set()))
            candidate = {
                "exchange": fund_name,
                "token": symbol,
                "chain": token["chain"],
                "amount": token["amount"],
                "value_usd": token["value_usd"],
                "token_address": token["token_address"],
                "exchange_count": max(exchange_count, 1),
                "score": 0,
            }
            key = candidate_signal_key(candidate, "smart_money")
            previous = existing.get(key)
            if previous is None and is_initial_snapshot:
                previous = {
                    "value_usd": candidate["value_usd"],
                    "amount": candidate["amount"],
                }
            previous_value = _float_or_zero((previous or {}).get("value_usd"))
            previous_amount = _float_or_zero((previous or {}).get("amount"))
            direction = signal_direction(candidate["value_usd"], previous_value, candidate["amount"], previous_amount)
            if direction == "flat":
                candidate["score"] = int(_float_or_zero((previous or {}).get("score")) or score_candidate(candidate["value_usd"], 1))
            else:
                candidate["score"] = smart_money_score(candidate["value_usd"], exchange_count, direction)
            if direction != "flat" and candidate["score"] < SMART_MONEY_MIN_SAVE_SCORE:
                continue

            seen_keys.add(key)
            candidates.append((candidate, previous))

        if not is_initial_snapshot:
            for key, previous in existing.items():
                if key in seen_keys:
                    continue
                symbol = str(previous.get("token") or "").strip().upper()
                previous_value = _float_or_zero(previous.get("value_usd"))
                if (
                    not symbol
                    or is_excluded_smart_money_token(symbol)
                ):
                    continue
                if previous_value < SMART_MONEY_THRESHOLD_USD:
                    continue

                overlap_count = int(previous.get("exchange_count") or 0)
                candidate = {
                    "exchange": fund_name,
                    "token": symbol,
                    "chain": previous.get("chain") or "unknown",
                    "amount": 0,
                    "value_usd": 0,
                    "token_address": previous.get("token_address") or "",
                    "exchange_count": max(overlap_count, 1),
                    "score": smart_money_score(0, overlap_count, "removed_or_moved"),
                }
                candidates.append((candidate, previous))

        for wallet in _related_wallets_for(fund_name):
            address = wallet.get("address") or ""
            source_name = wallet.get("label") or f"{fund_name} related"
            source_chain = wallet.get("chain") or ""
            if not address:
                continue

            related_existing = fetch_existing_signals(source_name, "smart_money")
            related_initial_snapshot = len(related_existing) == 0

            try:
                print(f"Arkham related wallet: {source_name} ({address[:10]}...)", flush=True)
                related_tokens = fetch_arkham_address_portfolio(address, source_chain, SMART_MONEY_THRESHOLD_USD)
                print(f"   {len(related_tokens)} related-wallet tokens acima de ${SMART_MONEY_THRESHOLD_USD:,.0f}", flush=True)
            except Exception as exc:
                print(f"   Arkham related wallet falhou para {source_name}: {exc}", flush=True)
                related_tokens = []

            for token in related_tokens:
                symbol = token["symbol"]
                if is_excluded_smart_money_token(symbol):
                    continue

                exchange_count = len(token_exchanges.get(symbol, set()))
                candidate = {
                    "exchange": source_name,
                    "token": symbol,
                    "chain": token["chain"],
                    "amount": token["amount"],
                    "value_usd": token["value_usd"],
                    "token_address": token["token_address"],
                    "exchange_count": max(exchange_count, 1),
                    "score": 0,
                }
                key = candidate_signal_key(candidate, "smart_money")
                previous = related_existing.get(key)
                if previous is None and related_initial_snapshot:
                    previous = {
                        "value_usd": candidate["value_usd"],
                        "amount": candidate["amount"],
                    }
                previous_value = _float_or_zero((previous or {}).get("value_usd"))
                previous_amount = _float_or_zero((previous or {}).get("amount"))
                direction = signal_direction(candidate["value_usd"], previous_value, candidate["amount"], previous_amount)
                if direction == "flat":
                    candidate["score"] = int(_float_or_zero((previous or {}).get("score")) or score_candidate(candidate["value_usd"], 1))
                else:
                    candidate["score"] = smart_money_score(candidate["value_usd"], exchange_count, direction)
                if direction != "flat" and candidate["score"] < SMART_MONEY_MIN_SAVE_SCORE:
                    continue
                candidates.append((candidate, previous))

        if index < len(funds) - 1:
            time.sleep(1.1)

    saved = 0
    for candidate, previous in sorted(candidates, key=lambda item: item[0]["score"], reverse=True):
        previous_value = _float_or_zero((previous or {}).get("value_usd"))
        direction = signal_direction(_float_or_zero(candidate.get("value_usd")), previous_value)
        if save_candidate(candidate, signal_type="smart_money", previous=previous):
            saved += 1
            print(
                f"smart_money {direction} {candidate['token']} · {candidate['exchange']} · "
                f"${candidate['value_usd']:,.0f} · score {candidate['score']}",
                flush=True,
            )

    print(f"Smart money: {len(candidates)} sinais/deltas; {saved} guardados.", flush=True)
    return len(candidates), saved, candidates


def send_daily_telegram_report(sm_candidates: list, insider_alerts: list[dict]) -> None:
    """Combined narrative report: smart money moves + insider activity."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    direction_order = {"new": 0, "increased": 1, "decreased": 2, "removed_or_moved": 3, "flat": 4}
    enriched = []
    for candidate, previous in sm_candidates:
        prev_val = _float_or_zero((previous or {}).get("value_usd"))
        prev_amt = _float_or_zero((previous or {}).get("amount"))
        direction = signal_direction(
            _float_or_zero(candidate.get("value_usd")),
            prev_val,
            _float_or_zero(candidate.get("amount")),
            prev_amt,
        )
        enriched.append((candidate, previous, direction))

    active_sm = [(c, p, d) for c, p, d in enriched if d in ("new", "increased", "decreased", "removed_or_moved")]
    active_sm.sort(key=lambda x: (direction_order.get(x[2], 9), -float(x[0].get("score") or 0)))

    lines = ["*📡 Vigia Crypto — Resumo Diário*", ""]

    if active_sm:
        lines.append("*🐋 Market Makers & Smart Money*")
        lines.append("")
        for candidate, previous, direction in active_sm[:8]:
            token = candidate.get("token", "?")
            fund = candidate.get("exchange", "?")
            val = _fmt_val(candidate.get("value_usd", 0))
            prev_val_num = _float_or_zero((previous or {}).get("value_usd"))
            if direction == "new":
                lines.append(f"🆕 *{fund}* entrou em *{token}* com {val}")
            elif direction == "increased":
                delta = _fmt_val(float(candidate.get("value_usd", 0)) - prev_val_num)
                lines.append(f"📈 *{fund}* aumentou *{token}* (+{delta}, total {val})")
            elif direction == "decreased":
                delta = _fmt_val(prev_val_num - float(candidate.get("value_usd", 0)))
                lines.append(f"📉 *{fund}* reduziu *{token}* (-{delta}, total {val})")
            elif direction == "removed_or_moved":
                lines.append(f"🚪 *{fund}* saiu de *{token}* ({_fmt_val(prev_val_num)})")

    if insider_alerts:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("*🕵️ Insiders*")
        lines.append("")
        for alert in insider_alerts[:6]:
            entity = str(alert.get("entity") or "").replace("insider:", "")
            token = alert.get("token") or "token"
            val = _fmt_val(float(alert.get("value_usd") or 0))
            flow = alert.get("flow", "?")
            cp = alert.get("counterparty_label") or ""
            if flow == "out":
                line = f"📤 *{entity}* enviou {val} *{token}*"
                if cp:
                    line += f" → {cp}"
            else:
                line = f"📥 *{entity}* recebeu {val} *{token}*"
                if cp:
                    line += f" de {cp}"
            lines.append(line)

    if len(lines) <= 2:
        return

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=10)
        if r.status_code == 200:
            print("Telegram daily report enviado.", flush=True)
        else:
            print(f"Telegram Markdown falhou ({r.status_code}: {r.text[:200]}), a tentar sem parse_mode...", flush=True)
            plain = text.replace("*", "").replace("_", "").replace("`", "")
            r2 = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": plain, "disable_web_page_preview": True}, timeout=10)
            if r2.status_code == 200:
                print("Telegram daily report enviado (plain text).", flush=True)
            else:
                print(f"Telegram plain também falhou: {r2.status_code} {r2.text[:200]}", flush=True)
    except Exception as exc:
        print(f"Telegram daily report excepção: {exc}", flush=True)


def _parse_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_transfer_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("transfers", "items", "data", "results"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
    return []


def _entity_name(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    entity = value.get("arkhamEntity") if isinstance(value.get("arkhamEntity"), dict) else {}
    predicted = value.get("predictedEntity") if isinstance(value.get("predictedEntity"), dict) else {}
    label = value.get("arkhamLabel") if isinstance(value.get("arkhamLabel"), dict) else {}
    return str(entity.get("name") or predicted.get("name") or label.get("name") or "").strip()


def _addr_str(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("address") or "").strip()
    return str(value or "").strip()


def _is_new_activity(row: dict[str, Any], activity: dict[str, Any]) -> bool:
    prev_ts = _parse_ts(row.get("last_activity_ts"))
    new_ts = _parse_ts(activity.get("timestamp"))
    if not new_ts:
        return False
    if not prev_ts:
        return True
    return new_ts > prev_ts


def fetch_candidate_wallets() -> list[dict[str, Any]]:
    params = {
        "select": "id,entity,address,chain,score,balance_usd,classification,source,last_activity_ts,raw",
        "order": "score.desc,balance_usd.desc",
        "limit": str(INSIDER_WALLET_LIMIT),
    }
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/{CANDIDATE_WALLETS_TABLE}",
        headers=SUPABASE_HEADERS,
        params=params,
        timeout=30,
    )
    if response.status_code >= 400:
        print(f"candidate_wallets fetch falhou: HTTP {response.status_code}", flush=True)
        return []
    return response.json()


def latest_activity_for_wallet(address: str, min_value_usd: float) -> dict[str, Any] | None:
    candidates = []
    for flow in ("out", "in"):
        try:
            response = requests.get(
                f"{ARKHAM_BASE_URL}/transfers",
                headers=ARKHAM_HEADERS,
                params={"base": address, "flow": flow, "limit": TRANSFER_LOOKBACK_LIMIT},
                timeout=REQUEST_TIMEOUT_ACTIVITY,
            )
        except Exception:
            time.sleep(1.05)
            continue
        if response.status_code >= 400:
            time.sleep(1.05)
            continue
        rows = _extract_transfer_rows(response.json() if response.content else {})
        for row in rows:
            value_usd = _float_or_zero(row.get("historicalUSD") or row.get("usdValue") or row.get("valueUsd") or 0)
            if value_usd >= min_value_usd:
                ts = _parse_ts(row.get("blockTimestamp"))
                from_obj = row.get("fromAddress")
                to_obj = row.get("toAddress")
                candidates.append({
                    "flow": flow,
                    "timestamp": ts.isoformat() if ts else str(row.get("blockTimestamp") or ""),
                    "timestamp_dt": ts,
                    "token": str(row.get("tokenSymbol") or row.get("tokenName") or "").strip(),
                    "value_usd": value_usd,
                    "tx": row.get("transactionHash"),
                    "chain": row.get("chain"),
                    "from": _addr_str(from_obj),
                    "to": _addr_str(to_obj),
                    "from_label": _entity_name(from_obj),
                    "to_label": _entity_name(to_obj),
                })
                break
        time.sleep(1.05)
    if not candidates:
        return None
    candidates.sort(
        key=lambda r: r.get("timestamp_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    result = candidates[0].copy()
    result.pop("timestamp_dt", None)
    return result


def save_wallet_activity(wallet_row: dict[str, Any], activity: dict[str, Any]) -> bool:
    raw = wallet_row.get("raw") if isinstance(wallet_row.get("raw"), dict) else {}
    raw = {**raw, "last_activity": activity, "last_activity_checked_at": datetime.now(timezone.utc).isoformat()}
    flow = activity.get("flow")
    counterparty = activity.get("to") if flow == "out" else activity.get("from")
    counterparty_label = activity.get("to_label") if flow == "out" else activity.get("from_label")
    payload = {
        "last_activity_ts": activity.get("timestamp") or None,
        "last_activity_value_usd": activity.get("value_usd") or 0,
        "last_activity_flow": flow or None,
        "last_activity_token": activity.get("token") or None,
        "last_activity_chain": activity.get("chain") or None,
        "last_activity_counterparty": counterparty or None,
        "last_activity_counterparty_label": counterparty_label or None,
        "last_activity_tx": activity.get("tx") or None,
        "activity_checked_at": datetime.now(timezone.utc).isoformat(),
        "raw": raw,
    }
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{CANDIDATE_WALLETS_TABLE}",
        headers={**SUPABASE_HEADERS, "Prefer": "return=minimal"},
        params={"id": f"eq.{wallet_row['id']}"},
        data=json.dumps(payload),
        timeout=30,
    )
    return response.status_code in (200, 204)


def _insider_score(value_usd: float, wallet_score: int = 0) -> int:
    if value_usd >= 5_000_000:
        base = 97
    elif value_usd >= 1_000_000:
        base = 92
    elif value_usd >= 500_000:
        base = 87
    elif value_usd >= 100_000:
        base = 82
    else:
        base = 75
    return max(base, wallet_score)


def save_insider_signal_to_arkham(wallet_row: dict[str, Any], activity: dict[str, Any]) -> None:
    flow = activity.get("flow", "?")
    value_usd = float(activity.get("value_usd") or 0)
    entity = str(wallet_row.get("entity") or "")
    token = activity.get("token") or ""
    chain = activity.get("chain") or wallet_row.get("chain") or ""
    counterparty = activity.get("to_label") if flow == "out" else activity.get("from_label")
    signal_key = f"insider:{str(wallet_row.get('address',''))[:12]}:{token}:{(activity.get('timestamp') or '')[:10]}"
    payload = {
        "signal_key": signal_key,
        "entity": entity,
        "entity_type": "insider",
        "exchange": counterparty or "",
        "token": token,
        "token_address": f"insider:{str(wallet_row.get('address',''))[:20]}",
        "chain": chain,
        "amount": float(activity.get("amount") or 0),
        "value_usd": value_usd,
        "previous_value_usd": 0,
        "value_delta_usd": value_usd,
        "signal_direction": "new" if flow == "in" else "decreased",
        "exchange_count": 1,
        "score": _insider_score(value_usd, int(wallet_row.get("score") or 0)),
        "ts": activity.get("timestamp"),
        "type": "insider",
        "signature": signal_key,
        "pair_url": f"https://dexscreener.com/search?q={token}",
        "analysis_text": f"Insider {entity.replace('insider:', '')} · {_fmt_val(value_usd)} {token} {flow}",
    }
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/{ARKHAM_SIGNALS_TABLE}",
            headers={**SUPABASE_HEADERS, "Prefer": "resolution=ignore-duplicates,return=minimal"},
            data=json.dumps(payload),
            timeout=15,
        )
        if response.status_code not in (200, 201, 204):
            print(f"  arkham_signals insider insert falhou HTTP {response.status_code}", flush=True)
    except Exception as exc:
        print(f"  arkham_signals insider insert falhou: {exc}", flush=True)


def scan_insider_wallets() -> list[dict[str, Any]]:
    """Check latest Arkham activity for prelisting insider wallets. Returns list of new alerts."""
    wallets = fetch_candidate_wallets()
    insiders = [w for w in wallets if str(w.get("source") or "").startswith("prelisting")]
    if not insiders:
        print("Insider wallets: nenhuma encontrada.", flush=True)
        return []

    print(f"INSIDERS — {len(insiders)} wallets a verificar (min ${INSIDER_MIN_VALUE_USD:,.0f})", flush=True)
    alerts: list[dict[str, Any]] = []
    for index, row in enumerate(insiders, 1):
        address = str(row.get("address") or "").strip()
        if not address:
            continue
        activity = latest_activity_for_wallet(address, INSIDER_MIN_VALUE_USD)
        if not activity:
            print(f"[{index}/{len(insiders)}] {address[:12]}... sem actividade >= ${INSIDER_MIN_VALUE_USD:,.0f}", flush=True)
            continue
        is_new = _is_new_activity(row, activity)
        entity = str(row.get("entity") or "")
        label = activity.get("to_label") if activity.get("flow") == "out" else activity.get("from_label")
        computed_score = _insider_score(float(activity.get("value_usd") or 0), int(row.get("score") or 0))
        print(
            f"[{index}/{len(insiders)}] {entity} {address[:12]}...{'[NEW]' if is_new else ''} "
            f"{activity['flow']} {activity.get('token') or 'token'} {_fmt_val(activity.get('value_usd', 0))} "
            f"score {computed_score}{(' → ' + label) if label else ''}",
            flush=True,
        )
        save_wallet_activity(row, activity)
        if is_new:
            save_insider_signal_to_arkham(row, activity)
            alerts.append({
                "entity": entity,
                "token": activity.get("token") or "",
                "value_usd": activity.get("value_usd") or 0,
                "flow": activity.get("flow") or "",
                "counterparty_label": (activity.get("to_label") if activity.get("flow") == "out" else activity.get("from_label")) or "",
                "chain": activity.get("chain") or row.get("chain") or "",
            })

    print(f"Insiders: {len(insiders)} verificadas, {len(alerts)} novos alertas.", flush=True)
    return alerts


def main() -> None:
    _require_env()
    print("🔎 ARKHAM EXCHANGE SCANNER — iniciado", flush=True)
    start = time.time()

    token_exchanges, exchange_candidates, exchange_saved = scan_exchange_candidates()
    smart_candidates, smart_saved, raw_candidates = scan_smart_money_with_deltas(token_exchanges)
    insider_alerts = scan_insider_wallets()
    send_daily_telegram_report(raw_candidates, insider_alerts)

    print(
        f"🏁 Arkham concluido: exchange={exchange_candidates}/{exchange_saved}, "
        f"smart_money={smart_candidates}/{smart_saved}, insiders={len(insider_alerts)} alertas. "
        f"Duracao total: {round(time.time() - start, 1)}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
