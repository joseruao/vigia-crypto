import os
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Stream OpenAI com compatibilidade total ---
async def stream_openai_response(prompt: str):
    """Stream de texto contínuo (UTF-8 seguro)."""
    try:
        stream = await client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        async for event in stream:
            if event.type == "message.delta" and event.delta.content:
                yield event.delta.content.encode("utf-8")
                await asyncio.sleep(0)

        await stream.aclose()

    except Exception as e:
        log.error(f"❌ Erro no stream OpenAI: {e}")
        yield f"[ERRO]: {str(e)}".encode("utf-8")


# --- Endpoint /chat/stream ---
@router.post("/stream")
async def chat_stream(request: Request):
    try:
        body = await request.body()
        data = json.loads(body.decode("utf-8", errors="ignore"))
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟢 CHAT prompt recebido: {prompt[:100]}...")
        return StreamingResponse(
            stream_openai_response(prompt),
            media_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        log.error(f"💥 Falha no /chat/stream: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Endpoint /chat/complete (JSON normal, não stream) ---
@router.post("/complete")
async def chat_complete(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
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
        log.error(f"💥 Falha no /chat/complete: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
