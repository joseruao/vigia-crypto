# backend/Api/routes/alerts.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
router = APIRouter(tags=["alerts"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EXCHANGES = ["Binance", "Coinbase", "Kraken", "Bybit", "Gate.io", "Bitget", "OKX", "MEXC"]

class ChatRequest(BaseModel):
    prompt: str

@router.get("/alerts/predictions")
def predictions():
    try:
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
            .limit(8)
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
                .limit(8)
            ).execute()
            data = getattr(resp, "data", []) or []

        return data
    except Exception:
        return []

@router.post("/alerts/ask")
def ask_alerts(req: ChatRequest, exchange: Optional[str] = Query(None)):
    try:
        q = (req.prompt or "").lower()
        detected_exchange = next((ex for ex in EXCHANGES if ex.lower() in q), None)
        if exchange:
            detected_exchange = exchange

        base = supabase.table("transacted_tokens").select(
            "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
            "score, pair_url, ts, analysis_text"
        )
        if detected_exchange:
            base = base.eq("exchange", detected_exchange)

        resp = (
            base.order("score", desc=True)
                .order("ts", desc=True)
                .limit(10)
        ).execute()

        rows = getattr(resp, "data", []) or []
        if not rows:
            where = f"na {detected_exchange}" if detected_exchange else ""
            return {"answer": f"Nenhum token encontrado {where}."}

        # usa analysis_text quando existir; senão gera linha com links
        lines = []
        for r in rows:
            if r.get("analysis_text"):
                lines.append(f"- {r['analysis_text']}")
                continue

            token = r.get("token") or "—"
            ex = r.get("exchange") or "—"
            score = r.get("score")
            score_txt = f"{score:.1f}" if isinstance(score, (int, float)) else "—"

            pair_url = r.get("pair_url") or (
                f"https://dexscreener.com/solana/{r.get('token_address')}"
                if r.get("token_address") else f"https://dexscreener.com/search?q={token}"
            )
            coingecko_url = f"https://www.coingecko.com/en/search?query={token}"

            lines.append(
                f"- **{token}** _( {ex} )_ — **Score:** {score_txt}  \n"
                f"  ↳ [DexScreener]({pair_url}) · [CoinGecko]({coingecko_url})"
            )

        where = f"na **{detected_exchange}**" if detected_exchange else ""
        answer = f"**Últimos potenciais listings detetados {where}:**\n\n" + "\n".join(lines)
        return {"answer": answer}

    except Exception as e:
        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}
