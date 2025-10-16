# backend/Api/main.py
from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta se precisares
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

# Registo de routers no startup para ter logs bonitos,
# mas importar aqui também é ok (alerts.py já é safe com lazy init)
@app.on_event("startup")
def on_startup():
    logger.info("🚀 API startup")
    from .routes.alerts import router as alerts_router
    app.include_router(alerts_router)
    logger.info("✅ Routers registados")
