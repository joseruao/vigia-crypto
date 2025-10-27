# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
import os
import openai
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])

# Configurar chave do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Função geradora de stream (para FastAPI)
async def stream_openai(prompt: str):
    """
    Gera resposta em stream a partir do OpenAI (GPT-4-mini).
    Cada chunk é enviado diretamente para o frontend.
    """
    try:
        client = openai.AsyncOpenAI(api_key=openai.api_key)

        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if "content" in delta:
                yield delta.content
                await asyncio.sleep(0)  # liberta o loop event
    except Exception as e:
        yield f"\n⚠️ Erro: {str(e)}"


@router.post("/stream")
async def chat_stream(request: Request):
    """
    Endpoint principal do ChatWindow.
    Retorna stream de texto contínuo.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return PlainTextResponse("⚠️ Prompt vazio.", status_code=400)

        return StreamingResponse(stream_openai(prompt), media_type="text/plain")

    except Exception as e:
        return PlainTextResponse(f"⚠️ Erro: {str(e)}", status_code=500)
