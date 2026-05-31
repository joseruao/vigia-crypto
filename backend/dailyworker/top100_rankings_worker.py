import math
import time
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Any

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from analisegrafica.coin_analysis import AdvancedCoinAnalyzer


TOP100_TABLE = "top100_technical_rankings"
TOP100_EXCLUDED_SYMBOLS = {
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD",
    "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "RETH", "BETH",
}


def _num(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _risk_label(rank: int, volume_ratio: float, change_7d: float, change_30d: float) -> str:
    if rank <= 20 and volume_ratio >= 0.04 and abs(change_7d) < 18:
        return "BAIXO/MODERADO"
    if volume_ratio < 0.015 or abs(change_7d) > 35 or abs(change_30d) > 80:
        return "ELEVADO"
    if volume_ratio < 0.03 or abs(change_7d) > 22:
        return "MODERADO/ELEVADO"
    return "MODERADO"


def _score_coin(item: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(item.get("symbol") or "").upper().strip()
    rank = int(item.get("market_cap_rank") or 999)
    market_cap = _num(item.get("market_cap"))
    volume = _num(item.get("total_volume"))
    change_24h = _num(item.get("price_change_percentage_24h"))
    change_7d = _num(item.get("price_change_percentage_7d_in_currency"))
    change_30d = _num(item.get("price_change_percentage_30d_in_currency"))
    volume_ratio = volume / market_cap if market_cap > 0 else 0.0

    score = 42.0

    # Preferimos setups analisaveis: tendencia positiva, mas sem perseguir pumps extremos.
    if 5 <= change_30d <= 65:
        score += 14
    elif change_30d > 65:
        score += 4
    elif change_30d < -20:
        score -= 10
    else:
        score += max(min(change_30d * 0.25, 8), -6)

    if -8 <= change_7d <= 18:
        score += 13
    elif 18 < change_7d <= 35:
        score += 5
    elif change_7d > 35:
        score -= 8
    else:
        score += max(min(change_7d * 0.5, 6), -10)

    if -5 <= change_24h <= 7:
        score += 6
    elif change_24h > 12:
        score -= 4
    elif change_24h < -10:
        score -= 6

    score += min(math.log10(volume_ratio * 1000 + 1) * 8, 16)

    if rank <= 10:
        score += 1
    elif rank <= 50:
        score += 3
    elif rank <= 100:
        score += 1

    if symbol in TOP100_EXCLUDED_SYMBOLS:
        score = 0
    if change_7d > 30 or change_30d > 90:
        score -= 8
    if change_24h < -8 and change_7d < -12:
        score -= 8

    score = round(min(max(score, 0), 100), 1)
    risk = _risk_label(rank, volume_ratio, change_7d, change_30d)

    if score >= 75:
        signal = "FORTE"
    elif score >= 65:
        signal = "BOA"
    elif score >= 55:
        signal = "OBSERVAR"
    else:
        signal = "FRACA"

    reasons = []
    if change_30d > 0 and -8 <= change_7d <= 12:
        reasons.append("tendencia 30d com pullback/controlada")
    elif change_7d > 0:
        reasons.append(f"momentum 7d {change_7d:.1f}%")
    if change_30d > 0:
        reasons.append(f"forca 30d {change_30d:.1f}%")
    if volume_ratio >= 0.05:
        reasons.append("volume forte vs market cap")
    if change_7d > 30:
        reasons.append("preco esticado")
    if not reasons:
        reasons.append("sinais mistos")

    return {
        "score": score,
        "risk": risk,
        "signal": signal,
        "volume_ratio": round(volume_ratio, 5),
        "rationale": ", ".join(reasons[:3]),
    }


def _technical_score(technical: Dict[str, Any] | None, fallback_score: float) -> float:
    if not technical:
        return fallback_score

    score = 35.0
    rsi = _num(technical.get("rsi"), 50)
    position = _num(technical.get("current_position"), 50)
    trend = str(technical.get("trend") or "")
    volume_ratio = _num(technical.get("volume_ratio_20d"), 1)

    if 28 <= rsi <= 48:
        score += 24
    elif 48 < rsi <= 62:
        score += 14
    elif rsi < 28:
        score += 10
    elif rsi >= 70:
        score -= 16

    if 8 <= position <= 45:
        score += 22
    elif 45 < position <= 65:
        score += 10
    elif position > 75:
        score -= 14

    if trend == "UPTREND":
        score += 14
    else:
        score -= 4

    if volume_ratio >= 1.2:
        score += 8
    elif volume_ratio < 0.4:
        score -= 3

    score = score * 0.72 + fallback_score * 0.28
    return round(min(max(score, 0), 100), 1)


def _technical_signal(score: float, rsi: float | None, position: float | None) -> str:
    if rsi is not None and rsi >= 72:
        return "AGUARDAR"
    if position is not None and position >= 78:
        return "AGUARDAR"
    if score >= 78:
        return "FORTE"
    if score >= 65:
        return "BOA"
    if score >= 52:
        return "OBSERVAR"
    return "FRACA"


def _technical_summary(symbol: str, technical: Dict[str, Any] | None, fallback: Dict[str, Any]) -> str:
    if not technical:
        return fallback["rationale"]

    rsi = technical.get("rsi")
    trend = technical.get("trend")
    position = technical.get("current_position")
    support = technical.get("support")
    resistance = technical.get("resistance")
    parts = []

    if trend:
        parts.append(f"tendencia {trend.lower()}")
    if rsi is not None:
        if rsi < 30:
            parts.append(f"RSI oversold ({rsi})")
        elif rsi > 70:
            parts.append(f"RSI alto ({rsi})")
        else:
            parts.append(f"RSI controlado ({rsi})")
    if position is not None:
        if position <= 45:
            parts.append("perto da metade inferior do range")
        elif position >= 75:
            parts.append("esticada perto da resistencia")
        else:
            parts.append("zona intermedia do range")
    if support and resistance:
        parts.append(f"suporte {support}, resistencia {resistance}")

    return f"{symbol}: " + "; ".join(parts[:4])


async def _analyze_symbol_technical(symbol: str, analyzer: AdvancedCoinAnalyzer, semaphore: asyncio.Semaphore) -> Dict[str, Any] | None:
    async with semaphore:
        try:
            result = await analyzer.analyze_coin(symbol, "60d")
            if not result or result.get("error") or result.get("snapshot_only"):
                return None

            analysis = result.get("analysis") or {}
            sr = analysis.get("support_resistance") or {}
            trend = analysis.get("trend") or {}
            volume = analysis.get("volume") or {}
            recs = result.get("recommendations") or {}
            strategy = recs.get("estrategia_trading") or {}
            targets = strategy.get("targets") or []

            return {
                "rsi": analysis.get("rsi"),
                "trend": trend.get("direction"),
                "trend_strength": trend.get("strength"),
                "volatility": analysis.get("volatility"),
                "volume_ratio_20d": volume.get("ratio_20d"),
                "support": sr.get("dynamic_support"),
                "resistance": sr.get("dynamic_resistance"),
                "current_position": sr.get("current_position"),
                "entry_zone": (result.get("trading_zones") or {}).get("posicao_atual"),
                "stop_loss": strategy.get("stop_loss"),
                "targets": targets[:3],
                "technical_action": recs.get("acao_principal"),
                "technical_confidence": recs.get("confianca"),
            }
        except Exception as e:
            print(f"Top100 tecnico falhou para {symbol}: {e}", flush=True)
            return None


async def enrich_rows_with_technical(rows: List[Dict[str, Any]], max_symbols: int = 100) -> List[Dict[str, Any]]:
    analyzer = AdvancedCoinAnalyzer()
    semaphore = asyncio.Semaphore(4)
    symbols = [row["symbol"] for row in rows[:max_symbols]]
    results = await asyncio.gather(
        *[_analyze_symbol_technical(symbol, analyzer, semaphore) for symbol in symbols],
        return_exceptions=False,
    )
    technical_by_symbol = dict(zip(symbols, results))

    enriched = []
    for row in rows:
        technical = technical_by_symbol.get(row["symbol"])
        updated = dict(row)
        if technical:
            updated.update({
                "rsi": technical.get("rsi"),
                "trend": technical.get("trend"),
                "trend_strength": technical.get("trend_strength"),
                "volatility": technical.get("volatility"),
                "volume_ratio_20d": technical.get("volume_ratio_20d"),
                "support": technical.get("support"),
                "resistance": technical.get("resistance"),
                "current_position": technical.get("current_position"),
                "entry_zone": technical.get("entry_zone"),
                "stop_loss": technical.get("stop_loss"),
                "targets": technical.get("targets") or [],
                "technical_action": technical.get("technical_action"),
                "technical_confidence": technical.get("technical_confidence"),
            })

        updated["score"] = _technical_score(technical, _num(row.get("score")))
        rsi = _num(technical.get("rsi"), None) if technical else None
        position = _num(technical.get("current_position"), None) if technical else None
        updated["signal"] = _technical_signal(updated["score"], rsi, position)
        updated["rationale"] = _technical_summary(row["symbol"], technical, {
            "rationale": row.get("rationale") or "sinais mistos",
        })
        enriched.append(updated)

    enriched.sort(key=lambda row: (row["score"], -row["rank"]), reverse=True)
    return enriched


def fetch_top100_market_data() -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h,7d,30d",
            },
            timeout=30,
        )
        response.raise_for_status()
        print("Top100 obtido via CoinGecko", flush=True)
        return response.json() or []
    except Exception as e:
        print(f"CoinGecko indisponivel para top100: {e}. A tentar CoinPaprika...", flush=True)
        return fetch_top100_market_data_coinpaprika()


def fetch_top100_market_data_coinpaprika() -> List[Dict[str, Any]]:
    response = requests.get("https://api.coinpaprika.com/v1/tickers", timeout=30)
    response.raise_for_status()
    rows = []
    for item in (response.json() or [])[:100]:
        quote = (item.get("quotes") or {}).get("USD") or {}
        rows.append({
            "id": item.get("id"),
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "market_cap_rank": item.get("rank"),
            "current_price": quote.get("price"),
            "market_cap": quote.get("market_cap"),
            "total_volume": quote.get("volume_24h"),
            "price_change_percentage_24h": quote.get("percent_change_24h"),
            "price_change_percentage_7d_in_currency": quote.get("percent_change_7d"),
            "price_change_percentage_30d_in_currency": quote.get("percent_change_30d"),
        })
    print(f"Top100 obtido via CoinPaprika: {len(rows)} moedas", flush=True)
    return rows


def build_top100_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    rows_by_symbol = {}
    for item in items:
        symbol = str(item.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        if symbol in TOP100_EXCLUDED_SYMBOLS:
            continue

        computed = _score_coin(item)
        row = {
            "date": today,
            "rank": int(item.get("market_cap_rank") or 999),
            "coin_id": item.get("id"),
            "symbol": symbol,
            "name": item.get("name"),
            "price": item.get("current_price"),
            "market_cap": item.get("market_cap"),
            "volume_24h": item.get("total_volume"),
            "change_24h": item.get("price_change_percentage_24h"),
            "change_7d": item.get("price_change_percentage_7d_in_currency"),
            "change_30d": item.get("price_change_percentage_30d_in_currency"),
            "volume_ratio": computed["volume_ratio"],
            "score": computed["score"],
            "risk": computed["risk"],
            "signal": computed["signal"],
            "rationale": computed["rationale"],
            "ts": now,
        }
        existing = rows_by_symbol.get(symbol)
        if not existing or row["rank"] < existing["rank"]:
            rows_by_symbol[symbol] = row

    rows = list(rows_by_symbol.values())
    rows.sort(key=lambda row: (row["score"], -row["rank"]), reverse=True)
    return rows


async def update_top100_rankings(
    upsert_func: Callable[[str, Dict[str, Any], List[str]], bool],
    bulk_upsert_func: Callable[[str, List[Dict[str, Any]], List[str]], int] | None = None,
) -> int:
    print("🔎 ATUALIZANDO RANKING TECNICO TOP100...")
    items = fetch_top100_market_data()
    rows = build_top100_rows(items)
    rows = await enrich_rows_with_technical(rows, max_symbols=100)

    if bulk_upsert_func:
        saved = bulk_upsert_func(TOP100_TABLE, rows, ["date", "symbol"])
        if saved == 0 and rows and any("rsi" in row for row in rows):
            legacy_rows = [
                {
                    key: value
                    for key, value in row.items()
                    if key not in {
                        "rsi", "trend", "trend_strength", "volatility", "volume_ratio_20d",
                        "support", "resistance", "current_position", "entry_zone", "stop_loss",
                        "targets", "technical_action", "technical_confidence",
                    }
                }
                for row in rows
            ]
            print("Top100 tecnico: retry sem colunas novas para manter compatibilidade Supabase", flush=True)
            saved = bulk_upsert_func(TOP100_TABLE, legacy_rows, ["date", "symbol"])
        print(f"Top100 atualizado em lote: {saved}/{len(rows)} moedas guardadas", flush=True)
        return saved

    saved = 0
    for row in rows:
        if upsert_func(TOP100_TABLE, row, ["date", "symbol"]):
            saved += 1
        time.sleep(0.05)

    print(f"✅ Top100 atualizado: {saved}/{len(rows)} moedas guardadas")
    return saved
