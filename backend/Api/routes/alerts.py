# backend/Api/routes/alerts.py
# -*- coding: utf-8 -*-
import json
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional, Dict, Any

from Api.services.db import fetch_alerts
from Api.services.summaries import items_to_markdown

router = APIRouter(prefix="/alerts", tags=["alerts"])

async def read_loose_body(request: Request) -> Dict[str, Any]:
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        return await request.json()
    raw = (await request.body()) or b""
    text = raw.decode("utf-8", errors="ignore").strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    if text:
        return {"prompt": text}
    raise HTTPException(status_code=400, detail="Body vazio ou inválido")

@router.post("/ask")
async def ask_alerts(request: Request, exchange: Optional[str] = Query(default=None)) -> dict:
    try:
        data = await read_loose_body(request)
        prompt_val = data.get("prompt") or ""
        prompt = str(prompt_val).strip()
        ex = data.get("exchange") or exchange
        if not prompt:
            raise HTTPException(status_code=400, detail="Falta 'prompt'.")
        
        rows, _ = fetch_alerts(exchange=ex, limit=25)
        answer = items_to_markdown(rows)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"⚠️ Erro ao processar: {str(e)}"}

@router.get("/predictions")
def get_predictions(limit: int = 10, exchange: Optional[str] = None):
    try:
        rows, _ = fetch_alerts(exchange=exchange, limit=limit)
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
