from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    _env_path = BACKEND_DIR / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("devil")

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
ALLOWED_ORIGINS = {
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://joseruao.com",
    "https://www.joseruao.com",
    "https://joseruao.vercel.app",
}

app = FastAPI(title="Devil's Advocate API", version="1.0.0")

app.add_middleware(
    StarletteCORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://joseruao\.com|https://www\.joseruao\.com|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True, "status": "healthy"}


from Api.routes.devils_advocate import router as devils_advocate_router

app.include_router(devils_advocate_router, prefix="")
