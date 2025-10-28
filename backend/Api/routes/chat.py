# backend/Api/routes/chat.py
import os
import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PT = {
    "role": "system",
    "content": "Responde em PT-PT, direto ao assunto."
}

# ============ STREAM ============
async def stream_openai_response(prompt: str) -> AsyncGenerator[bytes, None]:
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[SYSTEM_PT, {"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and getattr(delta, "content", None):
                    yield delta.content.encode("utf-8")
                    await asyncio.sleep(0)
            except Exception:
                pass
    except Exception as e:
        log.error(f"❌ stream_openai_response: {e}")
        yield f"[ERRO]: {e}".encode("utf-8")

@router.post("/stream")
async def chat_stream(request: Request):
    try:
        raw = await request.body()
        data = json.loads(raw.decode("utf-8", errors="ignore"))
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟢 /chat/stream: {prompt[:120]}...")
        return StreamingResponse(
            stream_openai_response(prompt),
            media_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        log.error(f"💥 /chat/stream exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============ COMPLETE ============
@router.post("/complete")
async def chat_complete(request: Request):
    try:
        # ⚠️ Não uses request.json() por causa de encoding no PowerShell
        raw = await request.body()
        data = json.loads(raw.decode("utf-8", errors="ignore"))
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        # (A) tentativa normal
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[SYSTEM_PT, {"role": "user", "content": prompt}],
                temperature=0.7,
            )
            text = None
            try:
                text = resp.choices[0].message.content
            except Exception:
                pass
            if not text:
                try:
                    text = getattr(resp.choices[0], "text", None)
                except Exception:
                    pass
            if not text:
                text = "Sem resposta."
            return JSONResponse({"answer": text})
        except Exception as inner:
            log.warning(f"⚠️ complete normal falhou, fallback: {inner}")

        # (B) fallback: usa o mesmo fluxo de stream e concatena
        acc = []
        async for chunk in stream_openai_response(prompt):
            try:
                acc.append(chunk.decode("utf-8", errors="ignore"))
            except Exception:
                pass
        return JSONResponse({"answer": ("".join(acc).strip() or "Sem resposta.")})

    except Exception as e:
        log.error(f"💥 /chat/complete exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
