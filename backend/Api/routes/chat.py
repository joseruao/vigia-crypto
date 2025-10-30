# backend/Api/chat.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from . import alerts  # importa o ficheiro de cima

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/holdings")
def get_holdings(
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    exchange: Optional[str] = None,
):
    """
    devolve lista JSON que o teu frontend pode meter na UI.
    """
    try:
        if exchange:
            rows = alerts.search_holdings_by_exchange(exchange, min_score=min_score)
        else:
            rows = alerts.get_top_holdings(limit=limit, min_score=min_score)

        # normalizar chaves para o frontend
        return [
            {
                "token": r.get("token"),
                "exchange": r.get("exchange"),
                "chain": r.get("chain"),
                "value_usd": float(r.get("value_usd") or 0),
                "liquidity": float(r.get("liquidity") or 0),
                "volume_24h": float(r.get("volume_24h") or 0),
                "score": float(r.get("score") or 0),
                "pair_url": r.get("pair_url"),
                "analysis": r.get("analysis") or r.get("analysis_text"),
                "ts": r.get("ts"),
            }
            for r in rows
        ]
    except Exception as e:
        # não rebentar o frontend
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/predictions")
def get_predictions(
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
):
    try:
        rows = alerts.get_top_predictions(limit=limit, min_score=min_score)
        return [
            {
                "token": r.get("token"),
                "exchange": r.get("exchange"),
                "chain": r.get("chain"),
                "value_usd": float(r.get("value_usd") or 0),
                "liquidity": float(r.get("liquidity") or 0),
                "volume_24h": float(r.get("volume_24h") or 0),
                "score": float(r.get("score") or 0),
                "pair_url": r.get("pair_url"),
                "analysis": r.get("analysis") or r.get("analysis_text"),
                "ts": r.get("ts"),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============== ASK STYLE ==============

from pydantic import BaseModel

class AskPayload(BaseModel):
    prompt: str

@router.post("/ask")
def ask_alerts(payload: AskPayload):
    q = payload.prompt.lower().strip()

    # 1) se perguntar por exchange
    exchanges = [
        "Binance", "Coinbase", "Bybit", "Gate.io", "Bitget",
        "OKX", "MEXC", "Kraken"
    ]
    for ex in exchanges:
        if ex.lower() in q:
            rows = alerts.search_holdings_by_exchange(ex, min_score=0)
            if not rows:
                return {"answer": f"Não encontrei holdings recentes da {ex}."}
            top = rows[:10]
            txt = "\n".join(alerts.build_holding_msg(r) for r in top)
            return {"answer": txt}

    # 2) genérico – manda top holdings
    rows = alerts.get_top_holdings(limit=10, min_score=0)
    if not rows:
        return {"answer": "Sem holdings relevantes registados."}
    txt = "\n".join(alerts.build_holding_msg(r) for r in rows)
    return {"answer": txt}
