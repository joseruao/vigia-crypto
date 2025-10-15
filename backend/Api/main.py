# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.alerts import router as alerts_router
from .routes.chat import router as chat_router
from .routes.health import router as health_router

app = FastAPI(title="Vigia Crypto API", version="1.0.0"
