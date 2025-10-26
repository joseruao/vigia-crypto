# backend/Api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/ping")
def ping():
    return {"status": "ok"}

@router.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.0"}
