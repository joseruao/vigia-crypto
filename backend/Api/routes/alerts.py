# backend/Api/routes/alerts.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AskRequest(BaseModel):
    prompt: str

@router.post("/ask")
async def alerts_ask(payload: AskRequest):
    # Placeholder – troca pela tua lógica real de alerts
    return {"answer": f"Alerta-base para: {payload.prompt}"}
