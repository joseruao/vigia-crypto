# backend/Api/main.py
# -*- coding: utf-8 -*-

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # em produção: restringir
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
