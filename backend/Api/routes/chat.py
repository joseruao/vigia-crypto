# backend/Api/routes/chat.py
import os
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
import openai
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Helper para stream async ---
async def stream_openai_response(prompt: str):
    """Stream de texto contínuo (UTF-8 seguro)."""
    try:
        stream = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.7,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.get("content"):
                yield delta["content"].encode("utf-8")
                await asyncio.sleep(0)
    except Exception as e:
        log.error(f"❌ Erro no stream OpenAI: {e}")
        yield f"\n[ERRO]: {str(e)}".encode("utf-8")

# --- Endpoint /chat/stream ---
@router.post("/stream")
async def chat_stream(request: Request):
    try:
        body = await request.body()
        try:
            data = json.loads(body.decode("utf-8", errors="ignore"))
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        prompt = data.get("prompt", "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟢 CHAT prompt recebido: {prompt[:80]}...")
        return StreamingResponse(stream_openai_response(prompt),
                                 media_type="text/plain; charset=utf-8")
    except Exception as e:
        log.error(f"💥 Falha geral no /chat/stream: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Endpoint /chat/complete (resposta JSON normal) ---
@router.post("/complete")
async def chat_complete(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        resp = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = resp.choices[0].message.content
        return JSONResponse({"answer": text})
    except Exception as e:
        log.error(f"💥 Falha no /chat/complete: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
