# backend/Api/main.py
from __future__ import annotations

import os
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

print("=== DEBUG START ===")
print("Python path:", sys.path)
print("Current directory:", os.getcwd())
print("FRONTEND_URL:", os.environ.get("FRONTEND_URL"))
print("SUPABASE_URL:", os.environ.get("SUPABASE_URL"))
print("=== DEBUG END ===")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Aplicação a iniciar...")
    yield
    log.info("🔴 Aplicação a encerrar...")

app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

# CORS: abre tudo para já
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ← depois fechamos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_buffering_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Accel-Buffering", "no")
    resp.headers.setdefault("Cache-Control", "no-cache")
    return resp

# rotas
from Api.routes.alerts import router as alerts_router
app.include_router(alerts_router)

@app.get("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    log.info(f"🚀 A arrancar Uvicorn na porta {port}")
    uvicorn.run("Api.main:app", host="0.0.0.0", port=port, log_level="info")
