# -*- coding: utf-8 -*-
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("vigia-api")

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

# CORS relaxado (aperta em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rotas raiz/saúde que o sanity espera ---
@app.get("/")
def root():
    return {"ok": True, "service": "vigia-crypto", "version": "1.0.0"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"api_version": "alerts-v2"}

# --- Startup: registar routers ---
@app.on_event("startup")
def on_startup():
    log.info("🚀 API startup")
    # importa aqui para evitar erros de import antes do app existir
    from .routes.alerts import router as alerts_router
    from .routes.chat import router as chat_router
    from .routes.health import router as health_router
    from .routes import health as health_module

    app.include_router(alerts_router, prefix="")
    app.include_router(chat_router, prefix="")
    app.include_router(health_router, prefix="")
    # injeta app no módulo de health para /__routes
    health_module.routes_app = app
    log.info("✅ Routers registados")

@app.on_event("shutdown")
def on_shutdown():
    log.info("👋 API shutdown")
