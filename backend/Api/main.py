from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
from openai import OpenAI
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# CORS (para permitir requests do frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção trocar por ["http://localhost:3000", "https://joseruao.io"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo do pedido do chat
class ChatRequest(BaseModel):
    prompt: str

# Endpoint /chat (resposta única, sem streaming)
@app.post("/chat")
def chat(req: ChatRequest):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # podes trocar por "gpt-4o" se quiseres qualidade máxima
        messages=[
            {"role": "system", "content": "Tu és um assistente especializado em criptomoedas."},
            {"role": "user", "content": req.prompt},
        ],
    )
    return {"answer": completion.choices[0].message.content}

# Endpoint /chat/stream (resposta em streaming)
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
                    yield event.delta  # devolve apenas o texto
                elif event.type == "error":
                    yield f"⚠️ Erro: {event.error}"
            stream.close()

    return StreamingResponse(generate(), media_type="text/plain")

# Healthcheck
@app.get("/ping")
def ping():
    return {"status": "ok"}

# Predictions (mock, para já estático)
@app.get("/alerts/predictions")
def predictions():
    return [
        {"exchange": "Bitget", "token": "ai16z", "certeza": 95},
        {"exchange": "Binance", "token": "XYZ", "certeza": 92},
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
