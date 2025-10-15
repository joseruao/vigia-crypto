# backend/Api/main.py
# -*- coding: utf-8 -*-

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# importa routers (garante que existem __init__.py em backend/, Api/, routes/)
from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

# CORS (ajusta domains em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(alerts_router, prefix="")
app.include_router(chat_router, prefix="")

@app.get("/ping")
def ping():
    return {"status": "ok"}

# 🔎 rota de prova de vida/versão (usa isto para confirmar que o web está com o código novo)
@app.get("/__version")
def version():
    return {"api_version": "alerts-v2", "desc": "GET/POST /alerts/ask com analysis_text e dedupe"}
