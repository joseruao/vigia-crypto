# backend/Api/routes/alerts.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

# Se já criaste o cliente Supabase noutro módulo, importa-o.
# Caso contrário, usa este bloco e garante que tens as envs SUPABASE_URL e SUPABASE_SERVICE_ROLE setadas no Render.
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL / SUPABASE_KEY envs")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ---------- MODELOS ----------
class AskIn(BaseModel):
    prompt: str
    exchange: Optional[str] = None


class Prediction(BaseModel):
    id: int
    exchange: str
    token: str
    token_address: str
    value_usd: float
    liquidity: float
    volume_24h: float
    score: int
    pair_url: Optional[str] = None
    ts: datetime


# ---------- HELPERS ----------
def format_predictions_md(rows: List[Prediction]) -> str:
    if not rows:
        return "Nenhum potencial listing detetado nas últimas leituras."

    lines = ["**Últimos potenciais listings detetados :**", ""]
    for r in rows:
        cg = f"https://www.coingecko.com/en/search?query={r.token}"
        ds = r.pair_url or ""
        ex = r.exchange
        lines.append(
            f"- **{r.token}** _( {ex} )_ — **Score:** {r.score}.  \n"
            f"  ↳ [DexScreener]({ds}) · [CoinGecko]({cg})"
        )
    return "\n".join(lines)


async def read_loose_body(request: Request) -> dict:
    """
    Aceita application/json, form-urlencoded e texto cru.
    Retorna sempre um dict com pelo menos a key 'prompt' (ou lança 400).
    """
    ctype = (request.headers.get("content-type") or "").lower()

    # 1) JSON direto
    if "application/json" in ctype:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        return data

    # 2) form-urlencoded
    if "application/x-www-form-urlencoded" in ctype:
        form = await request.form()
        return dict(form)

    # 3) fallback: tentar json do raw, depois tratar como texto
    raw = (await request.body()) or b""
    text = raw.decode("utf-8", errors="ignore").strip()

    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Se vier só texto, assume que é o prompt
    if text:
        return {"prompt": text}

    raise HTTPException(status_code=400, detail="Body vazio ou inválido")


# ---------- ENDPOINTS ----------
@router.get("/predictions")
def get_predictions(limit: int = 10) -> List[Prediction]:
    """
    Devolve as últimas N previsões (como já validaste no sanity).
    """
    resp = supabase.table("predictions") \
        .select("*") \
        .order("ts", desc=True) \
        .limit(limit) \
        .execute()

    rows = resp.data or []
    return [Prediction(**r) for r in rows]


@router.post("/ask")
async def ask_alerts(request: Request, exchange: Optional[str] = Query(default=None)) -> dict:
    """
    Endpoint robusto: aceita vários content-types e devolve `{"answer": "...markdown..."}`.
    """
    data = await read_loose_body(request)

    prompt = str(data.get("prompt") or "").strip()
    ex = data.get("exchange") or exchange  # body tem prioridade; query é opcional

    if not prompt:
        raise HTTPException(status_code=400, detail="Falta 'prompt'.")

    # Lógica simples: ler últimas 10 previsões (opcionalmente filtradas por exchange)
    q = supabase.table("predictions").select("*").order("ts", desc=True).limit(10)
    if ex:
        q = q.eq("exchange", ex)
    resp = q.execute()
    rows = [Prediction(**r) for r in (resp.data or [])]

    answer = format_predictions_md(rows)
    return {"answer": answer}
