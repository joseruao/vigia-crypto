from __future__ import annotations

import os
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from starlette.requests import Request

app = FastAPI(title="Vigia API", version="0.1.0")

# ---- CORS ----
VERCEL_ORIGIN = os.environ.get("NEXT_PUBLIC_SITE_URL") or "https://vigia-crypto-mjfz.vercel.app"
ALLOWED_ORIGINS = [
    VERCEL_ORIGIN.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",  # remove quando estiveres confiante
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers de negócio ----
from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router

app.include_router(alerts_router)
app.include_router(chat_router)

# ---- Meta / Health ----
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
    """
    Lista todas as rotas carregadas na app (para debug).
    """
    out: List[Dict[str, Any]] = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            out.append({
                "path": r.path,
                "methods": sorted(list(r.methods or [])),
                "name": r.name,
            })
    return sorted(out, key=lambda x: x["path"])

# ---- Log no arranque com as rotas (aparece nos logs do Render) ----
@app.on_event("startup")
async def _log_routes_on_startup():
    try:
        lines = ["[vigia] rotas carregadas:"]
        for r in app.routes:
            if isinstance(r, APIRoute):
                methods = ",".join(sorted(list(r.methods or [])))
                lines.append(f" - {r.path} [{methods}]")
        print("\n".join(lines))
    except Exception as e:
        print("[vigia] falha a listar rotas:", repr(e))

# Não precisamos de uvicorn.run aqui; o Render arranca o servidor ao executar `python -m backend.Api.main`.
