from __future__ import annotations

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import alerts

log = logging.getLogger(__name__)

app = FastAPI(
    title="Vigia Crypto API",
    version=os.environ.get("GIT_SHA", "dev"),
)

# CORS para o front no Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # se quiseres, restringe ao domínio Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    # Marcador explícito para sabermos que este ficheiro está live
    return {
        "version": os.environ.get("GIT_SHA", "dev"),
        "marker": "main.v3"  # <--- MARCADOR 1
    }

@app.get("/")
def root():
    return {"status": "ok", "marker": "root.v3"}  # <--- MARCADOR 2

# Rotas do módulo alerts
app.include_router(alerts.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.Api.main:app", host="0.0.0.0", port=port, reload=False)
