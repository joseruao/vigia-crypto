from __future__ import annotations

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# ---------- logging “amigo do Render” ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("vigia")

# ---------- lifespan (substitui on_event) ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # imprime rotas no arranque
    try:
        routes_info = []
        for r in app.routes:
            if isinstance(r, APIRoute):
                methods = ",".join(sorted(list(r.methods or [])))
                routes_info.append(f" - {r.path} [{methods}]")
        log.info("rotas carregadas:\n%s", "\n".join(routes_info) if routes_info else "(vazio)")
    except Exception as e:
        log.exception("falha a listar rotas: %r", e)
    yield
    log.info("shutdown concluído")

app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

# ---------- CORS ----------
FRONTEND_URL = os.environ.get("FRONTEND_URL") or "https://vigia-crypto-mjfz.vercel.app"
ALLOWED_ORIGINS = [
    FRONTEND_URL.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
# CORREÇÃO: Removido "backend." porque já estamos dentro de backend/
from Api.routes.alerts import router as alerts_router
from Api.routes.chat import router as chat_router
app.include_router(alerts_router)
app.include_router(chat_router)

# ---------- Health & meta ----------
@app.get("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {
        "name": "vigia-backend",
        "version": app.version,
        "commit": os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("COMMIT") or "unknown",
        "ts": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/__routes")
def list_routes() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            out.append({
                "path": r.path,
                "methods": sorted(list(r.methods or [])),
                "name": r.name,
            })
    return sorted(out, key=lambda x: x["path"])

@app.get("/__debug")
def debug():
    import sys
    return {
        "python_version": sys.version,
        "paths": sys.path,
        "current_file": __file__,
        "env_frontend_url": os.environ.get("FRONTEND_URL"),
        "routes_count": len([r for r in app.routes if isinstance(r, APIRoute)])
    }