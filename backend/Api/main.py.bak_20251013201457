from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
from openai import OpenAI
from dotenv import load_dotenv
from supabase import create_client
from typing import Optional

# ============================
# CONFIG
# ============================
load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Exchanges conhecidas
EXCHANGES = ["Binance", "Coinbase", "Kraken", "Bybit", "Gate.io", "Bitget", "OKX", "MEXC"]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ em produção limitar a ["http://localhost:3000", "https://teusite.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# MODELOS
# ============================
class ChatRequest(BaseModel):
    prompt: str

# ============================
# ENDPOINTS CHAT
# ============================
@app.post("/chat")
def chat(req: ChatRequest):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu és um assistente especializado em criptomoedas."},
            {"role": "user", "content": req.prompt},
        ],
    )
    return {"answer": completion.choices[0].message.content}

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def generate():
        with client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu és um assistente especializado em criptomoedas."},
                {"role": "user", "content": req.prompt},
            ],
        ) as stream:
            for event in stream:
                if event.type == "content.delta" and event.delta:
                    yield event.delta
                elif event.type == "error":
                    yield f"⚠️ Erro: {event.error}"
            stream.close()

    return StreamingResponse(generate(), media_type="text/plain")

# ============================
# ENDPOINTS ALERTS
# ============================
# ============================
# ENDPOINTS ALERTS (NOVOS)
# ============================

@app.get("/alerts/predictions")
def predictions():
    """
    Devolve uma lista pequena para o painel de 'Listings' (canto superior direito).
    Ordena por score desc e ts desc. Filtra mínimos para evitar lixo.
    """
    try:
        q = (
            supabase.table("transacted_tokens")
            .select(
                "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
                "score, pair_url, ts"
            )
            .gte("value_usd", 10000)       # >= 10k USD
            .gte("liquidity", 100000)      # >= 100k USD
            .order("score", desc=True)
            .order("ts", desc=True)
            .limit(8)
        )
        resp = q.execute()
        data = getattr(resp, "data", []) or []

        # fallback: se vier vazio, relaxa filtros
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
    except Exception as e:
        return []


@app.post("/alerts/ask")
def ask_alerts(req: ChatRequest, exchange: Optional[str] = Query(None)):
    """
    Responde com base nos registos reais (Supabase) e já devolve markdown com links.
    - Se o prompt mencionar uma exchange, filtra por essa exchange.
    - Caso contrário: top 10 por score e ts.
    """
    try:
        q = (req.prompt or "").lower()

        # detetar exchange
        EXCHANGES = ["Binance", "Coinbase", "Kraken", "Bybit", "Gate.io", "Bitget", "OKX", "MEXC"]
        detected_exchange = None
        for ex in EXCHANGES:
            if ex.lower() in q:
                detected_exchange = ex
                break
        if exchange:
            detected_exchange = exchange

        base = supabase.table("transacted_tokens").select(
            "id, exchange, token, token_address, value_usd, liquidity, volume_24h, "
            "score, pair_url, ts"
        )

        if detected_exchange:
            base = base.eq("exchange", detected_exchange)

        # ordenar e limitar
        resp = (
            base.order("score", desc=True)
                .order("ts", desc=True)
                .limit(10)
        ).execute()

        rows = getattr(resp, "data", []) or []
        if not rows:
            where = f"na {detected_exchange}" if detected_exchange else ""
            return {"answer": f"Nenhum token encontrado {where}."}

        # construir markdown com links
        lines = []
        for r in rows:
            token = r.get("token") or "—"
            ex = r.get("exchange") or "—"
            score = r.get("score")
            score_txt = f"{score:.1f}" if isinstance(score, (int, float)) else "—"

            # links
            pair_url = r.get("pair_url")
            if not pair_url:
                # fallback DexScreener por token (página de search)
                token_addr = r.get("token_address") or ""
                if token_addr:
                    pair_url = f"https://dexscreener.com/solana/{token_addr}"
                else:
                    pair_url = f"https://dexscreener.com/search?q={token}"

            # CoinGecko — usar pesquisa (slug pode não existir)
            coingecko_url = f"https://www.coingecko.com/en/search?query={token}"

            line = f"- **{token}** _( {ex} )_ — **Score:** {score_txt}  \n" \
                   f"  ↳ [DexScreener]({pair_url}) · [CoinGecko]({coingecko_url})"
            lines.append(line)

        where = f"na **{detected_exchange}**" if detected_exchange else ""
        answer = f"**Últimos potenciais listings detetados {where}:**\n\n" + "\n".join(lines)
        return {"answer": answer}

    except Exception as e:
        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}

# ============================
# HEALTHCHECK
# ============================
@app.get("/ping")
def ping():
    return {"status": "ok"}

# ============================
# MAIN
# ============================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
