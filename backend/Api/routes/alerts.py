from __future__ import annotations

import json
import os
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

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
def get_predictions_direct(limit: int = 25, exchange: Optional[str] = None) -> List[Prediction]:
    """Chamada direta à REST API do Supabase (sem cliente)"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE")
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase envs em falta (SUPABASE_URL e SERVICE_ROLE).")

    # Chamada direta à REST API
    url = f"{supabase_url}/rest/v1/predictions"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "select": "*",
        "order": "ts.desc", 
        "limit": str(limit)
    }
    
    # Se exchange for especificada, adiciona filtro
    if exchange:
        params["exchange"] = f"eq.{exchange}"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return [Prediction(**item) for item in data]
        else:
            raise Exception(f"Supabase API error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"ERROR in get_predictions_direct: {e}")
        raise

def format_predictions_md(rows: List[Prediction]) -> str:
    if not rows:
        return "Nenhum potencial listing detetado nas últimas leituras."

    # DEBUG: Log para ver o que vem da BD
    print(f"DEBUG: Recebidas {len(rows)} linhas da BD")
    
    # Dedupe por token+exchange
    seen: set[tuple[str, str]] = set()
    uniq: List[Prediction] = []
    for r in rows:
        key = (r.token.upper(), r.exchange.upper())
        if key not in seen:
            seen.add(key)
            uniq.append(r)

    print(f"DEBUG: Após deduplicação: {len(uniq)} linhas únicas")

    lines = ["**Últimos potenciais listings detetados:**", ""]
    for r in uniq:
        cg = f"https://www.coingecko.com/en/search?query={r.token}"
        ds = r.pair_url or ""
        ex = r.exchange
        
        lines.append(
            f"- **{r.token}** ({ex}) — Score: {r.score}  \n"
            f"  [DexScreener]({ds}) | [CoinGecko]({cg})"
        )
    
    result = "\n".join(lines)
    print(f"DEBUG: Resultado final: {result}")
    return result

async def read_loose_body(request: Request) -> Dict[str, Any]:
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
    """Endpoint GET para testar a ligação à BD"""
    try:
        return get_predictions_direct(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao aceder aos dados: {str(e)}")

@router.post("/ask")
async def ask_alerts(request: Request, exchange: Optional[str] = Query(default=None)) -> dict:
    data = await read_loose_body(request)
    prompt_val = data.get("prompt") or ""
    prompt = str(prompt_val).strip()
    ex = data.get("exchange") or exchange

    if not prompt:
        raise HTTPException(status_code=400, detail="Falta 'prompt'.")

    try:
        # Usa a chamada direta em vez do cliente Supabase
        rows = get_predictions_direct(limit=25, exchange=ex)
        answer = format_predictions_md(rows)
        return {"answer": answer}
        
    except Exception as e:
        print(f"ERROR in /alerts/ask: {e}")
        raise HTTPException(status_code=500, detail=f"Erro temporário ao aceder aos dados: {str(e)}")