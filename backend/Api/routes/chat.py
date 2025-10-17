# backend/Api/routes/chat.py
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter(tags=["chat"])

@router.post("/chat")
async def chat_plain(req: Request):
    data = await req.json()
    prompt = (data.get("prompt") or "").strip()
    return {"answer": f"Eco: {prompt}"}

@router.post("/chat/stream")
async def chat_stream(req: Request):
    data = await req.json()
    prompt = (data.get("prompt") or "").strip()

    async def gen():
        text = f"Eco (stream): {prompt}"
        for i in range(0, len(text), 8):
            await asyncio.sleep(0.05)
            yield text[i:i+8]

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
