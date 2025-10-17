from __future__ import annotations

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- App ---
app = FastAPI(title="Vigia API", version="0.1.0")

# CORS: autoriza o teu frontend em Vercel e fallback para dev
VERCEL_ORIGIN = os.environ.get("NEXT_PUBLIC_SITE_URL") or "https://vigia-crypto-mjfz.vercel.app"
ALLOWED_ORIGINS = [
    VERCEL_ORIGIN.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",  # podes remover * quando estiveres confiante
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router

app.include_router(alerts_router)
app.include_router(chat_router)


# --- Health/Meta ---
@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    """
    Exibe info básica de versão/commit se existir.
    Render define RENDER_GIT_COMMIT em alguns ambientes.
    """
    return {
        "name": "vigia-backend",
        "version": app.version,
        "commit": os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("COMMIT") or "unknown",
        "ts": datetime.utcnow().isoformat() + "Z",
    }
