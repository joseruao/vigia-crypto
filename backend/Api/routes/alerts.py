# -*- coding: utf-8 -*-
import os, json, threading
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Request
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(tags=["alerts"])

# --- Supabase lazy (evita falhas em import) ---
from supabase import create_client
_SUPA_CLIENT = None
_SUPA_LOCK = threading.Lock()

def get_supabase():
    global _SUPA_CLIENT
    if _SUPA_CLIENT is None:
        with _SUPA_LOCK:
            if _SUPA_CLIENT is None:
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                if not url or not key:
                    raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY em falta.")
                _SUPA_CLIENT = create_client(url, key)
    return _SUPA_CLIENT

EXCHANGES = ["Binance", "Coinbase", "Kraken", "Bybit", "Gate.io", "Bitget", "OKX", "MEXC"]

def _coingecko_url(token: str) -> str:
    token = (token or "").strip()
    return f"https://www.coingecko.com/en/search?query={token}"

def _dexscreener_url(row: Dict[str, Any]) -> str:
    if row.get("pair_url"):
        return row["pair_url"]
    addr = row.get("token_address") or ""
    token = row.get("token") or ""
    return f"https://dexscreener.com/solana/{addr}" if addr else f"https://dexscreener.com/search?q={token}"

def _fetch_rows(exchange: Optional[str]) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    base = supabase.table("transacted_tokens").select(
        "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
        "score, pair_url, ts, analysis_text"
    )
    if exchange:
        base = base.eq("exchange", exchange)
    resp = base.order("score", desc=True).order("ts", desc=True).limit(100).execute()
    return getattr(resp, "data", []) or []

def _dedupe(rows: List[Dict[str, Any]], key=("token_address","exchange"), limit=10) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        k = tuple((r.get(f) or "").lower() for f in key)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= limit:
            break
    return out

def _build_answer(prompt: str, exchange: Optional[str]) -> Dict[str, Any]:
    q = (prompt or "").lower()
    detected = next((ex for ex in EXCHANGES if ex.lower() in q), None)
    if exchange:
        detected = exchange

    rows = _fetch_rows(detected)
    if not rows:
        where = f"na {detected}" if detected else ""
        return {"answer": f"Nenhum token encontrado {where}."}

    rows = _dedupe(rows, key=("token_address","exchange"), limit=10)

    lines: List[str] = []
    for r in rows:
        if r.get("analysis_text"):  # preferir o texto humano
            lines.append(f"- {r['analysis_text']}")
        else:
            token = r.get("token") or "—"
            ex = r.get("exchange") or "—"
            score = r.get("score")
            score_txt = f"{score:.1f}" if isinstance(score, (int, float)) else "—"
            lines.append(
                f"- **{token}** _( {ex} )_ — **Score:** {score_txt}  \n"
                f"  ↳ [DexScreener]({_dexscreener_url(r)}) · [CoinGecko]({_coingecko_url(token)})"
            )
    where = f"na **{detected}**" if detected else ""
    return {"answer": f"**Últimos potenciais listings detetados {where}:**\n\n" + "\n".join(lines)}

@router.get("/alerts/predictions")
def predictions():
    try:
        supabase = get_supabase()
        q = (
            supabase.table("transacted_tokens")
            .select("id, exchange, token, token_address, value_usd, liquidity, volume_24h, score, pair_url, ts")
            .gte("value_usd", 10000)
            .gte("liquidity", 100000)
            .order("score", desc=True)
            .order("ts", desc=True)
            .limit(20)
        ).execute()
        data = getattr(q, "data", []) or []
        if not data:
            q2 = (
                supabase.table("transacted_tokens")
                .select("id, exchange, token, token_address, value_usd, liquidity, volume_24h, score, pair_url, ts")
                .order("ts", desc=True)
                .limit(20)
            ).execute()
            data = getattr(q2, "data", []) or []

        for r in data:
            r["coingecko_url"] = _coingecko_url(r.get("token") or "")
            r["pair_url"] = _dexscreener_url(r)
        return _dedupe(data, key=("token_address","exchange"), limit=8)
    except Exception as e:
        return {"error": f"predictions failed: {e}", "data": []}

@router.post("/alerts/ask")
async def ask_post(request: Request, exchange: Optional[str] = Query(None)):
    try:
        prompt = None
        ctype = request.headers.get("content-type","")
        if "application/json" in ctype:
            body = await request.json()
            if isinstance(body, dict):
                prompt = body.get("prompt")
        else:
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
def ask_get(prompt: str = Query(...), exchange: Optional[str] = Query(None)):
    try:
        return _build_answer(prompt, exchange)
    except Exception as e:
        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}
