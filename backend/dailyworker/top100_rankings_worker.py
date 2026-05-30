import math
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Any

import requests


TOP100_TABLE = "top100_technical_rankings"


def _num(value, default=0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return float(default)


def _risk_label(rank: int, volume_ratio: float, change_7d: float, change_30d: float) -> str:
    if rank <= 20 and volume_ratio >= 0.04 and abs(change_7d) < 18:
        return "BAIXO/MODERADO"
    if volume_ratio < 0.015 or abs(change_7d) > 35 or abs(change_30d) > 80:
        return "ELEVADO"
    if volume_ratio < 0.03 or abs(change_7d) > 22:
        return "MODERADO/ELEVADO"
    return "MODERADO"


def _score_coin(item: Dict[str, Any]) -> Dict[str, Any]:
    rank = int(item.get("market_cap_rank") or 999)
    market_cap = _num(item.get("market_cap"))
    volume = _num(item.get("total_volume"))
    change_24h = _num(item.get("price_change_percentage_24h"))
    change_7d = _num(item.get("price_change_percentage_7d_in_currency"))
    change_30d = _num(item.get("price_change_percentage_30d_in_currency"))
    volume_ratio = volume / market_cap if market_cap > 0 else 0.0

    score = 45.0
    score += max(min(change_24h * 0.7, 8), -8)
    score += max(min(change_7d * 0.8, 18), -18)
    score += max(min(change_30d * 0.35, 14), -14)
    score += min(math.log10(volume_ratio * 1000 + 1) * 9, 18)

    if rank <= 10:
        score += 5
    elif rank <= 50:
        score += 3

    if change_7d > 30 or change_30d > 90:
        score -= 10
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
    if change_7d > 0:
        reasons.append(f"7d {change_7d:.1f}%")
    if change_30d > 0:
        reasons.append(f"30d {change_30d:.1f}%")
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


def fetch_top100_market_data() -> List[Dict[str, Any]]:
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
    return response.json() or []


def build_top100_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in items:
        computed = _score_coin(item)
        rows.append({
            "date": today,
            "rank": int(item.get("market_cap_rank") or 999),
            "coin_id": item.get("id"),
            "symbol": str(item.get("symbol") or "").upper(),
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
        })
    rows.sort(key=lambda row: (row["score"], -row["rank"]), reverse=True)
    return rows


def update_top100_rankings(upsert_func: Callable[[str, Dict[str, Any], List[str]], bool]) -> int:
    print("🔎 ATUALIZANDO RANKING TECNICO TOP100...")
    items = fetch_top100_market_data()
    rows = build_top100_rows(items)

    saved = 0
    for row in rows:
        if upsert_func(TOP100_TABLE, row, ["date", "symbol"]):
            saved += 1
        time.sleep(0.05)

    print(f"✅ Top100 atualizado: {saved}/{len(rows)} moedas guardadas")
    return saved
