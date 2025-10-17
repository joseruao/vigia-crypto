from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Dict, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/chat", tags=["chat"])

async def _read_json(request: Request) -> Dict[str, Any]:
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        
        if "application/json" in content_type:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        
        # Tenta ler como texto plano
        raw_body = await request.body()
        if raw_body:
            try:
                # Tenta parse como JSON
                data = json.loads(raw_body.decode('utf-8'))
                return data if isinstance(data, dict) else {"prompt": raw_body.decode('utf-8')}
            except json.JSONDecodeError:
                # Se não for JSON, usa como prompt direto
                return {"prompt": raw_body.decode('utf-8')}
        
        return {}
    except Exception as e:
        print(f"Erro a ler body: {e}")
        return {}

@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    data = await _read_json(request)
    prompt = str(data.get("prompt") or "").strip()
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt é obrigatório")

    msg = f"Eco: {prompt}\n(backend a streamar ok)"
    
    async def gen() -> AsyncGenerator[bytes, None]:
        for i in range(0, len(msg), 5):
            await asyncio.sleep(0.05)
            chunk = msg[i:i+5]
            yield chunk.encode("utf-8")

    return StreamingResponse(
        gen(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )