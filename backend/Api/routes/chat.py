# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
import os
import asyncio
import json
from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])

# === CONFIG ===
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_KEY)


async def stream_openai(prompt: str):
    """Stream da resposta do OpenAI (modelo GPT-4o-mini)."""
    try:
        print(f"🧠 OpenAI request: {prompt[:80]}...")

        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if "content" in delta:
                yield delta.content
                await asyncio.sleep(0)

    except Exception as e:
        print("❌ OpenAI stream error:", str(e))
        yield f"\n⚠️ Erro interno no modelo: {str(e)}"


@router.post("/stream")
async def chat_stream(request: Request):
    """Endpoint de streaming do chat (usado pelo ChatWindow)."""
    try:
        # --- parsing seguro do corpo ---
        try:
            data = await request.json()
        except Exception:
            body = await request.body()
            print("🟠 RAW BODY:", body)
            try:
                data = json.loads(body.decode("utf-8"))
            except UnicodeDecodeError:
                data = json.loads(body.decode("latin-1"))

        print("🟡 DATA RECEIVED:", data)
        prompt = data.get("prompt", "").strip()
        print("🟢 PROMPT:", prompt)

        if not prompt:
            return PlainTextResponse("⚠️ Prompt vazio ou inválido.", status_code=400)

        # --- stream normal ---
        return StreamingResponse(stream_openai(prompt), media_type="text/plain")

    except Exception as e:
        print("❌ CHAT STREAM ERROR:", str(e))
        return PlainTextResponse(f"⚠️ Erro: {str(e)}", status_code=500)
