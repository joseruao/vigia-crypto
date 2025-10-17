# backend/Api/main.py
from __future__ import annotations

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vigia Crypto API", version=os.environ.get("RELEASE", "dev"))

# CORS amplo para Vercel/localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # se quiseres, troca por o teu domínio Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# registo de routers só quando a app arranca
@app.on_event("startup")
def on_startup():
    print("🚀 API startup")
    # importa aqui para evitar falhas no import inicial
    from .routes.alerts import router as alerts_router
    from .routes.chat import router as chat_router  # cria já um chat básico opcional, ver abaixo
    app.include_router(alerts_router)
    app.include_router(chat_router)

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/")
def root():
    return {
        "name": "Vigia Crypto API",
        "version": app.version,
        "routes": [
            "/", "/ping", "/__version", "/__routes",
            "/openapi.json", "/alerts/ask", "/alerts/predictions",
            "/chat", "/chat/stream"
        ],
    }

@app.get("/__routes")
def __routes():
    return [r.path for r in app.routes]

@app.get("/__version")
def __version():
    return {
        "version": app.version,
        "python": os.environ.get("PYTHON_VERSION", "unknown"),
        "ts": datetime.utcnow().isoformat() + "Z",
        "commit": os.environ.get("RENDER_GIT_COMMIT", None),
    }
