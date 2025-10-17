from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat", tags=["chat"])

async def _read_json(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError
        return data
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido (esperado JSON object)")

@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    """
    Stream 'cru' (text/plain) em pequenos pedaços.
    Isto é um 'stub' para a tua UI não rebentar com 400.
    Substitui depois por chamada ao teu LLM.
    """
    data = await _read_json(request)
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Falta 'prompt'.")

    text = f"Eco: {prompt}\n(este é um stream de teste do backend)"
    async def gen() -> AsyncGenerator[bytes, None]:
        for chunk in [text[i:i+24] for i in range(0, len(text), 24)]:
            await asyncio.sleep(0.05)  # simula latência
            yield chunk.encode("utf-8")
    return StreamingResponse(gen(), media_type="text/plain")
