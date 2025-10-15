# -*- coding: utf-8 -*-
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
import os

router = APIRouter(tags=["chat"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat")
def chat(req: ChatRequest):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu és um assistente especializado em criptomoedas."},
            {"role": "user", "content": req.prompt},
        ],
    )
    return {"answer": completion.choices[0].message.content}

@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def generate():
        with client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu és um assistente especializado em criptomoedas."},
                {"role": "user", "content": req.prompt},
            ],
        ) as stream:
            for event in stream:
                if event.type == "content.delta" and event.delta:
                    yield event.delta
                elif event.type == "error":
                    yield f"⚠️ Erro: {event.error}"
            stream.close()
    return StreamingResponse(generate(), media_type="text/plain")
