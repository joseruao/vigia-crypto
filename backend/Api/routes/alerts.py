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


# ---------------------- HELPERS ----------------------
def get_supabase():
    if not create_client:
        raise RuntimeError("⚠️ supabase lib não instalada")

    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )

    if not url or not key:
        raise RuntimeError("⚠️ variáveis SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY ausentes")

    return create_client(url, key)


# ---------------------- MODELOS ----------------------
class AskPayload(BaseModel):
    prompt: str


# ---------------------- ROTAS ----------------------
@router.post("/ask")
async def alerts_ask(payload: AskPayload):
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")
    return {"answer": f"Resposta simulada para: {prompt}"}


@router.get("/holdings")
def get_holdings():
    """Retorna holdings de transacted_tokens (ou lista vazia em erro)."""
    try:
        sb = get_supabase()
        res = (
            sb.table("transacted_tokens")
            .select(
                "id, token, exchange, token_address, value_usd, liquidity, volume_24h, "
                "score, pair_url, analysis, ts"
            )
            .eq("type", "holding")
            .order("ts", desc=True)
            .limit(100)
            .execute()
        )
        data = getattr(res, "data", None) or []
        return JSONResponse(data)
    except Exception as e:
        log.error(f"❌ /alerts/holdings erro: {e}")
        return JSONResponse([], status_code=200)


@router.get("/predictions")
def get_predictions():
    """Retorna predictions de transacted_tokens (ou lista vazia em erro)."""
    try:
        sb = get_supabase()
        res = (
            sb.table("transacted_tokens")
            .select(
                "id, token, exchange, token_address, value_usd, liquidity, volume_24h, "
                "score, listing_probability, confidence, pair_url, ts"
            )
            .eq("type", "prediction")
            .order("ts", desc=True)
            .limit(100)
            .execute()
        )
        data = getattr(res, "data", None) or []
        return JSONResponse(data)
    except Exception as e:
        log.error(f"❌ /alerts/predictions erro: {e}")
        return JSONResponse([], status_code=200)
