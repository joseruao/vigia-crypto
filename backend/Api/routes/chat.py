# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
import os, asyncio, json
import httpx
from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Cliente HTTP com timeout (evita pendurar)
_http = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0, read=15.0, write=15.0))
client = AsyncOpenAI(api_key=OPENAI_KEY, http_client=_http) if OPENAI_KEY else None

def parse_json_safely(raw: bytes) -> dict:
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))

async def safe_openai_completion(messages):
    if not client:
        return "⚠️ OPENAI_API_KEY ausente."
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=False,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"⚠️ Modo seguro: não consegui falar com o modelo ({e})."

async def stream_openai(prompt: str):
    # fallback imediato se não houver client
    if not client:
        yield "⚠️ OPENAI_API_KEY ausente."
        return
    try:
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
        # nunca quebrar stream; devolve fallback e termina
        yield f"\n⚠️ Modo seguro: falha ao streamar ({e})."

@router.post("/stream")
async def chat_stream(request: Request):
    try:
        try:
            data = await request.json()
        except Exception:
            body = await request.body()
            print("🟠 RAW BODY:", body)
            data = parse_json_safely(body) if body else {}
        prompt = (data.get("prompt") or "").trim() if hasattr("", "trim") else (data.get("prompt") or "").strip()
        print("🟢 PROMPT:", prompt)

        if not prompt:
            return PlainTextResponse("⚠️ Prompt vazio ou inválido.", status_code=400)

        return StreamingResponse(stream_openai(prompt), media_type="text/plain")
    except Exception as e:
        # garantir que nunca devolvemos 503 “no response”
        print("❌ CHAT STREAM ERROR:", str(e))
        return PlainTextResponse(f"⚠️ Erro: {str(e)}", status_code=200)

@router.post("/complete")
async def chat_complete(request: Request):
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

        text = await safe_openai_completion([{"role": "user", "content": prompt}])
        return JSONResponse({"answer": text}, status_code=200)
    except Exception as e:
        # nunca 503
        print("❌ OpenAI complete error:", str(e))
        return JSONResponse({"answer": f"⚠️ Modo seguro: erro interno ({e})."}, status_code=200)
