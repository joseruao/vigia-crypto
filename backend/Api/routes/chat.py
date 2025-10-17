from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat", tags=["chat"])

async def _read_json(request: Request) -> Dict[str, Any]:
    # Aceita JSON e, se vier vazio, devolve prompt vazio (para não dar 400 na tua UI)
    try:
        if request.headers.get("content-type", "").lower().startswith("application/json"):
            data = await request.json()
            if not isinstance(data, dict):
                return {}
            return data
        # fallback: corpo cru
        raw = (await request.body()) or b""
        return {} if not raw else {"prompt": raw.decode("utf-8", errors="ignore")}
    except Exception:
        return {}

@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    data = await _read_json(request)
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        prompt = "…"

    text = f"Eco: {prompt}\n(este é um stream de teste do backend)"
    async def gen() -> AsyncGenerator[bytes, None]:
        for chunk in [text[i:i+24] for i in range(0, len(text), 24)]:
            await asyncio.sleep(0.05)
            yield chunk.encode("utf-8")
    return StreamingResponse(gen(), media_type="text/plain")
