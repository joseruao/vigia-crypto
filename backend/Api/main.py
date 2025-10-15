# backend/Api/main.py
# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router
from .routes.health import router as health_router

app = FastAPI(title="Vigia Crypto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(alerts_router, prefix="")
app.include_router(chat_router, prefix="")
app.include_router(health_router, prefix="")

# injeta a app no health para listar rotas
from .routes import health as health_module
health_module.routes.app = app  # type: ignore

@app.get("/ping")
def ping():
    return {"status": "ok"}
