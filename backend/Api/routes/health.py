# -*- coding: utf-8 -*-
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
import importlib

router = APIRouter(tags=["health"])
routes_app: FastAPI | None = None  # será injetado pelo main

@router.get("/__version")
def version():
    return {"api_version": "alerts-v2", "desc": "tem /alerts/ask GET e POST com analysis_text e dedupe"}

@router.get("/debug/deps")
def debug_deps():
    mods = ["httpx", "httpcore", "supabase", "gotrue", "postgrest", "realtime", "storage3", "fastapi", "uvicorn", "openai"]
    out = {}
    for m in mods:
        try:
            mod = importlib.import_module(m)
            out[m] = getattr(mod, "__version__", "unknown")
        except Exception as e:
            out[m] = f"ERR: {e}"
    return out

@router.get("/__routes")
def list_routes():
    assert routes_app is not None, "app não injetada"
    items = []
    for r in routes_app.routes:
        if isinstance(r, APIRoute):
            items.append({"path": r.path, "methods": sorted(list(r.methods))})
    return items
