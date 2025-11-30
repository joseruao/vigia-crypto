# backend/Api/main.py
from __future__ import annotations
import os, logging, sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Garante que o diretório backend está no path para imports absolutos
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Lista de origens permitidas
ALLOWED_ORIGINS = {
    FRONTEND_URL,
    "http://localhost:3000",
    "https://joseruao.com",
    "https://www.joseruao.com",
    "https://joseruao.vercel.app",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Vigia API a iniciar")
    yield
    log.info("🛑 Vigia API a encerrar")

app = FastAPI(title="Vigia API", version="0.1.0", lifespan=lifespan)

# CORS com verificação customizada para domínios do Vercel
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

app.add_middleware(
    StarletteCORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|https://joseruao\.com|https://www\.joseruao\.com|http://localhost:.*",
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_buffering_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Accel-Buffering", "no")
    resp.headers.setdefault("Cache-Control", "no-cache")
    return resp

# Routers
from Api.routes.alerts import router as alerts_router
app.include_router(alerts_router, prefix="")

@app.get("/")
@app.head("/")
def root():
    return {"ok": True, "service": "vigia-backend"}

@app.get("/ping")
@app.head("/ping")
def ping():
    return {"status": "ok"}

@app.get("/__version")
def version():
    return {"name": "vigia-backend", "version": "0.1.1"}

# ============================
# CHAT ENDPOINTS
# ============================

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Endpoint de chat com streaming.
    Se OpenAI estiver configurado, usa OpenAI. Caso contrário, retorna resposta simples.
    """
    try:
        # Tenta usar OpenAI se disponível
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            def generate():
                try:
                    with client.chat.completions.stream(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Tu és um assistente especializado em criptomoedas e análise de tokens."},
                            {"role": "user", "content": req.prompt},
                        ],
                    ) as stream:
                        for event in stream:
                            if event.type == "content.delta" and event.delta:
                                yield event.delta
                            elif event.type == "error":
                                yield f"⚠️ Erro: {event.error}"
                except Exception as e:
                    log.error(f"Erro no stream OpenAI: {e}")
                    yield f"⚠️ Erro ao processar: {str(e)}"
            
            return StreamingResponse(generate(), media_type="text/plain")
        else:
            # Fallback: resposta simples sem OpenAI
            def generate_fallback():
                response = f"Olá! Recebi a tua mensagem: '{req.prompt}'\n\n"
                response += "A funcionalidade de chat com IA está temporariamente indisponível.\n"
                response += "Podes usar as sugestões para consultar holdings e previsões de tokens."
                yield response
            
            return StreamingResponse(generate_fallback(), media_type="text/plain")
    except Exception as e:
        log.error(f"Erro em /chat/stream: {e}")
        def error_response():
            yield f"⚠️ Erro ao processar a mensagem: {str(e)}"
        return StreamingResponse(error_response(), media_type="text/plain")
