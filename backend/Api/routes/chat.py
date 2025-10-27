# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
import os, asyncio, json
from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

async def stream_openai(prompt: str):
    try:
        if not client:
            yield "⚠️ OPENAI_API_KEY ausente no servidor."
            return
        print(f"🧠 OpenAI request: {prompt[:120]}...")
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

def parse_json_safely(raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))

@router.post("/stream")
async def chat_stream(request: Request):
    try:
        try:
            data = await request.json()
        except Exception:
            body = await request.body()
            print("🟠 RAW BODY:", body)
            data = parse_json_safely(body) if body else {}
        print("🟡 DATA RECEIVED:", data)
        prompt = (data.get("prompt") or "").strip()
        print("🟢 PROMPT:", prompt)

        if not prompt:
            return PlainTextResponse("⚠️ Prompt vazio ou inválido.", status_code=400)

        return StreamingResponse(stream_openai(prompt), media_type="text/plain")
    except Exception as e:
        print("❌ CHAT STREAM ERROR:", str(e))
        return PlainTextResponse(f"⚠️ Erro: {str(e)}", status_code=500)

@router.post("/complete")
async def chat_complete(request: Request):
    """Alternativa sem stream — útil para debug rápido."""
    try:
        try:
            data = await request.json()
        except Exception:
            body = await request.body()
            print("🟠 RAW BODY:", body)
            data = parse_json_safely(body) if body else {}
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "prompt vazio"}, status_code=400)
        if not client:
            return JSONResponse({"error": "OPENAI_API_KEY ausente"}, status_code=500)

        print(f"🧠 OpenAI non-stream: {prompt[:120]}...")
        comp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        text = comp.choices[0].message.content or ""
        return JSONResponse({"answer": text})
    except Exception as e:
        print("❌ OpenAI complete error:", str(e))
        return JSONResponse({"error": str(e)}, status_code=500)
