# backend/Api/main.py
from __future__ import annotations
import os, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

ALLOWED_ORIGINS = {
    FRONTEND_URL,
    "http://localhost:3000",
    "https://joseruao.com",
    "https://www.joseruao.com",
    "https://joseruao.vercel.app",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Vigia API a iniciar")
    yield
    log.info("🛑 Vigia API a encerrar")

app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
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

# Routers
from Api.routes.alerts import router as alerts_router
app.include_router(alerts_router, prefix="")

@app.get("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.0"}
