import math
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Callable, Dict, List, Any

import requests


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
    macd_sig = str(technical.get("macd_signal") or "NEUTRO")
    bb_pos = str(technical.get("bb_position") or "NEUTRO")
    above_200 = technical.get("above_sma200")

    # RSI (Wilder) — peso alto
    if 28 <= rsi <= 48:
        score += 22
    elif 48 < rsi <= 62:
        score += 12
    elif rsi < 28:
        score += 8   # oversold extremo pode ser queda livre
    elif rsi >= 70:
        score -= 16

    # Posição no range suporte/resistência
    if 8 <= position <= 35:
        score += 20
    elif 35 < position <= 55:
        score += 10
    elif position > 75:
        score -= 14

    # Tendência SMA20/50 + confirmação SMA200
    if trend == "UPTREND":
        score += 12
        if above_200 is True:
            score += 4   # bónus: macro alinhado
    else:
        score -= 4
        if above_200 is False:
            score -= 3   # penalidade extra: macro também bearish

    # MACD
    if macd_sig == "BULLISH_STRONG":
        score += 10
    elif macd_sig == "BULLISH":
        score += 6
    elif macd_sig == "BEARISH_STRONG":
        score -= 10
    elif macd_sig == "BEARISH":
        score -= 5

    # Bollinger Bands
    if bb_pos == "ZONA_BAIXA":
        score += 6   # perto da banda inferior = possível bounce
    elif bb_pos == "ABAIXO_BANDA":
        score += 3   # abaixo da banda = oversold mas pode continuar
    elif bb_pos == "ACIMA_BANDA":
        score -= 8
    elif bb_pos == "ZONA_ALTA":
        score -= 4

    # Volume
    if volume_ratio >= 1.2:
        score += 6
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
    macd_sig = technical.get("macd_signal")
    bb_pos = technical.get("bb_position")
    above_200 = technical.get("above_sma200")
    parts = []

    if trend:
        macro = " (acima SMA200)" if above_200 is True else (" (abaixo SMA200)" if above_200 is False else "")
        parts.append(f"tendencia {trend.lower()}{macro}")
    if rsi is not None:
        if rsi < 30:
            parts.append(f"RSI oversold ({rsi})")
        elif rsi > 70:
            parts.append(f"RSI alto ({rsi})")
        else:
            parts.append(f"RSI {rsi}")
    if macd_sig and macd_sig != "NEUTRO":
        parts.append(f"MACD {macd_sig.lower().replace('_', ' ')}")
    if bb_pos and bb_pos not in ("NEUTRO",):
        parts.append(f"BB {bb_pos.lower().replace('_', ' ')}")
    if position is not None:
        if position <= 35:
            parts.append("zona de compra")
        elif position >= 75:
            parts.append("esticada perto da resistencia")
    if support and resistance:
        parts.append(f"sup {support:g} / res {resistance:g}")

    return f"{symbol}: " + "; ".join(parts[:5])


def _fetch_coinbase_candles(symbol: str, days: int = 210) -> List[Dict[str, float]] | None:
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        response = requests.get(
            f"https://api.exchange.coinbase.com/products/{symbol}-USD/candles",
            params={"granularity": 86400, "start": start.isoformat(), "end": end.isoformat()},
            timeout=12,
        )
        response.raise_for_status()
        candles = [
            {"ts": row[0], "low": float(row[1]), "high": float(row[2]), "open": float(row[3]), "close": float(row[4]), "volume": float(row[5])}
            for row in response.json() or []
        ]
        candles.sort(key=lambda row: row["ts"])
        return candles if len(candles) >= 20 else None
    except Exception:
        return None


def _fetch_gateio_candles(symbol: str, days: int = 210) -> List[Dict[str, float]] | None:
    try:
        response = requests.get(
            "https://api.gateio.ws/api/v4/spot/candlesticks",
            params={"currency_pair": f"{symbol}_USDT", "interval": "1d", "limit": days},
            timeout=12,
        )
        response.raise_for_status()
        candles = [
            {"ts": int(row[0]), "volume": float(row[1]), "close": float(row[2]), "high": float(row[3]), "low": float(row[4]), "open": float(row[5])}
            for row in response.json() or []
        ]
        candles.sort(key=lambda row: row["ts"])
        return candles if len(candles) >= 20 else None
    except Exception:
        return None


def _fetch_binance_candles(symbol: str, days: int = 210) -> List[Dict[str, float]] | None:
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": f"{symbol}USDT", "interval": "1d", "limit": days},
            timeout=12,
        )
        response.raise_for_status()
        candles = [
            {"ts": row[0] / 1000, "open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4]), "volume": float(row[5])}
            for row in response.json() or []
        ]
        return candles if len(candles) >= 20 else None
    except Exception:
        return None


def _fetch_coingecko_candles(coin_id: str | None, days: int = 210) -> List[Dict[str, float]] | None:
    if not coin_id:
        return None
    try:
        response = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json() or {}
        prices = payload.get("prices") or []
        volumes = payload.get("total_volumes") or []
        candles = []
        for index, item in enumerate(prices):
            ts_ms, price = item
            volume = volumes[index][1] if index < len(volumes) else 0
            candles.append({"ts": ts_ms / 1000, "open": float(price), "high": float(price), "low": float(price), "close": float(price), "volume": float(volume)})
        return candles if len(candles) >= 20 else None
    except Exception:
        return None


def _fetch_candles(symbol: str, coin_id: str | None) -> List[Dict[str, float]] | None:
    for fetcher in (
        lambda: _fetch_coinbase_candles(symbol),
        lambda: _fetch_gateio_candles(symbol),
        lambda: _fetch_binance_candles(symbol),
        lambda: _fetch_coingecko_candles(coin_id),
    ):
        candles = fetcher()
        if candles:
            return candles
    return None


def _sma(values: List[float], window: int) -> float:
    sample = values[-window:] if len(values) >= window else values
    return sum(sample) / len(sample) if sample else 0.0


def _ema(values: List[float], window: int) -> List[float]:
    """Exponential Moving Average — base para MACD e Bollinger."""
    if not values:
        return []
    k = 2 / (window + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _calculate_rsi_wilder(closes: List[float], window: int = 14) -> float:
    """RSI com suavização de Wilder (mais preciso que média simples)."""
    if len(closes) < window + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    # Seed com média simples dos primeiros `window` valores
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    # Wilder smoothing no resto
    for g, l in zip(gains[window:], losses[window:]):
        avg_gain = (avg_gain * (window - 1) + g) / window
        avg_loss = (avg_loss * (window - 1) + l) / window
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


def _calculate_macd(closes: List[float]) -> Dict[str, Any]:
    """MACD(12,26,9). Devolve linha MACD, sinal, histograma e classificação."""
    if len(closes) < 35:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0, "macd_signal": "NEUTRO"}
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [m - e for m, e in zip(ema12[25:], ema26[25:])]  # alinha pelo índice 25
    if len(macd_line) < 9:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0, "macd_signal": "NEUTRO"}
    signal_line = _ema(macd_line, 9)
    macd_val = round(macd_line[-1], 8)
    sig_val = round(signal_line[-1], 8)
    hist_val = round(macd_val - sig_val, 8)
    prev_hist = round(macd_line[-2] - signal_line[-2], 8) if len(macd_line) >= 2 else hist_val
    if macd_val > sig_val and hist_val > prev_hist:
        label = "BULLISH_STRONG"
    elif macd_val > sig_val:
        label = "BULLISH"
    elif macd_val < sig_val and hist_val < prev_hist:
        label = "BEARISH_STRONG"
    elif macd_val < sig_val:
        label = "BEARISH"
    else:
        label = "NEUTRO"
    return {"macd": macd_val, "signal": sig_val, "hist": hist_val, "macd_signal": label}


def _calculate_bollinger(closes: List[float], window: int = 20, std_mult: float = 2.0) -> Dict[str, Any]:
    """Bollinger Bands. Devolve posição relativa e estado de squeeze."""
    if len(closes) < window:
        return {"bb_upper": None, "bb_lower": None, "bb_position": "NEUTRO", "bb_width": None}
    sample = closes[-window:]
    mid = sum(sample) / window
    variance = sum((x - mid) ** 2 for x in sample) / window
    std = variance ** 0.5
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    current = closes[-1]
    width = round((upper - lower) / mid * 100, 2) if mid else 0.0
    if upper == lower:
        bb_pct = 50.0
    else:
        bb_pct = round((current - lower) / (upper - lower) * 100, 1)
    if bb_pct >= 90:
        bb_pos = "ACIMA_BANDA"
    elif bb_pct >= 70:
        bb_pos = "ZONA_ALTA"
    elif bb_pct <= 10:
        bb_pos = "ABAIXO_BANDA"
    elif bb_pct <= 30:
        bb_pos = "ZONA_BAIXA"
    else:
        bb_pos = "NEUTRO"
    return {
        "bb_upper": round(upper, 10),
        "bb_lower": round(lower, 10),
        "bb_position": bb_pos,
        "bb_pct": bb_pct,
        "bb_width": width,
    }


def _find_pivot_support_resistance(closes: List[float], highs: List[float], lows: List[float]) -> tuple[float, float]:
    """Suporte/resistência por swing pivots (mais realista que min/max simples)."""
    window = 5
    pivot_highs = []
    pivot_lows = []
    src_h = highs if len(highs) >= len(closes) else closes
    src_l = lows if len(lows) >= len(closes) else closes
    for i in range(window, len(src_h) - window):
        if all(src_h[i] >= src_h[j] for j in range(i - window, i + window + 1) if j != i):
            pivot_highs.append(src_h[i])
        if all(src_l[i] <= src_l[j] for j in range(i - window, i + window + 1) if j != i):
            pivot_lows.append(src_l[i])
    current = closes[-1]
    # Resistência = pivot high mais próximo ACIMA do preço atual
    resistances_above = [p for p in pivot_highs if p > current]
    # Suporte = pivot low mais próximo ABAIXO do preço atual
    supports_below = [p for p in pivot_lows if p < current]
    resistance = min(resistances_above) if resistances_above else max(src_h[-30:]) * 1.02
    support = max(supports_below) if supports_below else min(src_l[-30:]) * 0.98
    return round(support, 10), round(resistance, 10)


def _calculate_technical_from_candles(symbol: str, candles: List[Dict[str, float]]) -> Dict[str, Any] | None:
    closes = [float(c["close"]) for c in candles if c.get("close") is not None]
    highs = [float(c.get("high") or c.get("close") or 0) for c in candles]
    lows = [float(c.get("low") or c.get("close") or 0) for c in candles]
    volumes = [float(c.get("volume") or 0) for c in candles]
    if len(closes) < 20:
        return None

    current = closes[-1]

    # Médias móveis
    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    sma_200 = _sma(closes, 200) if len(closes) >= 50 else None
    above_sma200 = bool(sma_200 and current > sma_200)
    trend_strength = round(abs(sma_20 - sma_50) / sma_50 * 100, 1) if sma_50 else 0.0

    # Tendência: usa SMA200 se disponível para confirmar macro
    if sma_200:
        if sma_20 >= sma_50 and current > sma_200:
            trend = "UPTREND"
        elif sma_20 < sma_50 and current < sma_200:
            trend = "DOWNTREND"
        elif sma_20 >= sma_50:
            trend = "UPTREND"  # micro up, macro misto
        else:
            trend = "DOWNTREND"
    else:
        trend = "UPTREND" if sma_20 >= sma_50 else "DOWNTREND"

    # RSI Wilder
    rsi = _calculate_rsi_wilder(closes)

    # MACD
    macd_data = _calculate_macd(closes)

    # Bollinger Bands
    bb_data = _calculate_bollinger(closes)

    # Suporte/Resistência por pivots
    support, resistance = _find_pivot_support_resistance(closes, highs, lows)
    if resistance <= support:
        # fallback se pivots não encontraram nada útil
        support = round(min(lows[-30:] if len(lows) >= 30 else lows) * 0.98, 10)
        resistance = round(max(highs[-30:] if len(highs) >= 30 else highs) * 1.02, 10)

    current_position = round(((current - support) / (resistance - support)) * 100, 1) if resistance != support else 50.0
    current_position = max(0.0, min(100.0, current_position))

    # Volatilidade
    returns = [(b - a) / a for a, b in zip(closes[-21:-1], closes[-20:]) if a]
    volatility = round((sum((r - (sum(returns) / len(returns))) ** 2 for r in returns) / len(returns)) ** 0.5 * 100, 2) if returns else 0.0

    # Volume
    avg_volume = _sma(volumes, 20)
    volume_ratio = round((volumes[-1] / avg_volume), 2) if avg_volume else 1.0

    # Zona de entrada
    if current_position <= 35:
        entry_zone = "ZONA_DE_COMPRA"
    elif current_position >= 75:
        entry_zone = "ZONA_DE_VENDA"
    else:
        entry_zone = "ZONA_NEUTRA"

    # Ação técnica combinando RSI + MACD + posição
    macd_sig = macd_data["macd_signal"]
    bearish_macd = macd_sig in ("BEARISH", "BEARISH_STRONG")
    bullish_macd = macd_sig in ("BULLISH", "BULLISH_STRONG")
    if rsi >= 70 or current_position >= 75 or bb_data["bb_position"] == "ACIMA_BANDA":
        technical_action = "AGUARDAR"
    elif entry_zone == "ZONA_DE_COMPRA" and bullish_macd:
        technical_action = "COMPRA"
    elif entry_zone == "ZONA_DE_COMPRA" and not bearish_macd:
        technical_action = "COMPRA_CAUTELOSA"
    elif bearish_macd and rsi > 60:
        technical_action = "AGUARDAR"
    else:
        technical_action = "OBSERVAR"

    # Confiança
    high_conf = (25 <= rsi <= 55 and current_position <= 45 and bullish_macd)
    technical_confidence = "ALTA" if high_conf else "MEDIA"

    stop_loss = round(support * 0.92, 10)
    # ✅ FIX: Converter targets em string para evitar problemas com arrays no Supabase
    targets_str = " | ".join([
        f"{resistance * 0.98:g} - {resistance:g} (30%)",
        f"{resistance:g} - {resistance * 1.05:g} (50%)",
        f"{resistance * 1.05:g}+ (20%)",
    ])

    return {
        "rsi": rsi,
        "trend": trend,
        "trend_strength": trend_strength,
        "volatility": volatility,
        "volume_ratio_20d": volume_ratio,
        "support": support,
        "resistance": resistance,
        "current_position": current_position,
        "entry_zone": entry_zone,
        "stop_loss": f"{stop_loss:g}",
        "targets": targets_str,
        "technical_action": technical_action,
        "technical_confidence": technical_confidence,
        "macd_signal": macd_data["macd_signal"],
        "macd_hist": macd_data["hist"],
        "above_sma200": above_sma200,
        "bb_position": bb_data["bb_position"],
        "bb_width": bb_data.get("bb_width"),
    }


def _analyze_symbol_technical_sync(row: Dict[str, Any]) -> Dict[str, Any] | None:
    symbol = row.get("symbol")
    candles = _fetch_candles(symbol, row.get("coin_id"))
    if not candles:
        return None
    return _calculate_technical_from_candles(symbol, candles)


async def _analyze_symbol_technical(row: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any] | None:
    async with semaphore:
        try:
            return await asyncio.to_thread(_analyze_symbol_technical_sync, row)
        except Exception as e:
            print(f"Top100 tecnico falhou para {row.get('symbol')}: {e}", flush=True)
            return None


async def enrich_rows_with_technical(rows: List[Dict[str, Any]], max_symbols: int = 100) -> List[Dict[str, Any]]:
    semaphore = asyncio.Semaphore(4)
    selected_rows = rows[:max_symbols]
    results = await asyncio.gather(
        *[_analyze_symbol_technical(row, semaphore) for row in selected_rows],
        return_exceptions=False,
    )
    technical_by_symbol = dict(zip([row["symbol"] for row in selected_rows], results))

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
                "targets": technical.get("targets"),  # ✅ AGORA É STRING, OK PARA SUPABASE
                "technical_action": technical.get("technical_action"),
                "technical_confidence": technical.get("technical_confidence"),
                "macd_signal": technical.get("macd_signal"),
                "macd_hist": technical.get("macd_hist"),
                "above_sma200": technical.get("above_sma200"),
                "bb_position": technical.get("bb_position"),
                "bb_width": technical.get("bb_width"),
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
        # Supabase bulk upsert exige que todas as rows tenham exactamente os mesmos campos.
        # Normalizamos para a união de todas as keys, preenchendo None onde falta.
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        normalized = [{k: row.get(k) for k in all_keys} for row in rows]

        saved = bulk_upsert_func(TOP100_TABLE, normalized, ["date", "symbol"])
        if saved == 0 and rows:
            legacy_keys = all_keys - {
                "rsi", "trend", "trend_strength", "volatility", "volume_ratio_20d",
                "support", "resistance", "current_position", "entry_zone", "stop_loss",
                "targets", "technical_action", "technical_confidence",
                "macd_signal", "macd_hist", "above_sma200", "bb_position", "bb_width",
            }
            legacy_rows = [{k: row.get(k) for k in legacy_keys} for row in rows]
            print("Top100 tecnico: retry sem colunas tecnicas para manter compatibilidade Supabase", flush=True)
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
