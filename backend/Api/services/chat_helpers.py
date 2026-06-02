"""
Chat helper functions: intent classification, coin extraction,
position/PnL calculation, and response formatters.

Exported intent classifiers:
  _is_trade_followup, _is_sell_followup, _is_entry_price_followup,
  _is_analysis_detail_followup, _is_onboarding_question,
  _is_comparison_question, _should_use_coin_analysis
"""
from __future__ import annotations
import re
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared mutable state (populated by the coin-analysis endpoint)
# ---------------------------------------------------------------------------
LAST_COIN_ANALYSIS: dict = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
def _is_trade_followup(prompt: str) -> bool:
    q = prompt.lower()
    if "top100" in q or "top 100" in q:
        return False
    if any(t in q for t in ["listing", "listado", "vao ser", "vão ser", "previsao", "previsão"]):
        return False
    return any(t in q for t in [
        "compro", "comprar", "boa compra", "bom comprar", "vale a pena",
        "entro", "entrada", "buy", "should i buy", "is it good to buy",
        "fase de compra", "zona de compra", "esta em compra", "está em compra",
        "ainda achas", "achas o mesmo", "ainda pensas", "mantens", "e agora",
        "faz sentido", "o que achas",
    ])


def _is_sell_followup(prompt: str) -> bool:
    return any(t in prompt.lower() for t in [
        "vender", "vendo", "venda", "realizar", "realizo", "sair",
        "onde vendo", "onde saio", "take profit", "profit", "sell",
    ])


def _is_entry_price_followup(prompt: str) -> bool:
    return _extract_entry_price(prompt) is not None


def _is_analysis_detail_followup(prompt: str) -> bool:
    return any(t in prompt.lower() for t in [
        "porque", "porquê", "por que", "explica", "motivo", "risco",
        "target", "targets", "alvo", "alvos", "stop", "invalidacao",
        "invalidação", "onde entro", "entrada ideal", "plano",
        "fibonacci", "fib", "quando entra", "quando compro",
    ])


def _is_onboarding_question(prompt: str) -> bool:
    q = prompt.lower()
    return any(t in q for t in [
        "o que é isto", "o que é o vigia", "como funciona", "o que fazes",
        "o que podes", "como me podes ajudar", "o que é este site",
        "what is this", "how does this work", "what can you do",
        "what is vigia", "how can you help", "what do you do",
    ])


def _is_comparison_question(prompt: str) -> bool:
    upper = prompt.upper()
    known = ["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","DOGE","DOT","LINK","NEAR","APT","ARB","OP","SUI","ATOM","UNI","AAVE","FIL","WIF"]
    found = [c for c in known if re.search(rf"(?<![A-Z0-9]){c}(?![A-Z0-9])", upper)]
    return len(found) >= 2


def _format_comparison_followup(coins: list[str], history: list[ChatHistoryMessage]):
    """Compare coins using analyses already present in history. Returns None if data is missing."""
    coin_data: dict[str, dict] = {}
    for msg in reversed(history or []):
        if msg.role != "assistant":
            continue
        content = msg.content or ""
        for coin in coins:
            if coin in coin_data:
                continue
            if not re.search(rf"📊\s+{re.escape(coin)}\s+[—–]|Analise [Tt]ecnica de\s+\**{re.escape(coin)}\**", content):
                continue
            rsi = _extract_markdown_value(content, "RSI 14")
            if rsi == "N/A":
                rsi = _extract_markdown_value(content, "RSI")
            verdict_match = re.search(r"(?:🔥|🟢|🔴|🟡)\s+\*\*([^*\n]+)\*\*", content)
            entry_match = re.search(r"🎯 \*\*Entrada:\*\* perto de ([^\n]+)", content)
            target_match = re.search(r"🚀 \*\*Alvo:\*\* ([^\n]+)", content)
            stop_match = re.search(r"🛡️ \*\*Stop:\*\* ([^\n]+)", content)
            price_match = re.search(r"\*\*Preço atual:\*\* ([^\n]+)", content)
            sma200_match = re.search(r"(Acima|Abaixo) da SMA200", content)
            trend_match = re.search(r"Tendência de curto prazo: \*\*(\w+)\*\*", content)
            try:
                rsi_f: float | None = float(rsi)
            except (TypeError, ValueError):
                rsi_f = None
            coin_data[coin] = {
                "rsi": rsi, "rsi_f": rsi_f,
                "verdict": verdict_match.group(1) if verdict_match else None,
                "entry": entry_match.group(1).strip() if entry_match else "N/A",
                "target": target_match.group(1).strip() if target_match else "N/A",
                "stop": stop_match.group(1).strip() if stop_match else "N/A",
                "price": price_match.group(1).strip() if price_match else "N/A",
                "sma200": sma200_match.group(1) if sma200_match else None,
                "trend": trend_match.group(1) if trend_match else None,
            }
        if len(coin_data) >= 2:
            break

    present = [c for c in coins if c in coin_data]
    if len(present) < 2:
        return None

    def generate():
        yield "**Comparação técnica** com base nas análises anteriores:\n\n"
        for coin in present:
            d = coin_data[coin]
            verdict = d.get("verdict") or ""
            icon = "🔥" if "FORTE" in verdict else ("🟢" if "COMPRA" in verdict else ("🔴" if "VENDA" in verdict else "🟡"))
            yield f"{icon} **{coin}** — {d['price']}\n"
            yield f"RSI {d['rsi']} · Tendência: {d.get('trend') or 'N/A'} · {'Acima' if d.get('sma200') == 'Acima' else 'Abaixo'} SMA200\n"
            if d["entry"] != "N/A":
                yield f"Entrada {d['entry']} · Alvo {d['target']} · Stop {d['stop']}\n"
            yield "\n"

        a_coin, b_coin = present[0], present[1]
        a, b = coin_data[a_coin], coin_data[b_coin]
        a_rsi, b_rsi = a.get("rsi_f"), b.get("rsi_f")
        a_above = a.get("sma200") == "Acima"
        b_above = b.get("sma200") == "Acima"

        yield "**Leitura comparativa:**\n"

        if a_rsi is not None and b_rsi is not None:
            if abs(a_rsi - b_rsi) > 4:
                more = a_coin if a_rsi < b_rsi else b_coin
                less = b_coin if a_rsi < b_rsi else a_coin
                more_rsi = min(a_rsi, b_rsi)
                yield f"- RSI: {more} mais sobrevendido ({more_rsi:.1f}) — maior potencial de bounce, mas confirmar antes de entrar\n"
            else:
                yield f"- RSI semelhante: {a_coin} {a_rsi:.1f} vs {b_coin} {b_rsi:.1f} — ambos em oversold\n"

        if a_above != b_above:
            above = a_coin if a_above else b_coin
            below = b_coin if a_above else a_coin
            yield f"- SMA200: {above} acima (macro bullish), {below} abaixo (pressão vendedora macro)\n"
        else:
            yield f"- SMA200: ambos {'acima' if a_above else 'abaixo'} — mesmo contexto macro\n"

        a_score = sum([
            1 if (a_rsi or 99) < (b_rsi or 99) else 0,
            1 if a_above and not b_above else 0,
            1 if a.get("trend") == "UPTREND" and b.get("trend") != "UPTREND" else 0,
        ])
        b_score = sum([
            1 if (b_rsi or 99) < (a_rsi or 99) else 0,
            1 if b_above and not a_above else 0,
            1 if b.get("trend") == "UPTREND" and a.get("trend") != "UPTREND" else 0,
        ])

        yield "\n"
        if a_score > b_score:
            yield f"**Setup ligeiramente mais favorável: {a_coin}** — melhor combinação de RSI, tendência e SMA200.\n"
        elif b_score > a_score:
            yield f"**Setup ligeiramente mais favorável: {b_coin}** — melhor combinação de RSI, tendência e SMA200.\n"
        else:
            yield f"**Setup equivalente** entre {a_coin} e {b_coin} — sem vantagem clara de um sobre o outro agora.\n"
        yield "Ambos têm plano definido (entrada/alvo/stop). Se diversificares, ambos têm setup válido.\n"

    return generate


def _format_onboarding() -> callable:
    def generate():
        yield (
            "## O que faço e como te posso ajudar\n\n"
            "Sou um assistente de análise de mercado crypto. "
            "Não dou conselhos de investimento — dou-te **informação estruturada** para tomares melhores decisões.\n\n"
            "Tenho três fontes de dados principais:\n\n"
            "---\n\n"
            "### 🏦 Monitorização de wallets de grandes exchanges\n"
            "Acompanho wallets on-chain de exchanges como **Binance, Coinbase, Gate.io, Kraken, OKX e Bybit**. "
            "Quando uma exchange acumula um token que ainda não está listado nela, isso pode ser um sinal antecipado. "
            "Mostro o valor acumulado, há quanto tempo foi detetado e a probabilidade estimada.\n\n"
            "_Pergunta-me: \"Potenciais listings nas exchanges\"_\n\n"
            "---\n\n"
            "### 📊 Análise técnica diária do Top 100\n"
            "Todos os dias analiso as 100 maiores criptomoedas com indicadores técnicos reais: "
            "RSI, MACD, Bollinger Bands, médias móveis (SMA20/50/200) e suporte/resistência por swing pivots. "
            "Digo-te quais estão perto de zonas de compra, quais têm momentum a favor, e qual a leitura técnica de cada uma.\n\n"
            "_Pergunta-me: \"Melhores oportunidades hoje\" ou \"O que está barato agora?\"_\n\n"
            "---\n\n"
            "### 🔍 Análise individual de qualquer moeda\n"
            "Posso analisar qualquer criptomoeda em detalhe — zonas de entrada, stop loss, targets, RSI, tendência macro e micro.\n\n"
            "_Pergunta-me: \"Analisa BTC\", \"Analisa SOL\", \"Analisa NEAR\"_\n\n"
            "---\n\n"
            "**Nota:** Tudo o que vês é informação de mercado, não aconselhamento financeiro. "
            "Usa os dados para informares a tua própria análise."
        )
    return generate


def _should_use_coin_analysis(prompt: str) -> bool:
    q = prompt.lower()
    if "top100" in q or "top 100" in q:
        return False
    if any(t in q for t in ["listing", "listado", "vao ser", "vão ser", "previsao", "previsão"]):
        return False
    # Perguntas educativas ("o que é o RSI?") não devem disparar análise de moeda
    educational = ["o que é", "what is", "what are", "explica o que", "define ", "o que significa", "o que sao"]
    if any(t in q for t in educational):
        return False
    # Perguntas sobre o mercado em geral sem moeda específica não devem disparar análise de moeda
    if any(t in q for t in ["mercado", "market"]) and not _is_comparison_question(prompt):
        # Only block if there's no specific coin symbol present
        known = ["BTC","ETH","SOL","BNB","XRP","ADA","AVAX","DOGE","DOT","LINK","NEAR","APT","ARB","OP","SUI","ATOM","UNI","AAVE","FIL","WIF"]
        upper = prompt.upper()
        has_coin = any(re.search(rf"(?<![A-Z0-9]){c}(?![A-Z0-9])", upper) for c in known)
        if not has_coin:
            return False
    analysis_kw = [
        "analisa", "analise", "analyze", "análise", "análise gráfica",
        "gráfico", "gráfica", "técnica", "rsi", "médias móveis", "analisa-me",
    ]
    return any(kw in q for kw in analysis_kw)


# ---------------------------------------------------------------------------
# Number / money parsing
# ---------------------------------------------------------------------------
def _parse_number_text(value: str) -> float | None:
    try:
        cleaned = re.sub(r"[^\d,.\-]", "", value or "").replace(",", ".")
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _parse_compact_money(value: str) -> float | None:
    try:
        text = str(value or "").strip().upper().replace(",", ".")
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*([KMB])?", text)
        if not match:
            return None
        number = float(match.group(1))
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        return number * multipliers.get(match.group(2), 1)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Coin / position extraction
# ---------------------------------------------------------------------------
def _extract_entry_price(prompt: str) -> float | None:
    patterns = [
        r"(?:comprei|compra|entrada|preco medio|preço médio|medio|m[eé]dio)\s*(?:a|ao|em|foi|:)?\s*\$?\s*([\d]+(?:[,.]\d+)?)",
        r"\$?\s*([\d]+(?:[,.]\d+)?)\s*(?:de entrada|preco medio|preço médio|medio|m[eé]dio)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return _parse_number_text(match.group(1))
    return None


def _extract_position_size(prompt: str, coin: str | None = None) -> dict | None:
    text = prompt or ""
    fiat_patterns = [
        r"(?:tenho|posi[cç][aã]o(?:\s+de)?|investi|meti|entrei\s+com)\s*(?:cerca\s+de\s*)?(?:€|\$)?\s*([\d]+(?:[,.]\d+)?)\s*(€|eur|euros|usd|dolares|dólares|\$)",
        r"(?:€|\$)\s*([\d]+(?:[,.]\d+)?)\s*(?:em|de)?\s*(?:posi[cç][aã]o|investidos?)?",
    ]
    for pattern in fiat_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = _parse_number_text(match.group(1))
            if amount is not None:
                return {"type": "fiat", "amount": amount}

    symbol = re.escape((coin or "").upper())
    unit_patterns = []
    if symbol:
        unit_patterns.extend([
            rf"(?:tenho|posi[cç][aã]o(?:\s+de)?)\s*([\d]+(?:[,.]\d+)?)\s*{symbol}\b",
            rf"([\d]+(?:[,.]\d+)?)\s*{symbol}\b",
        ])
    unit_patterns.append(
        r"(?:tenho|posi[cç][aã]o(?:\s+de)?)\s*([\d]+(?:[,.]\d+)?)\s*(?:moedas|tokens|coins|unidades)"
    )
    for pattern in unit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = _parse_number_text(match.group(1))
            if amount is not None:
                return {"type": "units", "amount": amount}
    return None


def _normalize_coin_symbol(symbol: str | None) -> str | None:
    if not symbol:
        return None
    normalized = symbol.upper().strip().strip("$.,!?;:")
    aliases = {
        "NEA": "NEAR",
        "HYPERLIQUID": "HYPE",
        "DOGWIFHAT": "WIF",
        "WIFHAT": "WIF",
        "RNDR": "RENDER",
        "FETCH": "FET",
        "ASI": "FET",
    }
    return aliases.get(normalized, normalized)


def _extract_targets(content: str) -> list[str]:
    direct = re.findall(
        r"^\s*-?\s*([0-9][^\n]+(?:\(\d+%\)|\+.*\(\d+%\)))", content, re.MULTILINE
    )
    if direct:
        return direct
    lines = content.splitlines()
    targets: list[str] = []
    in_targets = False
    for line in lines:
        clean = line.strip().lstrip("- ").strip()
        if not clean:
            if in_targets and targets:
                break
            continue
        if clean.lower().startswith(("targets", "zonas de realizacao", "zonas de venda")):
            in_targets = True
            continue
        if in_targets:
            if re.match(r"^[0-9]", clean):
                targets.append(clean)
                continue
            if targets:
                break
    return targets


# ---------------------------------------------------------------------------
# Position / PnL
# ---------------------------------------------------------------------------
def _position_summary(
    position: dict | None, entry_price: float | None, current_price: float | None
) -> dict:
    if not position or not entry_price or not current_price:
        return {}
    amount = position.get("amount")
    if not amount:
        return {}
    if position.get("type") == "fiat":
        invested = float(amount)
        units = invested / entry_price if entry_price else None
        current_value = units * current_price if units is not None else None
    else:
        units = float(amount)
        invested = units * entry_price
        current_value = units * current_price
    pnl_value = current_value - invested if current_value is not None else None
    pnl_pct = (pnl_value / invested) * 100 if invested else None
    return {
        "units": units,
        "invested": invested,
        "current_value": current_value,
        "pnl_value": pnl_value,
        "pnl_pct": pnl_pct,
    }


# ---------------------------------------------------------------------------
# Markdown / text extraction
# ---------------------------------------------------------------------------
def _latest_analysis_text(
    history: list[ChatHistoryMessage],
) -> tuple[str | None, str | None]:
    fallback: tuple[str | None, str | None] = (None, None)
    for msg in reversed(history or []):
        if msg.role != "assistant":
            continue
        content = msg.content or ""
        full_match = re.search(r"Analise tecnica de\s+\**([A-Z0-9$.-]+)\**", content, re.IGNORECASE)
        if full_match:
            return full_match.group(1).upper(), content
        snapshot_match = re.search(r"Snapshot de mercado de\s+\**([A-Z0-9$.-]+)\**", content, re.IGNORECASE)
        if snapshot_match:
            return snapshot_match.group(1).upper(), content
        followup_match = re.search(
            r"(?:ultima analise de|analise anterior de)\s+\**([A-Z0-9$.-]+)\**",
            content, re.IGNORECASE,
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
    return match.group(1).strip().lstrip("- ").strip().strip("*").strip()


def _snapshot_metrics_from_text(content: str) -> dict:
    return {
        "price": _extract_markdown_value(content, "Preco atual"),
        "chain_dex": _extract_markdown_value(content, "Chain/DEX"),
        "liquidity": _extract_markdown_value(content, "Liquidez"),
        "volume": _extract_markdown_value(content, "Volume 24h"),
        "change": _extract_markdown_value(content, "Variação 24h"),
        "market_cap": _extract_markdown_value(content, "Market cap"),
        "fdv": _extract_markdown_value(content, "FDV"),
    }


# ---------------------------------------------------------------------------
# Formatting utilities
# ---------------------------------------------------------------------------
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


def _fmt_money(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if number >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:.0f}"


def _human_zone(zone: str) -> str:
    zones = {
        "ZONA_DE_COMPRA": "zona de compra",
        "ZONA_DE_VENDA": "zona de venda",
        "ZONA_NEUTRA": "zona neutra",
    }
    return zones.get(str(zone or ""), str(zone or "N/A").replace("_", " ").lower())


def _snapshot_risk_label(liquidity: float | None, volume: float | None) -> str:
    if liquidity is None:
        return "RISCO ELEVADO"
    if liquidity < 25_000 or (volume is not None and volume < 5_000):
        return "RISCO MUITO ELEVADO"
    if liquidity < 100_000 or (volume is not None and volume < 25_000):
        return "RISCO ELEVADO"
    if liquidity < 500_000:
        return "RISCO MODERADO/ELEVADO"
    return "RISCO MODERADO"


def _entry_plan_lines(budget: float, cautious: bool = False) -> list[str]:
    if cautious:
        return [
            f"  - 25% inicial: ~{_fmt_money(budget * 0.25)}",
            f"  - 35% em pullback/confirmacao: ~{_fmt_money(budget * 0.35)}",
            f"  - 40% reservado se o setup melhorar: ~{_fmt_money(budget * 0.40)}",
        ]
    return [
        f"  - 40% inicial: ~{_fmt_money(budget * 0.40)}",
        f"  - 30% em pullback: ~{_fmt_money(budget * 0.30)}",
        f"  - 30% reservado para confirmacao/invalidacao: ~{_fmt_money(budget * 0.30)}",
    ]


# ---------------------------------------------------------------------------
# Analysis stance
# ---------------------------------------------------------------------------
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
            "AGUARDAR / COMPRA SO EM PULLBACK",
            f"RSI alto e preco perto da resistencia; tendencia ainda positiva, mas a entrada ideal ja nao e aqui. "
            f"Pullback razoavel seria procurar preco mais perto de {support}. Score tecnico {score}/100.",
        )
    if rsi >= 70:
        return (
            "AGUARDAR PULLBACK",
            f"RSI alto; apesar do contexto positivo, o risco de comprar esticado e maior. "
            f"Melhor esperar aproximacao ao suporte em {support} ou nova consolidacao. Score tecnico {score}/100.",
        )
    if zone == "ZONA_DE_COMPRA" and rsi < 65:
        return (
            recs.get("acao_principal", "COMPRA CONTROLADA"),
            f"Preco em zona de compra com RSI ainda controlado. Score tecnico {score}/100.",
        )
    if zone == "ZONA_DE_VENDA":
        return (
            "REALIZAR / AGUARDAR",
            f"Preco em zona de venda; melhor proteger lucro do que perseguir entrada. Score tecnico {score}/100.",
        )
    if trend == "UPTREND":
        return (
            "AGUARDAR CONFIRMACAO",
            f"Tendencia positiva, mas sem zona de entrada clara. "
            f"Se corrigir, o suporte relevante abaixo esta perto de {support}. Score tecnico {score}/100.",
        )
    return (
        recs.get("acao_principal", "AGUARDAR"),
        f"Sinais mistos; esperar melhor relacao risco/retorno. Score tecnico {score}/100.",
    )


# ---------------------------------------------------------------------------
# Response generators
# ---------------------------------------------------------------------------
def _format_snapshot_followup(prompt: str, coin: str, content: str, side: str = "buy"):
    metrics = _snapshot_metrics_from_text(content)
    price = metrics.get("price", "N/A")
    liquidity_text = metrics.get("liquidity", "N/A")
    volume_text = metrics.get("volume", "N/A")
    liquidity = _parse_compact_money(liquidity_text)
    volume = _parse_compact_money(volume_text)
    risk = _snapshot_risk_label(liquidity, volume)
    entry_price = _extract_entry_price(prompt)
    current_value = _parse_number_text(price)
    position = _extract_position_size(prompt, coin)
    position_summary = _position_summary(position, entry_price, current_value)

    def generate_buy():
        yield f"Com base no snapshot DexScreener de **{coin}**:\n\n"
        if risk in {"RISCO MUITO ELEVADO", "RISCO ELEVADO"}:
            yield "**Eu nao trataria isto como compra tecnica normal. Falta liquidez/volume para confiar num setup.**\n\n"
        else:
            yield "**Isto ainda e so uma leitura de mercado, nao uma analise tecnica completa. Entrada teria de ser pequena e muito controlada.**\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Liquidez: **{liquidity_text}**\n"
        yield f"- Volume 24h: **{volume_text}**\n"
        yield f"- Risco: **{risk}**\n"
        yield "- Sem candles fiaveis, nao ha RSI, suporte, stop ou targets tecnicos confiaveis.\n"
        yield "- Antes de comprar, eu confirmaria contrato, holders, liquidez bloqueada e atividade real no par.\n"

    def generate_sell():
        if entry_price is None:
            yield f"Para avaliar venda de **{coin}**, preciso do teu preco medio de entrada.\n\n"
            yield f"- Preco atual: **{price}**\n"
            yield f"- Liquidez: **{liquidity_text}**\n"
            yield f"- Risco: **{risk}**\n\n"
            yield "Exemplo: `comprei a 0.000002, devo vender?`\n"
            return
        pnl_pct = None
        if current_value and entry_price:
            pnl_pct = ((current_value - entry_price) / entry_price) * 100
        yield f"Com base no snapshot DexScreener de **{coin}**, olhando pelo lado de venda:\n\n"
        if risk in {"RISCO MUITO ELEVADO", "RISCO ELEVADO"}:
            yield "**Aqui a prioridade e gestao de risco, porque a liquidez/volume podem nao aguentar uma saida limpa.**\n\n"
        else:
            yield "**Eu olharia para venda parcial por gestao de risco, mas sem targets tecnicos calculados por falta de candles.**\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Teu preco medio: **{_fmt_price(entry_price)}**\n"
        if pnl_pct is not None:
            yield f"- Resultado aproximado: **{pnl_pct:.1f}%**\n"
        if position_summary:
            yield f"- Quantidade estimada: **{position_summary['units']:.4g} {coin}**\n"
            yield f"- Capital investido: **{_fmt_money(position_summary['invested'])}**\n"
            yield f"- Valor atual estimado: **{_fmt_money(position_summary['current_value'])}**\n"
            yield f"- PnL estimado: **{_fmt_money(position_summary['pnl_value'])} ({position_summary['pnl_pct']:.1f}%)**\n"
        yield f"- Liquidez: **{liquidity_text}**\n"
        yield f"- Volume 24h: **{volume_text}**\n"
        yield f"- Risco: **{risk}**\n"
        yield "- Sem candles fiaveis, eu nao inventaria targets; usaria liquidez e tamanho da posicao para decidir saida parcial.\n"

    def generate_detail():
        yield f"Com base no snapshot DexScreener de **{coin}**:\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Liquidez: **{liquidity_text}**\n"
        yield f"- Volume 24h: **{volume_text}**\n"
        yield f"- Risco: **{risk}**\n"
        yield "- Nao ha candles historicos suficientes para calcular targets, stop, RSI ou suportes com qualidade.\n"

    if side == "sell":
        return generate_sell
    if side == "detail":
        return generate_detail
    return generate_buy


def _format_text_analysis_followup(history: list[ChatHistoryMessage], prompt: str = ""):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None
    if "Snapshot de mercado" in content:
        return _format_snapshot_followup("", coin, content, side="buy")

    price = _extract_markdown_value(content, "Preco atual")
    rsi = _extract_markdown_value(content, "RSI 14")
    if rsi == "N/A":
        rsi = _extract_markdown_value(content, "RSI")
    zone_match = re.search(r"preco esta em\s+\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
    zone = zone_match.group(1).strip() if zone_match else _extract_markdown_value(content, "Zona atual")
    action_match = re.search(r"\*\*Resumo:\*\*\s*([^.\n]+)", content, re.IGNORECASE)
    action = action_match.group(1).strip() if action_match else _extract_markdown_value(content, "Sinal tecnico")
    stop = _extract_markdown_value(content, "Stop loss")
    target_matches = _extract_targets(content)

    try:
        rsi_value = float(rsi)
    except (TypeError, ValueError):
        rsi_value = 50.0
    budget_info = _extract_position_size(prompt, coin)
    budget = budget_info.get("amount") if budget_info and budget_info.get("type") == "fiat" else None

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
        if budget:
            yield "- Plano de entrada faseada possivel:\n"
            for line in _entry_plan_lines(float(budget), cautious=("AGUARDAR" in action.upper() or rsi_value >= 68)):
                yield f"{line}\n"

    return generate


def _format_text_sell_followup(prompt: str, history: list[ChatHistoryMessage]):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None
    if "Snapshot de mercado" in content:
        return _format_snapshot_followup(prompt, coin, content, side="sell")

    price = _extract_markdown_value(content, "Preco atual")
    rsi = _extract_markdown_value(content, "RSI 14")
    if rsi == "N/A":
        rsi = _extract_markdown_value(content, "RSI")
    zone = _extract_markdown_value(content, "Zona atual")
    if zone == "N/A":
        zone_match = re.search(r"preco esta em\s+\*\*([^*\n]+)\*\*", content, re.IGNORECASE)
        zone = zone_match.group(1).strip() if zone_match else "N/A"
    target_matches = _extract_targets(content)

    try:
        rsi_value = float(rsi)
    except (TypeError, ValueError):
        rsi_value = 50.0
    current_value = _parse_number_text(price)
    entry_price = _extract_entry_price(prompt)

    if entry_price is None:
        def ask_entry():
            yield f"Antes de dizer se faz sentido vender **{coin}**, preciso do teu preco medio de entrada.\n\n"
            yield f"- Preco atual: **{price}**\n"
            yield f"- Zonas tecnicas de venda/realizacao: {', '.join(target_matches[:3]) if target_matches else 'N/A'}\n\n"
            yield "Exemplo: `comprei a 5.5, devo vender?`\n\n"
        return ask_entry

    pnl_pct = None
    if current_value and entry_price:
        pnl_pct = ((current_value - entry_price) / entry_price) * 100
    position = _extract_position_size(prompt, coin)
    position_summary = _position_summary(position, entry_price, current_value)

    if pnl_pct is not None and pnl_pct < -10:
        decision = "Como estas em perda, eu nao trataria isto como realizacao de lucro. A decisao passa por gerir risco: vender parcial se a tese mudou, ou esperar recuperacao tecnica se ainda acreditas no setup."
    elif rsi_value >= 70:
        decision = "Se ja tens posicao, faz sentido considerar realizacao parcial; nao precisa ser tudo de uma vez."
    elif target_matches:
        decision = "Eu usaria os targets como zonas de venda parcial, mantendo gestao de risco."
    else:
        decision = "Eu nao venderia por impulso; procuraria uma zona tecnica clara de realizacao."

    def generate():
        yield f"Com base na analise anterior de **{coin}**, olhando pelo lado de venda:\n\n"
        yield f"**{decision}**\n\n"
        yield f"- Preco atual: **{price}**\n"
        yield f"- Teu preco medio: **{_fmt_price(entry_price)}**\n"
        if pnl_pct is not None:
            yield f"- Resultado aproximado: **{pnl_pct:.1f}%**\n"
        if position_summary:
            yield f"- Quantidade estimada: **{position_summary['units']:.4g} {coin}**\n"
            yield f"- Capital investido: **{_fmt_money(position_summary['invested'])}**\n"
            yield f"- Valor atual estimado: **{_fmt_money(position_summary['current_value'])}**\n"
            yield f"- PnL estimado: **{_fmt_money(position_summary['pnl_value'])} ({position_summary['pnl_pct']:.1f}%)**\n"
        yield f"- Zona atual: **{zone}**\n"
        yield f"- RSI: **{rsi}**\n"
        if target_matches:
            yield "- Zonas de venda/realizacao:\n"
            for target in target_matches[:3]:
                yield f"  - {target}\n"
            if position_summary and position_summary.get("current_value"):
                yield "- Plano faseado possivel:\n"
                yield f"  - 30% da posicao: ~{_fmt_money(position_summary['current_value'] * 0.30)}\n"
                yield f"  - 50% da posicao: ~{_fmt_money(position_summary['current_value'] * 0.50)}\n"
                yield f"  - 20% restante: deixar correr se mantiver forca\n"
        else:
            yield "- Nao encontrei targets claros na ultima analise.\n"

    return generate


def _format_text_analysis_detail_followup(prompt: str, history: list[ChatHistoryMessage]):
    coin, content = _latest_analysis_text(history)
    if not coin or not content:
        return None
    if "Snapshot de mercado" in content:
        return _format_snapshot_followup(prompt, coin, content, side="detail")

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
    target_matches = _extract_targets(content)

    def generate():
        yield f"Com base na analise anterior de **{coin}**:\n\n"
        if any(t in prompt_lower for t in ["risco", "stop", "invalidacao", "invalidação"]):
            yield f"- Risco: **{risk}**\n" if risk != "N/A" else "- Risco: nao apareceu explicitamente na ultima resposta.\n"
            if stop != "N/A":
                yield f"- Invalida se perder: **{stop}**\n"
            yield f"- Contexto: preco em **{zone}**, RSI **{rsi}**, sinal **{action}**.\n"
        elif any(t in prompt_lower for t in ["target", "targets", "alvo", "alvos"]):
            if target_matches:
                yield "Zonas de realizacao que estavam no plano:\n"
                for target in target_matches[:3]:
                    yield f"- {target}\n"
            else:
                yield "Nao encontrei targets claros na ultima analise.\n"
        elif any(t in prompt_lower for t in ["onde entro", "entrada ideal", "plano"]):
            yield f"- Entrada: **{zone}**\n"
            yield f"- Preco atual: **{price}**\n"
            yield f"- Sinal: **{action}**\n"
            if stop != "N/A":
                yield f"- Stop/invalidação: **{stop}**\n"
        else:
            yield f"O racional principal e: preco em **{zone}**, RSI **{rsi}** e sinal **{action}**.\n"
            yield "Isto favorece uma leitura faseada/disciplinada, nao uma entrada all-in.\n"

    return generate


def _format_trade_followup(prompt: str, history: list[ChatHistoryMessage] | None = None):
    cached = LAST_COIN_ANALYSIS or {}
    coin = cached.get("coin")
    result = cached.get("result") or {}
    if not coin or not result:
        return _format_text_analysis_followup(history or [], prompt)
    if result.get("snapshot_only"):
        snapshot_lines = list(_format_coin_analysis(coin, result))
        return _format_snapshot_followup(prompt, coin, "".join(snapshot_lines), side="buy")

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
    budget_info = _extract_position_size(prompt, coin)
    budget = budget_info.get("amount") if budget_info and budget_info.get("type") == "fiat" else None

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
        if budget:
            yield "- Plano de entrada faseada possivel:\n"
            for line in _entry_plan_lines(float(budget), cautious=(action.startswith("AGUARDAR") or rsi >= 68 or position >= 75)):
                yield f"{line}\n"

    return generate


def _rsi_label_analysis(rsi: float) -> str:
    if rsi < 28:
        return "Oversold extremo — possível bounce forte"
    if rsi < 38:
        return "Oversold — vendedores enfraquecidos"
    if rsi < 50:
        return "Neutro baixo — equilíbrio pendendo para baixo"
    if rsi < 62:
        return "Neutro — equilíbrio"
    if rsi < 70:
        return "Neutro alto — compradores dominam"
    return "Overbought — evitar novas compras"


def _format_coin_analysis(coin: str, result: dict):
    if result.get("snapshot_only"):
        changes = result.get("price_change") or {}
        yield f"## 📊 {coin} — Snapshot de mercado\n\n"
        yield "_Sem candles históricos suficientes — leitura rápida via DexScreener._\n\n"
        yield f"**Preço:** {_fmt_price(result.get('current_price'))} · "
        yield f"24h {_fmt_percent(changes.get('h24'))}\n\n"
        chain = result.get('chain') or 'N/A'
        dex = result.get('dex') or 'N/A'
        yield f"**Chain/DEX:** {chain} / {dex}\n"
        yield f"**Liquidez:** {_fmt_money(result.get('liquidity_usd'))}\n"
        yield f"**Volume 24h:** {_fmt_money(result.get('volume_24h'))}\n"
        if result.get("market_cap"):
            yield f"**Market cap:** {_fmt_money(result.get('market_cap'))}\n"
        elif result.get("fdv"):
            yield f"**FDV:** {_fmt_money(result.get('fdv'))}\n"
        if result.get("pair_url"):
            yield f"\n[Ver par no DexScreener]({result.get('pair_url')})\n"
        yield "\n⚠️ Sem candles fiáveis não há RSI, suportes ou targets calculáveis. Confirma liquidez, holders e contrato antes de qualquer decisão."
        return

    analysis = result.get("analysis", {}) or {}
    zones = result.get("trading_zones", {}) or {}
    recs = result.get("recommendations", {}) or {}
    strategy = recs.get("estrategia_trading", {}) or {}
    sr = analysis.get("support_resistance", {}) or {}
    ma = analysis.get("moving_averages", {}) or {}
    trend = analysis.get("trend", {}) or {}
    volume = analysis.get("volume", {}) or {}
    fib = analysis.get("fibonacci", {}) or {}
    fib_levels = fib.get("levels", {}) or {}

    action, summary = _analysis_stance(analysis, zones, recs)
    current_zone = _human_zone(zones.get("posicao_atual"))
    rsi_val = analysis.get("rsi")
    price = result.get("current_price")
    support = sr.get("dynamic_support")
    resistance = sr.get("dynamic_resistance")
    position_pct = sr.get("current_position")
    trend_dir = trend.get("direction", "")
    stop = strategy.get("stop_loss")
    targets = strategy.get("targets") or []
    risk_alert = recs.get("alerta_risco", "")

    price_f = float(price or 0)
    rsi_f = float(rsi_val) if rsi_val is not None else None
    sma200 = float((ma or {}).get("sma_200") or 0)
    sep = "━" * 30

    # ── VEREDICTO ────────────────────────────────────────────
    # Determinar a mensagem principal em linguagem simples
    is_buy_zone = current_zone == "zona de compra"
    is_sell_zone = current_zone == "zona de venda"
    is_oversold = rsi_f is not None and rsi_f < 35
    is_overbought = rsi_f is not None and rsi_f > 68
    awaiting = action.startswith("AGUARDAR")

    if is_buy_zone and is_oversold and not awaiting:
        verdict_icon = "🔥"
        verdict = "ZONA DE COMPRA FORTE — RSI em oversold, perto do suporte"
    elif is_buy_zone and not awaiting:
        verdict_icon = "🟢"
        verdict = "ZONA DE COMPRA — preço perto do suporte"
    elif is_sell_zone or is_overbought:
        verdict_icon = "🔴"
        verdict = "ZONA DE VENDA / REALIZAÇÃO — preço perto da resistência"
    elif awaiting and is_oversold:
        verdict_icon = "🟡"
        verdict = "AGUARDAR CONFIRMAÇÃO — RSI baixo mas sem momentum ainda"
    elif awaiting:
        verdict_icon = "🟡"
        verdict = "AGUARDAR — preço em zona neutra, sem entrada clara"
    else:
        verdict_icon = "🟡"
        verdict = "ZONA NEUTRA — sem sinal claro agora"

    yield f"# 📊 {coin} — Análise Técnica\n\n"
    yield f"{verdict_icon} **{verdict}**\n"
    yield f"{sep}\n\n"

    # ── PREÇO + PLANO (o mais importante primeiro) ────────────
    if price_f:
        yield f"**Preço atual:** {_fmt_price(price_f)}\n\n"

    if not awaiting and support and resistance and stop:
        upside = ((float(resistance) - price_f) / price_f) * 100 if price_f else 0
        downside = ((price_f - float(stop)) / price_f) * 100 if price_f else 0
        yield f"🎯 **Entrada:** perto de {_fmt_price(support)}\n"
        yield f"🚀 **Alvo:** {_fmt_price(resistance)}"
        if upside > 0:
            yield f" (+{upside:.0f}%)"
        yield "\n"
        yield f"🛡️ **Stop:** {_fmt_price(stop)}"
        if downside > 0:
            yield f" (-{downside:.0f}%)"
        yield "\n"
        if targets:
            yield "\n**Targets parciais:**\n"
            for t in targets[:3]:
                yield f"› {t}\n"
    elif awaiting and support:
        yield f"⏳ **Aguardar:** pullback para {_fmt_price(support)} antes de considerar entrada\n"
        if stop:
            yield f"🛡️ **Stop se entrar:** {_fmt_price(stop)}\n"

    yield f"\n{sep}\n\n"

    # ── PORQUÊ — indicadores em linguagem simples ─────────────
    yield "**Porquê esta leitura:**\n"

    if rsi_f is not None:
        rsi_emoji = "✅" if rsi_f < 45 else ("⚠️" if rsi_f < 70 else "🔴")
        yield f"{rsi_emoji} RSI {rsi_f:.1f} — {_rsi_label_analysis(rsi_f)}\n"

    if trend_dir:
        trend_emoji = "📈" if trend_dir == "UPTREND" else "📉"
        yield f"{trend_emoji} Tendência de curto prazo: **{trend_dir}**"
        strength = trend.get("strength")
        if strength:
            yield f" ({_fmt_percent(strength)} divergência)"
        yield "\n"

    if ma and sma200 > 0:
        if price_f > sma200:
            yield f"✅ Acima da SMA200 — tendência macro bullish\n"
        else:
            yield f"⚠️ Abaixo da SMA200 — pressão macro vendedora\n"
        sma20 = float(ma.get("sma_20") or 0)
        sma50 = float(ma.get("sma_50") or 0)
        if sma20 and sma50:
            yield f"   SMA20 {_fmt_price(sma20)} · SMA50 {_fmt_price(sma50)} · SMA200 {_fmt_price(sma200)}\n"

    if volume:
        vol_trend = volume.get("trend", "")
        vol_ratio = volume.get("ratio_20d", 1)
        if vol_trend == "LOW":
            yield f"⚠️ Volume baixo ({vol_ratio}x média) — confirmar antes de entrar\n"
        elif vol_trend == "HIGH":
            yield f"✅ Volume alto ({vol_ratio}x média) — momentum confirmado\n"

    if fib_levels:
        fib_618 = fib_levels.get("0.618")
        fib_382 = fib_levels.get("0.382")
        if fib_618 and fib_382:
            yield f"📐 Fibonacci: 61.8% → {_fmt_price(fib_618)} · 38.2% → {_fmt_price(fib_382)}\n"

    if risk_alert and "MODERADO" not in risk_alert.upper():
        yield f"\n⚠️ {risk_alert}\n"
