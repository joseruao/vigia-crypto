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

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    # Tenta carregar .env do diretório backend primeiro, depois da raiz
    env_paths = [
        BACKEND_DIR / ".env",
        BACKEND_DIR.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logging.info(f"✅ Carregado .env de: {env_path}")
            break
    else:
        logging.warning("⚠️ Nenhum ficheiro .env encontrado")
except ImportError:
    logging.warning("⚠️ python-dotenv não instalado. Usando apenas variáveis de ambiente do sistema.")

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

class ChatRequest(BaseModel):
    prompt: str

def _should_use_coin_analysis(prompt: str) -> bool:
    """Verifica se o prompt pede análise gráfica de moeda"""
    prompt_lower = prompt.lower()
    analysis_keywords = ["analisa", "análise", "análise gráfica", "gráfico", "gráfica", "técnica", "rsi", "médias móveis", "analisa-me"]
    coin_keywords = ["moeda", "coin", "token", "criptomoeda", "cryptocurrency", "btc", "eth", "sol", "usdt", "ada", "bnb", "xrp", "doge", "dot", "matic", "avax", "link", "ltc", "bch", "xlm", "etc", "trx", "xmr", "eos", "atom", "algo", "vet", "icp", "fil", "near", "apt", "arb", "op", "sui", "inj", "sei", "tia", "wif", "bonk"]
    
    has_analysis = any(kw in prompt_lower for kw in analysis_keywords)
    has_coin = any(kw in prompt_lower for kw in coin_keywords)
    
    # Se tem análise E (moeda OU é pedido genérico "analisa-me uma criptomoeda")
    if has_analysis:
        if has_coin:
            return True
        # Também aceita pedidos genéricos como "analisa-me uma criptomoeda"
        if "uma" in prompt_lower or "one" in prompt_lower:
            return True
    
    return False

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Endpoint de chat com streaming.
    Se OpenAI estiver configurado, usa OpenAI. Caso contrário, retorna resposta simples.
    Detecta pedidos de análise gráfica e integra automaticamente.
    """
    try:
        # Verifica se é pedido de análise gráfica
        if _should_use_coin_analysis(req.prompt):
            try:
                from analisegrafica.coin_analysis import AdvancedCoinAnalyzer
                import os
                
                # Extrai nome da moeda do prompt
                coin = None
                prompt_upper = req.prompt.upper()
                
                # Lista de moedas conhecidas (ordem por tamanho decrescente para evitar matches parciais)
                known_coins = ["BITCOIN", "ETHEREUM", "SOLANA", "CARDANO", "POLKADOT", "POLYGON", "AVALANCHE", "CHAINLINK", "LITECOIN", "BITCOIN CASH", "STELLAR", "ETHEREUM CLASSIC", "TRON", "MONERO", "EOS", "COSMOS", "ALGORAND", "VECHAIN", "INTERNET COMPUTER", "FILECOIN", "NEAR", "APTOS", "ARBITRUM", "OPTIMISM", "SUI", "INJECTIVE", "SEI", "CELESTIA", "DOGWIFHAT", "BONK"]
                coin_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "AVAX", "LINK", "LTC", "BCH", "XLM", "ETC", "TRX", "XMR", "EOS", "ATOM", "ALGO", "VET", "ICP", "FIL", "NEAR", "APT", "ARB", "OP", "SUI", "INJ", "SEI", "TIA", "WIF", "BONK", "BNB", "XRP", "DOGE", "USDT", "USDC"]
                
                # Primeiro tenta encontrar por nome completo
                for coin_name in known_coins:
                    if coin_name in prompt_upper:
                        # Mapeia nome completo para símbolo
                        coin_map = {
                            "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "CARDANO": "ADA",
                            "POLKADOT": "DOT", "POLYGON": "MATIC", "AVALANCHE": "AVAX", "CHAINLINK": "LINK",
                            "LITECOIN": "LTC", "BITCOIN CASH": "BCH", "STELLAR": "XLM", "ETHEREUM CLASSIC": "ETC",
                            "TRON": "TRX", "MONERO": "XMR", "COSMOS": "ATOM", "ALGORAND": "ALGO",
                            "VECHAIN": "VET", "INTERNET COMPUTER": "ICP", "FILECOIN": "FIL", "APTOS": "APT",
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
                
                # Último recurso: procura qualquer palavra em maiúsculas que pareça um símbolo de moeda
                if not coin:
                    for word in req.prompt.split():
                        word_upper = word.upper().strip(".,!?")
                        if len(word_upper) >= 2 and len(word_upper) <= 5 and word_upper.isalpha():
                            coin = word_upper
                            break
                
                if coin:
                    openai_key = os.getenv("OPENAI_API_KEY")
                    analyzer = AdvancedCoinAnalyzer(openai_api_key=openai_key)
                    analysis_result = await analyzer.analyze_coin(coin)
                    
                    if "error" not in analysis_result:
                        def generate_analysis():
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
                log.warning(f"Erro ao tentar análise gráfica: {e}")
                # Continua com o fluxo normal
        
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
