# -*- coding: utf-8 -*-
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# logging ruidoso para ver arranque no Render
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("vigia-api")

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# == Endpoints básicos para sanity e evitar 503 ==
@app.get("/")
def root():
    return {"ok": True, "service": "vigia-crypto", "version": "1.0.0"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"api_version": "alerts-v2", "desc": "tem /alerts/ask GET e POST com analysis_text e dedupe"}

# == Routers (importes tardios para evitar falhas no cold start) ==
@app.on_event("startup")
def on_startup():
    log.info("🚀 API startup")
    # importa routers só quando tudo está carregado
    from .routes.alerts import router as alerts_router
    from .routes.chat import router as chat_router
    from .routes.health import router as health_router

    app.include_router(alerts_router, prefix="")
    app.include_router(chat_router, prefix="")
    app.include_router(health_router, prefix="")
    # injeta app no health p/ listar rotas
    from .routes import health as health_module
    health_module.routes_app = app  # type: ignore
    log.info("✅ Routers registados")

@app.on_event("shutdown")
def on_shutdown():
    log.info("👋 API shutdown")
