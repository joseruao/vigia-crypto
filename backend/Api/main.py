# Api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# importa o router das rotas
from .routes.alerts import router as alerts_router

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

# CORS: abre para o teu frontend (ajusta se quiseres afunilar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # ou ["https://o_teu_dominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# healthcheck básico
@app.get("/ping")
def ping():
    return {"status": "ok"}

# regista rotas
app.include_router(alerts_router)
