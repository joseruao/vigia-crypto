# backend/Api/routes/alerts.py
from __future__ import annotations
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/alerts", tags=["alerts"])

log = logging.getLogger("vigia.alerts")

# =====================================================
# ENV / CONFIG
# =====================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
# se estiveres a testar local com a anon, deixa passar
if not SUPABASE_URL:
    log.warning("⚠️ SUPABASE_URL em falta — /alerts vai devolver vazio")
if not SUPABASE_SERVICE_ROLE_KEY:
    log.warning("⚠️ SUPABASE_SERVICE_ROLE_KEY em falta — só dá para ler se RLS permitir")

TABLE = "transacted_tokens"
HTTP_TIMEOUT = 10.0

# =====================================================
# HELPERS SUPABASE
# =====================================================
async def sb_select(
    params: Dict[str, str],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Faz GET ao Supabase REST.
    Usa sempre a tabela transacted_tokens.
    """
    if not SUPABASE_URL:
        return []
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    # order=-ts é suportado
    params = dict(params)
    params.setdefault("order", "ts.desc")
    params.setdefault("limit", str(limit))

    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json()
    log.error(f"❌ Supabase GET {r.status_code}: {r.text}")
    return []

# =====================================================
# NORMALIZAÇÕES
# =====================================================
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
    if not ex:
        return ex
    return EXCHANGE_NORMALIZE.get(ex, ex)

# =====================================================
# MODELOS DE SAÍDA (simples)
# =====================================================
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

# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/health")
async def alerts_health():
    return {
        "ok": True,
        "ts": int(datetime.now(tz=timezone.utc).timestamp()),
        "supabase": bool(SUPABASE_URL),
    }


@router.get("/holdings")
async def get_holdings(
    exchange: Optional[str] = Query(None, description="Filtrar por exchange (ex: Binance, Gate.io)"),
    min_score: float = Query(50, description="Score mínimo"),
    limit: int = Query(50, le=200),
):
    """
    Devolve holdings mais recentes da tabela transacted_tokens.
    Só traz type=holding.
    Se estiver vazio devolve [] com 200, não 500.
    """
    params: Dict[str, str] = {
        "type": "eq.holding",
        "score": f"gte.{min_score}",
    }
    if exchange:
        # aceitar 'Binance' e 'Binance 1'
        params["exchange"] = f"ilike.{exchange}%"

    rows = await sb_select(params, limit=limit)
    holdings = [to_holding_row(r) for r in rows]
    return holdings  # [] se não houver


@router.get("/predictions")
async def get_predictions(
    min_score: float = Query(50),
    limit: int = Query(50, le=200),
):
    """
    Para já vamos assumir que predictions também são guardadas em transacted_tokens,
    mas com type='prediction' (se ainda não tens, isto devolve []).
    """
    params = {
        "type": "eq.prediction",
        "score": f"gte.{min_score}",
    }
    rows = await sb_select(params, limit=limit)
    preds = [to_holding_row(r) for r in rows]
    return preds


@router.post("/ask")
async def alerts_ask(payload: Dict[str, Any]):
    """
    Perguntas tipo:
    - "que tokens a binance está a fazer holding e ainda não foram listados?"
    - "mostra holdings da gate.io com score > 70"
    Isto é simples, não LLM.
    """
    q = (payload.get("prompt") or payload.get("question") or "").lower().strip()
    if not q:
        raise HTTPException(status_code=400, detail="prompt/question em falta")

    # 1) detectar exchange
    target_ex: Optional[str] = None
    for ex in ["binance", "gate.io", "gate", "bybit", "mexc", "okx", "kraken", "coinbase", "bitget"]:
        if ex in q:
            # normalizar
            if ex == "gate":
                target_ex = "Gate.io"
            elif ex == "binance":
                target_ex = "Binance"
            else:
                target_ex = ex.capitalize() if "." not in ex else ex
            break

    # 2) detectar score
    min_score = 50.0
    if "score > 70" in q or "score acima de 70" in q or "score >= 70" in q:
        min_score = 70.0
    elif "score > 60" in q:
        min_score = 60.0

    # 3) buscar
    params: Dict[str, str] = {
        "type": "eq.holding",
        "score": f"gte.{min_score}",
    }
    if target_ex:
        params["exchange"] = f"ilike.{target_ex}%"

    rows = await sb_select(params, limit=50)

    # 4) se pediste "ainda não listados" — aqui dependias da tua lógica antiga
    # neste momento só devolvemos o que está gravado
    if not rows:
        return {
            "answer": "Não encontrei holdings que batam nesses filtros.",
            "items": [],
        }

    items = [to_holding_row(r) for r in rows]
    return {
        "answer": f"Encontrei {len(items)} holdings.",
        "items": items,
    }
