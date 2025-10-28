# backend/Api/routes/alerts.py
import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from supabase import create_client
except ImportError:
    create_client = None

router = APIRouter(prefix="/alerts", tags=["alerts"])
log = logging.getLogger("vigia.alerts")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

def get_supabase():
    if not create_client:
        raise RuntimeError("supabase lib not installed")
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        raise RuntimeError("Supabase envs missing")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

class AskPayload(BaseModel):
    prompt: str

@router.post("/ask")
async def alerts_ask(payload: AskPayload):
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")
    return {"answer": f"Alerta-base para: {prompt}"}

@router.get("/holdings")
def get_holdings():
    """Retorna tokens com type='holding' da tabela transacted_tokens."""
    try:
        sb = get_supabase()
        resp = (
            sb.table("transacted_tokens")
            .select("id, token, exchange, token_address, value_usd, liquidity, volume_24h, score, pair_url, analysis, ts")
            .eq("type", "holding")
            .order("ts", desc=True)
            .limit(100)
            .execute()
        )
        return JSONResponse(resp.data or [])
    except Exception as e:
        log.error(f"Erro holdings: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar holdings")

@router.get("/predictions")
def get_predictions():
    """Retorna tokens com type='prediction' da tabela transacted_tokens."""
    try:
        sb = get_supabase()
        resp = (
            sb.table("transacted_tokens")
            .select("id, token, exchange, token_address, value_usd, liquidity, volume_24h, score, pair_url, analysis, ts")
            .eq("type", "prediction")
            .order("ts", desc=True)
            .limit(100)
            .execute()
        )
        return JSONResponse(resp.data or [])
    except Exception as e:
        log.error(f"Erro predictions: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar predictions")
