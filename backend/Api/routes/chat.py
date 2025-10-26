# backend/Api/routes/chat.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from Api.services.summaries import items_to_markdown
import asyncio

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/stream")
async def chat_stream(request: Request):
    body = await request.json()
    alerts = body.get("alerts") or []
    markdown = items_to_markdown(alerts)

    async def stream():
        for line in markdown.split("\n"):
            yield f"data: {line}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(stream(), media_type="text/event-stream")
