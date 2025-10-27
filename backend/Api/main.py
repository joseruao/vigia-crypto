# backend/Api/main.py
from __future__ import annotations

import os
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ========== DEBUG INICIAL ==========
print("=== DEBUG START ===")
print("Python path:", sys.path)
print("Current directory:", os.getcwd())
print("FRONTEND_URL:", os.environ.get("FRONTEND_URL"))
print("SUPABASE_URL:", os.environ.get("SUPABASE_URL"))
print("=== DEBUG END ===")

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

# ========== LIFESPAN ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Aplicação a iniciar...")
    yield
    log.info("🔴 Aplicação a encerrar...")

app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

# ========== CORS ==========
# Usa domínio único de produção. Mantém localhost p/ dev.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
ALLOWED_ORIGINS = {
    FRONTEND_URL,
    "http://localhost:3000",
    "https://joseruao.com",
    "https://www.joseruao.com",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== HEADERS úteis p/ streaming ==========
@app.middleware("http")
async def add_no_buffering_headers(request: Request, call_next):
    resp = await call_next(request)
    # Evita buffering em alguns proxies e cache agressivo
    resp.headers.setdefault("X-Accel-Buffering", "no")
    resp.headers.setdefault("Cache-Control", "no-cache")
    return resp

# ========== IMPORT DE ROTAS ==========
try:
    from Api.routes.alerts import router as alerts_router
    from Api.routes.chat import router as chat_router
    from Api.routes.health import router as health_router

    app.include_router(alerts_router)
    app.include_router(chat_router)
    app.include_router(health_router)

    log.info("✅ Routers carregados com sucesso.")
except Exception as e:
    log.error(f"❌ Erro ao carregar routers: {e}")

# ========== ROTAS DE SANITY ==========
@app.get("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.0"}

# ========== ARRANQUE ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    log.info(f"🚀 A arrancar Uvicorn na porta {port}")
    uvicorn.run("Api.main:app", host="0.0.0.0", port=port, log_level="info")
