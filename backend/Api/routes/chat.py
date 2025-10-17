from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat", tags=["chat"])

async def _read_json(request: Request) -> Dict[str, Any]:
    try:
        if (request.headers.get("content-type") or "").lower().startswith("application/json"):
            data = await request.json()
            return data if isinstance(data, dict) else {}
        raw = (await request.body()) or b""
        return {} if not raw else {"prompt": raw.decode("utf-8", errors="ignore")}
    except Exception:
        return {}

@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    data = await _read_json(request)
    prompt = str(data.get("prompt") or "").strip() or "…"

    msg = f"Eco: {prompt}\n(backend a streamar ok)"
    async def gen() -> AsyncGenerator[bytes, None]:
        for i in range(0, len(msg), 24):
            await asyncio.sleep(0.03)
            yield msg[i:i+24].encode("utf-8")

    return StreamingResponse(gen(), media_type="text/plain")
