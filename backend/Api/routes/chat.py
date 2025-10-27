# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
import os
import openai
import json
import asyncio
import logging

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

# ========================
# CONFIGURAÇÃO
# ========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY não definido")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ========================
# OPTIONS UNIVERSAL (CORS preflight)
# ========================
@router.options("/{path:path}")
async def options_handler():
    """Responde 200 a todos os preflights OPTIONS para evitar 405"""
    return PlainTextResponse("ok", status_code=200)

# ========================
# /chat/stream (streaming)
# ========================
@router.post("/stream")
async def chat_stream(request: Request):
    """
    Endpoint de streaming contínuo (text/plain)
    Retorna chunks em tempo real com respostas do modelo
    """
    try:
        data = await request.json()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟢 Novo pedido de stream: {prompt[:80]}...")

        async def generate():
            yield f"Recebi: {prompt}\nA gerar resposta...\n\n"
            try:
                stream = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "És o assistente do Vigia Crypto."},
                            {"role": "user", "content": prompt},
                        ],
                        stream=True,
                    )
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                yield "\n\n✅ [fim da resposta]"
            except Exception as e:
                log.error(f"❌ Erro no stream: {e}")
                yield f"\n[Erro interno: {e}]"

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        log.error(f"❌ CHAT STREAM ERROR: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ========================
# /chat/complete (resposta única)
# ========================
@router.post("/complete")
async def chat_complete(request: Request):
    """
    Endpoint simples — devolve resposta completa (sem stream)
    """
    try:
        data = await request.json()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "Missing prompt"}, status_code=400)

        log.info(f"🟡 Novo pedido completo: {prompt[:80]}...")

        completion = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "És o assistente do Vigia Crypto."},
                    {"role": "user", "content": prompt},
                ],
            )
        )

        answer = completion.choices[0].message.content.strip()
        return JSONResponse({"answer": answer})

    except Exception as e:
        log.error(f"❌ CHAT COMPLETE ERROR: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
