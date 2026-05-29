# backend/Api/main.py
from __future__ import annotations
import os, logging, sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import re

# Garante que o diretório backend está no path para imports absolutos
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    # Tenta carregar .env do diretório backend primeiro, depois da raiz
    # IMPORTANTE: NÃO carregamos .env.local porque pode sobrescrever com valores vazios
    env_paths = [
        BACKEND_DIR / ".env",
        BACKEND_DIR.parent / ".env",
        # NÃO incluir .env.local aqui - pode ter valores vazios que sobrescrevem
    ]
    loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)  # override=True para garantir que carrega
            logging.info(f"✅ Carregado .env de: {env_path}")
            # Verifica se as variáveis foram carregadas (tenta ambos os nomes para compatibilidade)
            supabase_url = os.getenv("SUPABASE_URL", "")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
            logging.info(f"   SUPABASE_URL: {'✅' if supabase_url else '❌'} ({len(supabase_url)} chars)")
            logging.info(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if supabase_key else '❌'} ({len(supabase_key)} chars)")
            loaded = True
            break
    if not loaded:
        # No Render/produção, variáveis vêm do ambiente, não de ficheiros .env
        # Só mostra warning se estiver em desenvolvimento local
        if os.getenv("RENDER") is None:  # Não está no Render
            logging.warning("⚠️ Nenhum ficheiro .env encontrado nos caminhos:")
            for env_path in env_paths:
                logging.warning(f"   - {env_path}")
        else:
            logging.info("ℹ️ Em produção (Render) - usando variáveis de ambiente diretamente")
except ImportError:
    logging.warning("⚠️ python-dotenv não instalado. Instala com: pip install python-dotenv")
except Exception as e:
    logging.error(f"❌ Erro ao carregar .env: {e}")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vigia")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Lista de origens permitidas
ALLOWED_ORIGINS = {
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",  # Porta alternativa do Next.js
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
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
    allow_origin_regex=r"https://.*\.vercel\.app|https://joseruao\.com|https://www\.joseruao\.com|http://localhost:.*|http://127\.0\.0\.1:.*",
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

# Coin Analysis Router
try:
    from Api.routes.coin_analysis import router as coin_analysis_router
    app.include_router(coin_analysis_router, prefix="")
except ImportError as e:
    log.warning(f"Coin analysis router não disponível: {e}")

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

class ChatHistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)

LAST_COIN_ANALYSIS: dict = {}

def _is_trade_followup(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    decision_terms = [
        "compro", "comprar", "boa compra", "bom comprar", "vale a pena",
        "entro", "entrada", "buy", "should i buy", "is it good to buy",
        "fase de compra", "zona de compra", "esta em compra", "está em compra",
        "ainda achas", "achas o mesmo", "ainda pensas", "mantens", "e agora",
    ]
    return any(term in prompt_lower for term in decision_terms)

def _is_sell_followup(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    sell_terms = [
        "vender", "vendo", "venda", "realizar", "realizo", "sair",
        "onde vendo", "onde saio", "take profit", "profit", "sell",
    ]
    return any(term in prompt_lower for term in sell_terms)

def _is_analysis_detail_followup(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    detail_terms = [
        "porque", "porquê", "por que", "explica", "motivo", "risco",
        "target", "targets", "alvo", "alvos", "stop", "invalidacao",
        "invalidação", "onde entro", "entrada ideal", "plano",
    ]
    return any(term in prompt_lower for term in detail_terms)

def _latest_analysis_text(history: list[ChatHistoryMessage]) -> tuple[str | None, str | None]:
    fallback: tuple[str | None, str | None] = (None, None)
    for msg in reversed(history or []):
        if msg.role != "assistant":
            continue
        content = msg.content or ""
        full_match = re.search(r"Analise tecnica de\s+\**([A-Z0-9$.-]+)\**", content, re.IGNORECASE)
        if full_match:
            return full_match.group(1).upper(), content

        followup_match = re.search(
            r"(?:ultima analise de|analise anterior de)\s+\**([A-Z0-9$.-]+)\**",
            content,
            re.IGNORECASE,
        )
        if followup_match and fallback == (None, None):
            fallback = (followup_match.group(1).upper(), content)
    return fallback

def _extract_markdown_value(content: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(rf"{re.escape(label)}:\s*([^\n]+)", content, re.IGNORECASE)
    if not match:
        return "N/A"
    value = match.group(1).strip()
    return value.lstrip("- ").strip().strip("*").strip()

def _format_text_analysis_followup(history: list[ChatHistoryMessage]):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None

    price = _extract_markdown_value(content, "Preco atual")
    rsi = _extract_markdown_value(content, "RSI 14")
    if rsi == "N/A":
        rsi = _extract_markdown_value(content, "RSI")
    zone_match = re.search(r"preco esta em\s+\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
    zone = zone_match.group(1).strip() if zone_match else "N/A"
    if zone == "N/A":
        zone = _extract_markdown_value(content, "Zona atual")
    action_match = re.search(r"\*\*Resumo:\*\*\s*([^.\n]+)", content, re.IGNORECASE)
    action = action_match.group(1).strip() if action_match else "N/A"
    if action == "N/A":
        action = _extract_markdown_value(content, "Sinal tecnico")
    stop = _extract_markdown_value(content, "Stop loss")
    target_matches = re.findall(r"^\s*-?\s*([0-9][^\n]+(?:\(\d+%\)|\+.*\(\d+%\)))", content, re.MULTILINE)

    try:
        rsi_value = float(rsi)
    except (TypeError, ValueError):
        rsi_value = 50.0

    if "AGUARDAR" in action.upper():
        decision = "Eu nao compraria agressivamente agora; esperaria pullback ou confirmacao."
    elif rsi_value >= 68:
        decision = "Eu so consideraria entrada faseada, porque o RSI ja esta alto."
    elif "COMPRA" in action.upper():
        decision = "Tecnicamente esta favoravel para uma entrada faseada, nao para entrar all-in."
    else:
        decision = "Eu trataria como observacao ate aparecer uma entrada mais clara."

    def generate():
        yield f"Com base na analise anterior de **{coin}**, a minha leitura informativa e:\n\n"
        yield f"**{decision}**\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Zona atual: **{zone}**\n"
        yield f"- RSI: **{rsi}**\n"
        yield f"- Sinal tecnico: **{action}**\n"
        if stop != "N/A":
            yield f"- Invalida se perder: **{stop}**\n"
        if target_matches:
            yield "- Zonas de realizacao:\n"
            for target in target_matches[:3]:
                yield f"  - {target}\n"
        yield "\n_Isto e analise informativa, nao aconselhamento financeiro._"

    return generate

def _format_text_sell_followup(history: list[ChatHistoryMessage]):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None

    price = _extract_markdown_value(content, "Preco atual")
    rsi = _extract_markdown_value(content, "RSI 14")
    if rsi == "N/A":
        rsi = _extract_markdown_value(content, "RSI")
    zone = _extract_markdown_value(content, "Zona atual")
    if zone == "N/A":
        zone_match = re.search(r"preco esta em\s+\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
        zone = zone_match.group(1).strip() if zone_match else "N/A"
    target_matches = re.findall(r"^\s*-?\s*([0-9][^\n]+(?:\(\d+%\)|\+.*\(\d+%\)))", content, re.MULTILINE)

    try:
        rsi_value = float(rsi)
    except (TypeError, ValueError):
        rsi_value = 50.0

    if rsi_value >= 70:
        decision = "Se ja tens posicao, faz sentido considerar realizacao parcial; nao precisa ser tudo de uma vez."
    elif target_matches:
        decision = "Eu usaria os targets como zonas de venda parcial, mantendo gestao de risco."
    else:
        decision = "Eu nao venderia por impulso; procuraria uma zona tecnica clara de realizacao."

    def generate():
        yield f"Com base na analise anterior de **{coin}**, olhando pelo lado de venda:\n\n"
        yield f"**{decision}**\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Zona atual: **{zone}**\n"
        yield f"- RSI: **{rsi}**\n"
        if target_matches:
            yield "- Zonas de venda/realizacao:\n"
            for target in target_matches[:3]:
                yield f"  - {target}\n"
        else:
            yield "- Nao encontrei targets claros na ultima analise.\n"
        yield "\n_Isto e analise informativa, nao aconselhamento financeiro._"

    return generate

def _format_text_analysis_detail_followup(prompt: str, history: list[ChatHistoryMessage]):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None

    prompt_lower = prompt.lower()
    price = _extract_markdown_value(content, "Preco atual")
    rsi = _extract_markdown_value(content, "RSI 14")
    if rsi == "N/A":
        rsi = _extract_markdown_value(content, "RSI")
    zone = _extract_markdown_value(content, "Zona atual")
    if zone == "N/A":
        zone_match = re.search(r"preco esta em\s+\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
        zone = zone_match.group(1).strip() if zone_match else "N/A"
    action = _extract_markdown_value(content, "Sinal tecnico")
    if action == "N/A":
        action_match = re.search(r"\*\*Resumo:\*\*\s*([^.\n]+)", content, re.IGNORECASE)
        action = action_match.group(1).strip() if action_match else "N/A"
    stop = _extract_markdown_value(content, "Stop loss")
    if stop == "N/A":
        stop = _extract_markdown_value(content, "Invalida se perder")
    risk = _extract_markdown_value(content, "Risco")
    target_matches = re.findall(r"^\s*-\s+([0-9][^\n]+)", content, re.MULTILINE)

    def generate():
        yield f"Com base na analise anterior de **{coin}**:\n\n"
        if any(term in prompt_lower for term in ["risco", "stop", "invalidacao", "invalidação"]):
            yield f"- Risco: **{risk}**\n" if risk != "N/A" else "- Risco: nao apareceu explicitamente na ultima resposta.\n"
            if stop != "N/A":
                yield f"- Invalida se perder: **{stop}**\n"
            yield f"- Contexto: preco em **{zone}**, RSI **{rsi}**, sinal **{action}**.\n"
        elif any(term in prompt_lower for term in ["target", "targets", "alvo", "alvos"]):
            if target_matches:
                yield "Zonas de realizacao que estavam no plano:\n"
                for target in target_matches[:3]:
                    yield f"- {target}\n"
            else:
                yield "Nao encontrei targets claros na ultima analise.\n"
        elif any(term in prompt_lower for term in ["onde entro", "entrada ideal", "plano"]):
            yield f"- Entrada: **{zone}**\n"
            yield f"- Preco atual: **{price}**\n"
            yield f"- Sinal: **{action}**\n"
            if stop != "N/A":
                yield f"- Stop/invalidação: **{stop}**\n"
        else:
            yield f"O racional principal e: preco em **{zone}**, RSI **{rsi}** e sinal **{action}**.\n"
            yield "Isto favorece uma leitura faseada/disciplinada, nao uma entrada all-in.\n"
        yield "\n_Isto e analise informativa, nao aconselhamento financeiro._"

    return generate

def _format_trade_followup(prompt: str, history: list[ChatHistoryMessage] | None = None):
    cached = LAST_COIN_ANALYSIS or {}
    coin = cached.get("coin")
    result = cached.get("result") or {}
    if not coin or not result:
        return _format_text_analysis_followup(history or [])

    analysis = result.get("analysis", {}) or {}
    zones = result.get("trading_zones", {}) or {}
    recs = result.get("recommendations", {}) or {}
    strategy = recs.get("estrategia_trading", {}) or {}
    sr = analysis.get("support_resistance", {}) or {}
    action, summary = _analysis_stance(analysis, zones, recs)

    rsi = float(analysis.get("rsi") or 50)
    position = float(sr.get("current_position") or 50)
    current_zone = _human_zone(zones.get("posicao_atual"))
    current_price = _fmt_price(result.get("current_price"))
    support_price = _fmt_price(sr.get("dynamic_support")) if sr.get("dynamic_support") is not None else "N/A"
    stop_loss = _fmt_price(strategy.get("stop_loss")) if strategy.get("stop_loss") else "N/A"
    targets = strategy.get("targets") or []

    if action.startswith("AGUARDAR"):
        decision = "Eu nao compraria agressivamente agora; esperaria pullback ou confirmacao."
    elif rsi >= 68 or position >= 75:
        decision = "Eu so consideraria entrada faseada, porque o preco ja esta um pouco esticado."
    elif "COMPRA" in action.upper():
        decision = "Tecnicamente esta favoravel para uma entrada faseada, nao para entrar all-in."
    else:
        decision = "Eu trataria como observacao ate aparecer uma entrada mais clara."

    def generate():
        yield f"Com base na ultima analise de **{coin}**, a minha leitura informativa e:\n\n"
        yield f"**{decision}**\n\n"
        yield f"- Preco atual: **{current_price}**\n"
        yield f"- Zona atual: **{current_zone}**\n"
        if action.startswith("AGUARDAR") and support_price != "N/A":
            yield f"- Pullback a vigiar: perto de **{support_price}**\n"
        yield f"- RSI: **{analysis.get('rsi', 'N/A')}**\n"
        yield f"- Sinal tecnico: **{action}**\n"
        yield f"- Motivo: {summary}\n"
        if stop_loss != "N/A":
            yield f"- Invalida se perder: **{stop_loss}**\n"
        if targets:
            yield "- Zonas de realizacao:\n"
            for target in targets[:3]:
                yield f"  - {target}\n"
        yield "\n_Isto e analise informativa, nao aconselhamento financeiro._"

    return generate

def _should_use_coin_analysis(prompt: str) -> bool:
    """Verifica se o prompt pede análise gráfica de moeda"""
    prompt_lower = prompt.lower()
    analysis_keywords = ["analisa", "analise", "analyze", "análise", "análise gráfica", "gráfico", "gráfica", "técnica", "rsi", "médias móveis", "analisa-me"]
    coin_keywords = ["moeda", "coin", "token", "criptomoeda", "cryptocurrency", "btc", "eth", "sol", "usdt", "ada", "bnb", "xrp", "doge", "dot", "matic", "avax", "link", "ltc", "bch", "xlm", "etc", "trx", "xmr", "eos", "atom", "algo", "vet", "icp", "fil", "near", "apt", "arb", "op", "sui", "inj", "sei", "tia", "wif", "bonk", "hype", "pepe", "shib", "floki", "wld", "uni", "aave", "ondo", "fet"]
    
    has_analysis = any(kw in prompt_lower for kw in analysis_keywords)
    has_coin = any(kw in prompt_lower for kw in coin_keywords)
    
    # Se tem análise E (moeda OU é pedido genérico "analisa-me uma criptomoeda")
    if has_analysis:
        return True
        if has_coin:
            return True
        # Também aceita pedidos genéricos como "analisa-me uma criptomoeda"
        if "uma" in prompt_lower or "one" in prompt_lower:
            return True
    
    return False

def _fmt_price(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if number == 0:
        return "$0"
    if number >= 1000:
        return f"${number:,.0f}"
    if number >= 1:
        return f"${number:,.2f}"
    if number >= 0.01:
        return f"${number:.6f}".rstrip("0").rstrip(".")
    return f"${number:.10f}".rstrip("0").rstrip(".")

def _fmt_percent(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"

def _human_zone(zone: str) -> str:
    zones = {
        "ZONA_DE_COMPRA": "zona de compra",
        "ZONA_DE_VENDA": "zona de venda",
        "ZONA_NEUTRA": "zona neutra",
    }
    return zones.get(str(zone or ""), str(zone or "N/A").replace("_", " ").lower())

def _analysis_stance(analysis: dict, zones: dict, recs: dict) -> tuple[str, str]:
    rsi = float(analysis.get("rsi") or 50)
    sr = analysis.get("support_resistance") or {}
    position = float(sr.get("current_position") or 50)
    support = _fmt_price(sr.get("dynamic_support")) if sr.get("dynamic_support") is not None else "suporte"
    zone = zones.get("posicao_atual")
    trend = (analysis.get("trend") or {}).get("direction", "")
    score = recs.get("score", "N/A")

    if rsi >= 70 and position >= 75:
        return (
            f"AGUARDAR / COMPRA SO EM PULLBACK",
            f"RSI alto e preco perto da resistencia; tendencia ainda positiva, mas a entrada ideal ja nao e aqui. Pullback razoavel seria procurar preco mais perto de {support}. Score tecnico {score}/100."
        )
    if rsi >= 70:
        return (
            "AGUARDAR PULLBACK",
            f"RSI alto; apesar do contexto positivo, o risco de comprar esticado e maior. Melhor esperar aproximacao ao suporte em {support} ou nova consolidacao. Score tecnico {score}/100."
        )
    if zone == "ZONA_DE_COMPRA" and rsi < 65:
        return (
            recs.get("acao_principal", "COMPRA CONTROLADA"),
            f"Preco em zona de compra com RSI ainda controlado. Score tecnico {score}/100."
        )
    if zone == "ZONA_DE_VENDA":
        return (
            "REALIZAR / AGUARDAR",
            f"Preco em zona de venda; melhor proteger lucro do que perseguir entrada. Score tecnico {score}/100."
        )
    if trend == "UPTREND":
        return (
            "AGUARDAR CONFIRMACAO",
            f"Tendencia positiva, mas sem zona de entrada clara. Se corrigir, o suporte relevante abaixo esta perto de {support}. Score tecnico {score}/100."
        )
    return (
        recs.get("acao_principal", "AGUARDAR"),
        f"Sinais mistos; esperar melhor relacao risco/retorno. Score tecnico {score}/100."
    )

def _format_coin_analysis(coin: str, result: dict):
    analysis = result.get("analysis", {}) or {}
    zones = result.get("trading_zones", {}) or {}
    recs = result.get("recommendations", {}) or {}
    strategy = recs.get("estrategia_trading", {}) or {}
    sr = analysis.get("support_resistance", {}) or {}
    ma = analysis.get("moving_averages", {}) or {}
    trend = analysis.get("trend", {}) or {}
    volume = analysis.get("volume", {}) or {}

    action, summary = _analysis_stance(analysis, zones, recs)
    confidence = recs.get("confianca", "N/A")
    current_zone = _human_zone(zones.get("posicao_atual"))

    yield f"# Analise tecnica de {coin}\n\n"
    yield f"**Resumo:** {action} com confianca {confidence}. {summary} O preco esta em **{current_zone}**.\n\n"

    yield "## Leitura rapida\n\n"
    yield f"- Preco atual: **{_fmt_price(result.get('current_price'))}**\n"
    yield f"- RSI 14: **{analysis.get('rsi', 'N/A')}**\n"
    yield f"- Tendencia: **{trend.get('direction', 'N/A')}**"
    if trend.get("strength") is not None:
        yield f" ({_fmt_percent(trend.get('strength'))})"
    yield "\n"
    yield f"- Volatilidade: **{_fmt_percent(analysis.get('volatility'))}**\n"
    if volume:
        yield f"- Volume: **{volume.get('trend', 'N/A')}**, {volume.get('ratio_20d', 'N/A')}x vs media 20d\n"
    yield "\n"

    if sr:
        yield "## Zonas principais\n\n"
        yield f"- Suporte dinamico: **{_fmt_price(sr.get('dynamic_support'))}**\n"
        yield f"- Resistencia dinamica: **{_fmt_price(sr.get('dynamic_resistance'))}**\n"
        if sr.get("current_position") is not None:
            yield f"- Posicao no range: **{sr.get('current_position')}%** entre suporte e resistencia\n"
        yield "\n"

    if ma:
        yield "## Medias moveis\n\n"
        yield f"- SMA 20: {_fmt_price(ma.get('sma_20'))}\n"
        yield f"- SMA 50: {_fmt_price(ma.get('sma_50'))}\n"
        yield f"- SMA 200: {_fmt_price(ma.get('sma_200'))}\n\n"

    if strategy:
        yield "## Plano\n\n"
        yield f"- Estrategia: **{strategy.get('estrategia', 'N/A')}**\n"
        if action.startswith("AGUARDAR"):
            support_text = _fmt_price(sr.get("dynamic_support")) if sr.get("dynamic_support") is not None else None
            if support_text:
                yield f"- Acao: esperar pullback para perto de **{support_text}** ou confirmacao antes de nova entrada\n"
            else:
                yield "- Acao: esperar pullback ou confirmacao antes de nova entrada\n"
        else:
            yield f"- Acao: {strategy.get('plano') or strategy.get('acao') or 'Aguardar confirmacao'}\n"
        if strategy.get("stop_loss"):
            yield f"- Stop loss: {_fmt_price(strategy.get('stop_loss'))}\n"
        targets = strategy.get("targets") or []
        if targets:
            yield "- Targets:\n"
            for target in targets[:3]:
                yield f"  - {target}\n"
        if strategy.get("recompra"):
            yield f"- Recompra: {strategy.get('recompra')}\n"
        yield "\n"

    raw_actions = recs.get("acoes_recomendadas") or []
    actions = []
    for action_item in raw_actions:
        text = str(action_item)
        if action.startswith("AGUARDAR") and "FAVOR" in text.upper() and "COMPRA" in text.upper():
            text = "TENDENCIA DE ALTA - CONTEXTO POSITIVO, MAS AGUARDAR PULLBACK"
        actions.append(text)
    if actions:
        yield "## Sinais detectados\n\n"
        for action_item in actions[:4]:
            yield f"- {action_item}\n"
        yield "\n"

    risk = recs.get("alerta_risco")
    if risk:
        yield f"**Risco:** {risk}\n\n"
    yield "_Isto e analise informativa, nao aconselhamento financeiro._"

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Endpoint de chat com streaming.
    Se OpenAI estiver configurado, usa OpenAI. Caso contrário, retorna resposta simples.
    Detecta pedidos de análise gráfica e integra automaticamente.
    """
    try:
        if _is_trade_followup(req.prompt):
            followup = _format_trade_followup(req.prompt, req.history)
            if followup:
                return StreamingResponse(followup(), media_type="text/plain")
        if _is_sell_followup(req.prompt):
            sell_followup = _format_text_sell_followup(req.history)
            if sell_followup:
                return StreamingResponse(sell_followup(), media_type="text/plain")
        if _is_analysis_detail_followup(req.prompt):
            detail_followup = _format_text_analysis_detail_followup(req.prompt, req.history)
            if detail_followup:
                return StreamingResponse(detail_followup(), media_type="text/plain")
        # Verifica se é pedido de análise gráfica
        if _should_use_coin_analysis(req.prompt):
            try:
                from analisegrafica.coin_analysis import AdvancedCoinAnalyzer
                
                # Extrai nome da moeda do prompt
                coin = None
                prompt_upper = req.prompt.upper()
                
                # Lista de moedas conhecidas (ordem por tamanho decrescente para evitar matches parciais)
                known_coins = ["BITCOIN", "ETHEREUM", "SOLANA", "CARDANO", "POLKADOT", "POLYGON", "AVALANCHE", "CHAINLINK", "LITECOIN", "BITCOIN CASH", "STELLAR", "ETHEREUM CLASSIC", "TRON", "MONERO", "EOS", "COSMOS", "ALGORAND", "VECHAIN", "INTERNET COMPUTER", "FILECOIN", "NEAR", "APTOS", "ARBITRUM", "OPTIMISM", "SUI", "INJECTIVE", "SEI", "CELESTIA", "DOGWIFHAT", "BONK"]
                coin_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "AVAX", "LINK", "LTC", "BCH", "XLM", "ETC", "TRX", "XMR", "EOS", "ATOM", "ALGO", "VET", "ICP", "FIL", "NEAR", "APT", "ARB", "OP", "SUI", "INJ", "SEI", "TIA", "WIF", "BONK", "HYPE", "PEPE", "SHIB", "FLOKI", "WLD", "UNI", "AAVE", "ONDO", "FET", "BNB", "XRP", "DOGE", "USDT", "USDC"]
                
                # Primeiro tenta encontrar por nome completo
                for coin_name in known_coins:
                    if coin_name in prompt_upper:
                        # Mapeia nome completo para símbolo
                        coin_map = {
                            "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "CARDANO": "ADA",
                            "POLKADOT": "DOT", "POLYGON": "MATIC", "AVALANCHE": "AVAX", "CHAINLINK": "LINK",
                            "LITECOIN": "LTC", "BITCOIN CASH": "BCH", "STELLAR": "XLM", "ETHEREUM CLASSIC": "ETC",
                            "TRON": "TRX", "MONERO": "XMR", "COSMOS": "ATOM", "ALGORAND": "ALGO",
                            "VECHAIN": "VET", "INTERNET COMPUTER": "ICP", "FILECOIN": "FIL", "NEAR": "NEAR", "APTOS": "APT",
                            "ARBITRUM": "ARB", "OPTIMISM": "OP", "INJECTIVE": "INJ", "CELESTIA": "TIA",
                            "DOGWIFHAT": "WIF"
                        }
                        coin = coin_map.get(coin_name, coin_name[:3])
                        break
                
                # Se não encontrou por nome, procura por símbolo
                if not coin:
                    for symbol in coin_symbols:
                        if symbol in prompt_upper:
                            coin = symbol
                            break
                
                # Se ainda não encontrou, tenta extrair palavra após "moeda" ou "coin"
                if not coin:
                    words = req.prompt.split()
                    for i, word in enumerate(words):
                        word_lower = word.lower().strip(".,!?")
                        if word_lower in ["moeda", "coin", "token", "criptomoeda"] and i + 1 < len(words):
                            next_word = words[i + 1].upper().strip(".,!?")
                            if len(next_word) >= 2 and next_word.isalpha():
                                coin = next_word
                                break
                
                # Último recurso: procura qualquer palavra que pareça um símbolo de moeda (maiúsculas ou minúsculas)
                if not coin:
                    for word in req.prompt.split():
                        word_upper = word.upper().strip(".,!?")
                        # Aceita palavras de 2-10 caracteres (para capturar moedas como TURBO, DOGWIFHAT, etc.)
                        if len(word_upper) >= 2 and len(word_upper) <= 10 and word_upper.isalpha():
                            # Ignora palavras comuns que não são moedas
                            common_words = {"ANALISA", "ME", "A", "MOEDA", "GRAFICAMENTE", "GRAFICO", "GRAFICA", 
                                          "TECNICA", "ANALISE", "CRIPTOMOEDA", "COIN", "TOKEN", "CRYPTOCURRENCY"}
                            if word_upper not in common_words:
                                coin = word_upper
                                break
                
                if coin:
                    openai_key = os.getenv("OPENAI_API_KEY")
                    try:
                        from Api.services.crypto_tools import analyze_coin_tool
                        analysis_result = await analyze_coin_tool(coin)
                    except Exception:
                        analyzer = AdvancedCoinAnalyzer(openai_api_key=openai_key)
                        analysis_result = await analyzer.analyze_coin(coin)
                    
                    if "error" not in analysis_result:
                        LAST_COIN_ANALYSIS.clear()
                        LAST_COIN_ANALYSIS.update({"coin": coin, "result": analysis_result})

                        def generate_analysis():
                            yield from _format_coin_analysis(coin, analysis_result)
                            return
                            # Preço atual
                            current_price = analysis_result.get("current_price", "N/A")
                            yield f"# 📊 Análise Técnica de {coin}\n\n"
                            yield f"**Preço Atual:** ${current_price}\n\n"
                            
                            # Análise técnica detalhada
                            analysis = analysis_result.get("analysis", {})
                            if analysis:
                                yield "## 📈 Indicadores Técnicos\n\n"
                                
                                # RSI
                                rsi = analysis.get("rsi", "N/A")
                                yield f"**RSI (14):** {rsi}\n"
                                if isinstance(rsi, (int, float)):
                                    if rsi < 30:
                                        yield "  → Oversold (oportunidade de compra)\n"
                                    elif rsi > 70:
                                        yield "  → Overbought (considerar venda)\n"
                                yield "\n"
                                
                                # Médias Móveis
                                ma = analysis.get("moving_averages", {})
                                if ma:
                                    yield "**Médias Móveis:**\n"
                                    yield f"- SMA 20: ${ma.get('sma_20', 'N/A')}\n"
                                    yield f"- SMA 50: ${ma.get('sma_50', 'N/A')}\n"
                                    yield f"- SMA 200: ${ma.get('sma_200', 'N/A')}\n\n"
                                
                                # Tendência
                                trend = analysis.get("trend", {})
                                if trend:
                                    direction = trend.get("direction", "N/A")
                                    strength = trend.get("strength", "N/A")
                                    yield f"**Tendência:** {direction} (Força: {strength}%)\n\n"
                                
                                # Volatilidade
                                volatility = analysis.get("volatility", "N/A")
                                yield f"**Volatilidade:** {volatility}%\n\n"
                                
                                # Suporte e Resistência
                                sr = analysis.get("support_resistance", {})
                                if sr:
                                    yield "## 🎯 Suporte e Resistência\n\n"
                                    yield f"**Suporte Dinâmico:** ${sr.get('dynamic_support', 'N/A')}\n"
                                    yield f"**Resistência Dinâmica:** ${sr.get('dynamic_resistance', 'N/A')}\n"
                                    yield f"**Posição Atual:** {sr.get('current_position', 'N/A')}% entre suporte e resistência\n\n"
                                
                                # Fibonacci
                                fib = analysis.get("fibonacci", {})
                                if fib:
                                    yield "## 📐 Níveis de Fibonacci\n\n"
                                    levels = fib.get("levels", {})
                                    if levels:
                                        yield f"- 23.6%: ${levels.get('0.236', 'N/A')}\n"
                                        yield f"- 38.2%: ${levels.get('0.382', 'N/A')}\n"
                                        yield f"- 50.0%: ${levels.get('0.5', 'N/A')}\n"
                                        yield f"- 61.8%: ${levels.get('0.618', 'N/A')}\n"
                                        yield f"- 78.6%: ${levels.get('0.786', 'N/A')}\n\n"
                                
                                # Volume
                                volume = analysis.get("volume", {})
                                if volume:
                                    yield "## 📊 Análise de Volume\n\n"
                                    yield f"**Volume Atual:** {volume.get('current', 'N/A'):,}\n"
                                    yield f"**Rácio vs Média 20d:** {volume.get('ratio_20d', 'N/A')}x\n"
                                    yield f"**Tendência de Volume:** {volume.get('trend', 'N/A')}\n\n"
                            
                            # Zonas de Trading
                            zones = analysis_result.get("trading_zones", {})
                            if zones:
                                yield "## 💰 Zonas de Trading\n\n"
                                
                                pos_atual = zones.get("posicao_atual", "N/A")
                                yield f"**Posição Atual:** {pos_atual}\n\n"
                                
                                # Zonas de Compra
                                compra = zones.get("compra", {})
                                if compra:
                                    yield "### 🟢 Zonas de Compra\n\n"
                                    for key, zona in compra.items():
                                        yield f"**{key.replace('_', ' ').title()}:**\n"
                                        yield f"- Range: ${zona.get('range', 'N/A')}\n"
                                        yield f"- Descrição: {zona.get('descricao', 'N/A')}\n"
                                        yield f"- Confiança: {zona.get('confianca', 'N/A')}\n"
                                        if 'alvo_stop_loss' in zona:
                                            yield f"- Stop Loss: ${zona.get('alvo_stop_loss', 'N/A')}\n"
                                        yield "\n"
                                
                                # Zonas de Venda
                                venda = zones.get("venda", {})
                                if venda:
                                    yield "### 🔴 Zonas de Venda\n\n"
                                    for key, zona in venda.items():
                                        yield f"**{key.replace('_', ' ').title()}:**\n"
                                        yield f"- Range: ${zona.get('range', 'N/A')}\n"
                                        yield f"- Descrição: {zona.get('descricao', 'N/A')}\n"
                                        yield f"- Confiança: {zona.get('confianca', 'N/A')}\n"
                                        if 'percentual_vender' in zona:
                                            yield f"- Percentual a Vender: {zona.get('percentual_vender', 'N/A')}\n"
                                        yield "\n"
                                
                                # Zona Neutra
                                neutra = zones.get("neutra", {})
                                if neutra:
                                    yield "### ⚪ Zona Neutra\n\n"
                                    yield f"**Range:** ${neutra.get('range', 'N/A')}\n"
                                    yield f"**Descrição:** {neutra.get('descricao', 'N/A')}\n"
                                    yield f"**Ação:** {neutra.get('acao', 'N/A')}\n"
                                    yield f"**Motivo:** {neutra.get('motivo', 'N/A')}\n\n"
                            
                            # Recomendações
                            recs = analysis_result.get("recommendations", {})
                            if recs:
                                yield "## 🎯 Recomendações e Estratégia\n\n"
                                yield f"**Ação Principal:** {recs.get('acao_principal', 'N/A')}\n"
                                yield f"**Confiança:** {recs.get('confianca', 'N/A')}\n"
                                yield f"**Score:** {recs.get('score', 'N/A')}/100\n\n"
                                
                                actions = recs.get('acoes_recomendadas', [])
                                if actions:
                                    yield "**Ações Recomendadas:**\n"
                                    for action in actions:
                                        yield f"- {action}\n"
                                    yield "\n"
                                
                                # Estratégia de Trading
                                strategy = recs.get('estrategia_trading', {})
                                if strategy:
                                    yield "**Estratégia de Trading:**\n"
                                    yield f"- Tipo: {strategy.get('estrategia', 'N/A')}\n"
                                    yield f"- Plano: {strategy.get('plano', 'N/A')}\n"
                                    if 'alocacao' in strategy:
                                        yield f"- Alocação: {strategy.get('alocacao', 'N/A')}\n"
                                    if 'stop_loss' in strategy:
                                        yield f"- Stop Loss: ${strategy.get('stop_loss', 'N/A')}\n"
                                    if 'targets' in strategy:
                                        yield "- Targets:\n"
                                        for target in strategy.get('targets', []):
                                            yield f"  - {target}\n"
                                    if 'recompra' in strategy:
                                        yield f"- Recompra: {strategy.get('recompra', 'N/A')}\n"
                                    yield "\n"
                                
                                # Alerta de Risco
                                alerta = recs.get('alerta_risco', 'N/A')
                                if alerta:
                                    yield f"**⚠️ Alerta de Risco:** {alerta}\n\n"
                            
                            # Resumo final
                            summary = analysis_result.get("summary", "")
                            if summary:
                                yield "## 📝 Resumo Executivo\n\n"
                                yield f"{summary}\n"
                        
                        return StreamingResponse(generate_analysis(), media_type="text/plain")
                    else:
                        # Erro na análise
                        def error_response():
                            error_msg = analysis_result.get("error", "Erro desconhecido na análise")
                            yield f"⚠️ Erro ao analisar {coin}: {error_msg}\n"
                            yield "\nPor favor, tenta com outro símbolo de moeda."
                        return StreamingResponse(error_response(), media_type="text/plain")
                else:
                    # Não encontrou moeda específica
                    def ask_for_coin():
                        yield "Por favor, especifica qual criptomoeda queres que analise.\n\n"
                        yield "Exemplos:\n"
                        yield "- Analisa-me a moeda BTC\n"
                        yield "- Analisa-me a moeda ETH\n"
                        yield "- Analisa-me a moeda ADA\n"
                        yield "- Analisa-me a moeda SOL\n"
                    
                    return StreamingResponse(ask_for_coin(), media_type="text/plain")
            except Exception as e:
                log.warning(f"Erro ao tentar análise gráfica: {e}", exc_info=True)
                # Retorna erro claro em vez de cair no fluxo genérico
                error_text = str(e)
                def analysis_error_response():
                    yield f"⚠️ Erro ao analisar a moeda: {error_text}\n\n"
                    yield "Possíveis causas:\n"
                    yield "- Moeda não disponível no Yahoo Finance (ex: tokens Solana)\n"
                    yield "- Cold start do servidor (tenta novamente em 10-20 segundos)\n"
                    yield "- Símbolo incorreto (usa BTC, ETH, SOL, TURBO, etc.)\n"
                return StreamingResponse(analysis_error_response(), media_type="text/plain")
        
        # Tenta usar OpenAI se disponível
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            def generate():
                try:
                    system_msg = "Tu és um assistente especializado em criptomoedas e análise de tokens. "
                    system_msg += "Se o utilizador pedir análise gráfica de uma moeda, podes mencionar que existe uma API dedicada em /coin/analyze."
                    
                    with client.chat.completions.stream(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_msg},
                            *[
                                {"role": msg.role, "content": msg.content}
                                for msg in (req.history or [])[-8:]
                                if msg.role in {"user", "assistant"} and msg.content
                            ],
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
        error_text = str(e)
        def error_response():
            yield f"⚠️ Erro ao processar a mensagem: {error_text}"
        return StreamingResponse(error_response(), media_type="text/plain")
