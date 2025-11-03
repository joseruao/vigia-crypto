# backend/Api/routes/alerts.py
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/alerts", tags=["alerts"])

log = logging.getLogger("vigia.alerts")

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)

TABLE = "transacted_tokens"
HTTP_TIMEOUT = 8.0

EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance",
    "Binance 2": "Binance",
    "Binance 3": "Binance",
    "Coinbase 1": "Coinbase",
    "Coinbase Hot": "Coinbase",
    "Kraken Cold 1": "Kraken",
    "Kraken Cold 2": "Kraken",
    "OKX 73": "OKX",
    "OKX 93": "OKX",
}

def norm_exchange(ex: str) -> str:
    return EXCHANGE_NORMALIZE.get(ex, ex)

async def sb_select(params: Dict[str, str], limit: int = 50) -> Dict[str, Any]:
    """
    devolve {ok: bool, data: [...], error: ...}
    assim o frontend nunca vê 'Failed to fetch' por JSON inválido
    """
    if not SUPABASE_URL:
        return {"ok": False, "data": [], "error": "SUPABASE_URL missing"}

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }

    params = dict(params)
    params.setdefault("order", "ts.desc")
    params.setdefault("limit", str(limit))

    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(url, headers=headers, params=params)
    except Exception as e:
        log.error(f"❌ Supabase fetch error: {e}")
        return {"ok": False, "data": [], "error": str(e)}

    if r.status_code == 200:
        return {"ok": True, "data": r.json(), "error": None}

    # se for 401 ou 42501 (RLS) devolve vazio mas com erro
    try:
        err_txt = r.text
    except Exception:
        err_txt = f"HTTP {r.status_code}"
    log.error(f"❌ Supabase {r.status_code}: {err_txt}")
    return {"ok": False, "data": [], "error": err_txt}

def to_holding_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "exchange": row.get("exchange"),
        "exchange_norm": norm_exchange(row.get("exchange") or ""),
        "token": row.get("token"),
        "token_address": row.get("token_address"),
        "value_usd": row.get("value_usd"),
        "liquidity": row.get("liquidity"),
        "volume_24h": row.get("volume_24h"),
        "score": row.get("score"),
        "pair_url": row.get("pair_url"),
        "analysis": row.get("analysis") or row.get("analysis_text"),
        "chain": row.get("chain"),
        "ts": row.get("ts"),
    }

@router.get("/health")
async def alerts_health():
    return {
        "ok": True,
        "ts": int(datetime.now(tz=timezone.utc).timestamp()),
        "supabase_url": bool(SUPABASE_URL),
        "has_key": bool(SUPABASE_SERVICE_ROLE_KEY),
    }

@router.get("/holdings")
async def get_holdings(
    exchange: Optional[str] = Query(None),
    min_score: float = Query(50),
    limit: int = Query(50, le=200),
):
    params: Dict[str, str] = {
        "type": "eq.holding",
        "score": f"gte.{min_score}",
    }
    if exchange:
        params["exchange"] = f"ilike.{exchange}%"

    res = await sb_select(params, limit=limit)
    data = [to_holding_row(r) for r in res["data"]]
    return {
        "ok": res["ok"],
        "error": res["error"],
        "items": data,
    }

@router.get("/predictions")
async def get_predictions(
    min_score: float = Query(50),
    limit: int = Query(50, le=200),
):
    params: Dict[str, str] = {
        "type": "eq.prediction",
        "score": f"gte.{min_score}",
    }
    res = await sb_select(params, limit=limit)
    data = [to_holding_row(r) for r in res["data"]]
    return {
        "ok": res["ok"],
        "error": res["error"],
        "items": data,
    }

@router.post("/ask")
async def alerts_ask(payload: Dict[str, Any]):
    # front tem de mandar JSON:
    # fetch('/alerts/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt:'...'})})
    q = (payload.get("prompt") or payload.get("question") or "").lower().strip()
    if not q:
        raise HTTPException(status_code=400, detail="prompt/question em falta")

    target_ex: Optional[str] = None
    for ex in ["binance", "gate.io", "gate", "bybit", "mexc", "okx", "kraken", "coinbase", "bitget"]:
        if ex in q:
            if ex == "gate":
                target_ex = "Gate.io"
            elif ex == "binance":
                target_ex = "Binance"
            else:
                target_ex = ex.capitalize() if "." not in ex else ex
            break

    min_score = 50.0
    if "70" in q:
        min_score = 70.0
    elif "60" in q:
        min_score = 60.0

    params: Dict[str, str] = {
        "type": "eq.holding",
        "score": f"gte.{min_score}",
    }
    if target_ex:
        params["exchange"] = f"ilike.{target_ex}%"

    res = await sb_select(params, limit=50)
    items = [to_holding_row(r) for r in res["data"]]

    # “ainda não foram listados” → filtra por listed_exchanges vazio se existir
    if "ainda nao foram listados" in q or "ainda não foram listados" in q:
        # só passa os que NÃO têm listed_exchanges ou lista vazia
        filtered = []
        for it in items:
            le = it.get("listed_exchanges")
            if not le or (isinstance(le, list) and len(le) == 0):
                filtered.append(it)
        items = filtered

    return {
        "ok": res["ok"],
        "error": res["error"],
        "count": len(items),
        "items": items,
    }
