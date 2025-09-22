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
@app.get("/alerts/predictions")
def predictions():
    """
    Endpoint mock (pode depois ligar à base real).
    """
    return [
        {"exchange": "Bitget", "token": "ai16z", "certeza": 95},
        {"exchange": "Binance", "token": "XYZ", "certeza": 92},
    ]

@app.post("/alerts/ask")
def ask_alerts(req: ChatRequest, exchange: Optional[str] = Query(None)):
    """
    Responde a perguntas sobre tokens detectados no Supabase.
    - Se o prompt mencionar uma exchange, filtra só dessa.
    - Caso contrário, devolve os 10 tokens mais recentes por score.
    """
    try:
        q = req.prompt.lower()
        detected_exchange = None

        for ex in EXCHANGES:
            if ex.lower() in q:
                detected_exchange = ex
                break
        if exchange:
            detected_exchange = exchange

        base_query = supabase.table("transacted_tokens").select("*")
        if detected_exchange:
            base_query = base_query.eq("exchange", detected_exchange)

        resp = (
            base_query.order("score", desc=True)
            .order("ts", desc=True)
            .limit(10)
            .execute()
        )

        data = getattr(resp, "data", [])
        if not data:
            return {
                "answer": f"Nenhum token encontrado {f'na {detected_exchange}' if detected_exchange else ''}."
            }

        tokens = [
            f"{row['token']} ({row['exchange']}, score {row.get('score', 0)})"
            for row in data
        ]

        return {
            "answer": f"Os últimos potenciais listings detetados {f'na {detected_exchange}' if detected_exchange else ''}:\n- "
            + "\n- ".join(tokens)
        }

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
