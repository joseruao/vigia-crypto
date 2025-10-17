from __future__ import annotations

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from .routes import alerts

log = logging.getLogger(__name__)

app = FastAPI(
    title="Vigia Crypto API",
    version=os.environ.get("GIT_SHA", "dev"),
)

# CORS relaxado: front no Vercel a chamar backend no Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # se quiseres, mete aqui o domínio do Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health + meta
@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    # Mostra a versão que o Render injeta (env) ou "dev"
    return {"version": os.environ.get("GIT_SHA", "dev")}

# Home simples (evita 404 no /)
@app.get("/")
def root():
    return {"status": "ok"}

# Endpoints da app
app.include_router(alerts.router)


# --- Execução local/Render (opção robusta) ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Render injeta PORT
    uvicorn.run("backend.Api.main:app", host="0.0.0.0", port=port, reload=False)
