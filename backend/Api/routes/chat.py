# backend/Api/routes/chat.py
import os
import json
import logging
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

# Cliente compatível com openai==1.45.0
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# Função para stream de mensagens
# -------------------------------
async def stream_openai_response(prompt: str):
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.7,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content.encode("utf-8")
                await asyncio.sleep(0)
    except Exception as e:
        log.error(f"❌ Erro stream_openai_response: {e}")
        yield f"[ERRO]: {e}".encode("utf-8")

# -------------------------------
# Endpoint de stream (text/plain)
# -------------------------------
@router.post("/stream")
async def chat_stream(request: Request):
    try:
        raw = await request.body()
        data = json.loads(raw.decode("utf-8", errors="ignore"))
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟢 /chat/stream: {prompt[:100]}...")

        return StreamingResponse(
            stream_openai_response(prompt),
            media_type="text/plain; charset=utf-8",
        )

    except Exception as e:
        log.error(f"💥 /chat/stream exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# -------------------------------
# Endpoint JSON normal
# -------------------------------
@router.post("/complete")
async def chat_complete(request: Request):
    try:
        data = await request.json()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        text = resp.choices[0].message.content
        return JSONResponse({"answer": text})
    except Exception as e:
        log.error(f"💥 /chat/complete exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
