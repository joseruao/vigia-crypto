# backend/Api/routes/chat.py
import os, json, logging, asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
import openai

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger("vigia.chat")

openai.api_key = os.getenv("OPENAI_API_KEY")

async def stream_openai_response(prompt: str):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
            stream=True,
        )
        for chunk in resp:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                yield delta["content"].encode("utf-8")
                await asyncio.sleep(0)
    except Exception as e:
        log.error(f"stream error: {e}")
        yield f"[ERRO]: {str(e)}".encode("utf-8")

@router.post("/stream")
async def chat_stream(request: Request):
    try:
        data = json.loads((await request.body()).decode("utf-8", errors="ignore"))
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error":"Missing prompt"}, status_code=400)
        return StreamingResponse(stream_openai_response(prompt),
                                 media_type="text/plain; charset=utf-8")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/complete")
async def chat_complete(request: Request):
    try:
        data = await request.json()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error":"Missing prompt"}, status_code=400)
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
        )
        text = resp.choices[0].message["content"]
        return JSONResponse({"answer": text})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
