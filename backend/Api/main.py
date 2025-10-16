# backend/Api/main.py
from __future__ import annotations
import os, time
from fastapi import FastAPI

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

@app.get("/__version")
def version():
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "")[:7],
        "ts": int(time.time()),
    }

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.on_event("startup")
def on_startup():
    from .routes.alerts import router as alerts_router
    from .routes.health import router as health_router  # se já existe
    app.include_router(health_router)
    app.include_router(alerts_router)
