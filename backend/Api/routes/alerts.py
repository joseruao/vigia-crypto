from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Set

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from supabase import create_client, Client  # type: ignore

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

# ---------- ENV & CLIENTE (lazy) ----------
_SUPABASE_CLIENT: Optional[Client] = None

def _get_env(name: str, *fallbacks: str) -> Optional[str]:
    for k in (name, *fallbacks):
        v = os.environ.get(k)
        if v:
            return v
    return None

def get_supabase() -> Client:
    """
    Cria e cacheia o cliente Supabase apenas quando chamado por uma rota.
    Falha só quando a rota é de facto usada (não no import).
    """
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    supabase_url = _get_env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = (
        _get_env("SUPABASE_SERVICE_ROLE")
        or _get_env("SUPABASE_KEY")
        or _get_env("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )

    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase envs em falta (SUPABASE_URL e SERVICE_ROLE/ANON)."
        )

    _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT

# ---------- HELPERS ----------
def _dedupe_predictions(rows: List[Prediction], max_items: int = 10) -> List[Prediction]:
    """
    Remove duplicados por (token, exchange, pair_url) preservando ordem temporal.
    """
    seen: Set[Tuple[str, str, str]] = set()
    out: List[Prediction] = []
    for r in rows:
        key = (r.token.upper().strip(), r.exchange.strip(), (r.pair_url or "").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= max_items:
            break
    return out

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
    Aceita application/json, x-www-form-urlencoded, e texto cru.
    Retorna sempre um dict com 'prompt' ou lança 400.
    """
    ctype = (request.headers.get("content-type") or "").lower()

    if "application/json" in ctype:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        return data

    if "application/x-www-form-urlencoded" in ctype:
        form = await request.form()
        return dict(form)

    raw = (await request.body()) or b""
    text = raw.decode("utf-8", errors="ignore").strip()

    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    if text:
        return {"prompt": text}

    raise HTTPException(status_code=400, detail="Body vazio ou inválido")

# ---------- ENDPOINTS ----------
@router.get("/predictions")
def get_predictions(limit: int = 10) -> List[Prediction]:
    sb = get_supabase()
    resp = (
        sb.table("predictions")
        .select("*")
        .order("ts", desc=True)
        .limit(max(limit, 1))
        .execute()
    )
    rows = [Prediction(**r) for r in (resp.data or [])]
    rows = _dedupe_predictions(rows, max_items=limit)
    return rows

@router.post("/ask")
async def ask_alerts(request: Request, exchange: Optional[str] = Query(default=None)) -> dict:
    data = await read_loose_body(request)

    prompt_val = data.get("prompt") or ""
    prompt = str(prompt_val).strip()
    ex = data.get("exchange") or exchange

    if not prompt:
        raise HTTPException(status_code=400, detail="Falta 'prompt'.")

    sb = get_supabase()
    q = sb.table("predictions").select("*").order("ts", desc=True).limit(25)
    if ex:
        q = q.eq("exchange", ex)
    resp = q.execute()
    rows = [Prediction(**r) for r in (resp.data or [])]
    rows = _dedupe_predictions(rows, max_items=10)

    answer = format_predictions_md(rows)
    return {"answer": answer}
