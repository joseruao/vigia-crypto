# backend/Api/routes/health.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter
import importlib

router = APIRouter(tags=["health"])

@router.get("/__version")
def version():
    return {"api_version": "alerts-v2", "desc": "tem /alerts/ask GET e POST com analysis_text e dedupe"}

@router.get("/debug/deps")
def debug_deps():
    mods = ["httpx", "supabase", "gotrue", "postgrest", "realtime", "storage3", "fastapi", "uvicorn"]
    out = {}
    for m in mods:
        try:
            mod = importlib.import_module(m)
            out[m] = getattr(mod, "__version__", "unknown")
        except Exception as e:
            out[m] = f"ERR: {e}"
    return out

@router.get("/__routes")
def routes():
    # devolve caminhos para confirmar o que está carregado
    from fastapi import FastAPI
    from fastapi.routing import APIRoute
    app: FastAPI = routes.app  # injetado pelo main
    items = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            items.append({"path": r.path, "methods": sorted(list(r.methods))})
    return items
