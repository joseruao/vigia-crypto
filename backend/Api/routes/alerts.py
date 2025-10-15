# backend/Api/routes/alerts.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os, threading, json

from dotenv import load_dotenv
load_dotenv()

router = APIRouter(tags=["alerts"])

# -------- Supabase (lazy) --------
from supabase import create_client
_SUPA_LOCK = threading.Lock()
_SUPA_CLIENT = None

def get_supabase():
    global _SUPA_CLIENT
    if _SUPA_CLIENT is None:
        with _SUPA_LOCK:
            if _SUPA_CLIENT is None:
                SUPABASE_URL = os.getenv("SUPABASE_URL")
                SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                if not SUPABASE_URL or not SUPABASE_KEY:
                    raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY em falta no ambiente do serviço WEB.")
                _SUPA_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _SUPA_CLIENT

EXCHANGES = ["Binance", "Coinbase", "Kraken", "Bybit", "Gate.io", "Bitget", "OKX", "MEXC"]

class ChatRequest(BaseModel):
    prompt: str

def _coingecko_url(token: str) -> str:
    token = (token or "").strip()
    return f"https://www.coingecko.com/en/search?query={token}"

def _dexscreener_url(row: Dict[str, Any]) -> str:
    pair_url = row.get("pair_url")
    if pair_url:
        return pair_url
    token_addr = row.get("token_address") or ""
    token = row.get("token") or ""
    return f"https://dexscreener.com/solana/{token_addr}" if token_addr else f"https://dexscreener.com/search?q={token}"

def _fetch_rows(detected_exchange: Optional[str]) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    base = supabase.table("transacted_tokens").select(
        "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
        "score, pair_url, ts, analysis_text"
    )
    if detected_exchange:
        base = base.eq("exchange", detected_exchange)

    resp = (
        base.order("score", desc=True)
            .order("ts", desc=True)
            .limit(100)
    ).execute()
    return getattr(resp, "data", []) or []

def _dedupe_rows(rows: List[Dict[str, Any]], key_fields=("token_address", "exchange"), limit=10) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        k = tuple((r.get(f) or "").lower() for f in key_fields)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= limit:
            break
    return out

def _build_answer(prompt: str, exchange: Optional[str] = None) -> dict:
    q = (prompt or "").lower()
    detected_exchange = next((ex for ex in EXCHANGES if ex.lower() in q), None)
    if exchange:
        detected_exchange = exchange

    rows = _fetch_rows(detected_exchange)
    if not rows:
        where = f"na {detected_exchange}" if detected_exchange else ""
        return {"answer": f"Nenhum token encontrado {where}."}

    rows = _dedupe_rows(rows, key_fields=("token_address", "exchange"), limit=10)

    lines: List[str] = []
    for r in rows:
        if r.get("analysis_text"):
            lines.append(f"- {r['analysis_text']}")
            continue

        token = r.get("token") or "—"
        ex = r.get("exchange") or "—"
        score = r.get("score")
        score_txt = f"{score:.1f}" if isinstance(score, (int, float)) else "—"
        pair_url = _dexscreener_url(r)
        coingecko_url = _coingecko_url(token)

        lines.append(
            f"- **{token}** _( {ex} )_ — **Score:** {score_txt}  \n"
            f"  ↳ [DexScreener]({pair_url}) · [CoinGecko]({coingecko_url})"
        )

    where = f"na **{detected_exchange}**" if detected_exchange else ""
    answer = f"**Últimos potenciais listings detetados {where}:**\n\n" + "\n".join(lines)
    return {"answer": answer}

@router.get("/alerts/predictions")
def predictions():
    try:
        supabase = get_supabase()
        q = (
            supabase.table("transacted_tokens")
            .select(
                "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
                "score, pair_url, ts"
            )
            .gte("value_usd", 10000)
            .gte("liquidity", 100000)
            .order("score", desc=True)
            .order("ts", desc=True)
            .limit(20)
        )
        resp = q.execute()
        data = getattr(resp, "data", []) or []
        if not data:
            resp = (
                supabase.table("transacted_tokens")
                .select(
                    "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
                    "score, pair_url, ts"
                )
                .order("ts", desc=True)
                .limit(20)
            ).execute()
            data = getattr(resp, "data", []) or []

        for r in data:
            r["coingecko_url"] = _coingecko_url(r.get("token") or "")
            r["pair_url"] = _dexscreener_url(r)
        data = _dedupe_rows(data, key_fields=("token_address", "exchange"), limit=8)
        return data
    except Exception as e:
        return {"error": f"predictions failed: {e}", "data": []}

# ---------- Compat: aceita POST (json ou text) e GET ----------
@router.post("/alerts/ask")
async def ask_alerts_post(request: Request, exchange: Optional[str] = Query(None)):
    try:
        prompt = None
        ctype = request.headers.get("content-type", "")
        if "application/json" in ctype:
            data = await request.json()
            if isinstance(data, dict):
                prompt = data.get("prompt")
        elif "text/plain" in ctype:
            prompt = (await request.body()).decode("utf-8", errors="ignore")
        else:
            # tentativa: se mandarem json mas com header marado
            raw = (await request.body()).decode("utf-8", errors="ignore").strip()
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    prompt = obj.get("prompt")
            except Exception:
                prompt = raw

        if not prompt or not str(prompt).strip():
            return {"answer": "⚠️ prompt vazio."}
        return _build_answer(str(prompt), exchange)
    except Exception as e:
        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}

@router.get("/alerts/ask")
def ask_alerts_get(
    prompt: str = Query(..., description="pergunta do utilizador"),
    exchange: Optional[str] = Query(None)
):
    try:
        return _build_answer(prompt, exchange)
    except Exception as e:
        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}
