# Api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, time

from .routes.alerts import router as alerts_router
# (se tiveres mais routers, importa e inclui aqui)

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ou substitui pelo domínio do Vercel para fechar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
        "ts": int(time.time()),
    }

app.include_router(alerts_router)
