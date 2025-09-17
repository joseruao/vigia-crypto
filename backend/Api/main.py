from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# CORS (para permitir requests do frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois podemos trocar por ["http://localhost:3000", "https://joseruao.io"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para o pedido do chat
class ChatRequest(BaseModel):
    prompt: str

# Endpoint do chat (mock)
@app.post("/chat")
def chat(req: ChatRequest):
    return {"answer": f"Recebi a tua mensagem: {req.prompt}"}

# Endpoint de healthcheck
@app.get("/ping")
def ping():
    return {"status": "ok"}

# Endpoint de predictions (mock)
@app.get("/alerts/predictions")
def predictions():
    return [
        {"exchange": "Bitget", "token": "ai16z", "certeza": 95},
        {"exchange": "Binance", "token": "XYZ", "certeza": 92},
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
