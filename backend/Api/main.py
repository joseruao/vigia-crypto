from __future__ import annotations

import os
import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Dict, List

# ========== DEBUG ==========
print("=== DEBUG START ===")
print("Python path:", sys.path)
print("Current directory:", os.getcwd())
print("=== DEBUG END ===")

# ---------- logging ----------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Application starting up...")
    yield
    log.info("🔴 Application shutting down...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

# ---------- CORS ----------
FRONTEND_URL = os.environ.get("FRONTEND_URL")
if not FRONTEND_URL:
    raise RuntimeError("❌ FRONTEND_URL não definido no ambiente")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
try:
    from Api.routes.alerts import router as alerts_router
    from Api.routes.chat import router as chat_router
    app.include_router(alerts_router)
    app.include_router(chat_router)
    print("✅ Routers loaded successfully")
except Exception as e:
    print(f"❌ Router error: {e}")

# ---------- Routes ----------
@app.get("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.0"}

print("=== STARTING SERVER ===")

# ========== ESSENTIAL: Start the server ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Uvicorn on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")