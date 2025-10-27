# backend/Api/routes/chat.py
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    prompt: str

@router.post("/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    """
    Stream de texto simples (não-SSE). O frontend lê com ReadableStream.
    """
    text = f"Recebi: {payload.prompt}\nA gerar resposta...\n"

    async def gen() -> AsyncGenerator[bytes, None]:
        for ch in text:
            # Aqui podes ligar ao teu LLM e ir dando yield de chunks
            yield ch.encode("utf-8")
            # opcional: await asyncio.sleep(0.002)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # evita buffering em proxies
    }
    return StreamingResponse(gen(), media_type="text/plain", headers=headers)
