# backend/Api/main.py
from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # ajusta se precisares restringir domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.on_event("startup")
def on_startup():
    logger.info("🚀 API startup")
    # Import aqui é seguro; alerts.py já não rebenta no import
    from .routes import alerts
    app.include_router(alerts.router)
    logger.info("✅ Routers registados")
