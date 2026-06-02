from __future__ import annotations

import json
from typing import Any, Dict

from Api.routes import alerts
from Api.services.chat_helpers import LAST_COIN_ANALYSIS, _format_coin_analysis, _normalize_coin_symbol


def _answer_payload(answer: str, **extra: Any) -> Dict[str, Any]:
    return {"ok": True, "answer": answer, **extra}


async def analyze_coin(symbol: str) -> Dict[str, Any]:
    coin = _normalize_coin_symbol(symbol)
    if not coin:
        return _answer_payload("Indica o simbolo da moeda. Exemplo: `analisa BTC`.", error="missing_symbol")

    from Api.services.crypto_tools import analyze_coin_tool

    result = await analyze_coin_tool(coin)
    if "error" in result:
        return _answer_payload(f"Erro ao analisar {coin}: {result.get('error')}", error=result.get("error"))

    LAST_COIN_ANALYSIS.clear()
    LAST_COIN_ANALYSIS.update({"coin": coin, "result": result})
    answer = "".join(_format_coin_analysis(coin, result))
    return _answer_payload(answer, symbol=coin, result=result)


def get_top100_rankings(mode: str = "score") -> Dict[str, Any]:
    prompts = {
        "score": "que moedas me aconselhas a analisar hoje do top100?",
        "low_risk": "quais moedas do top100 tem menos risco?",
        "near_support": "quais do top100 estao perto do suporte?",
        "low_rsi": "quais do top100 tem RSI mais baixo?",
        "risk_reward": "quais do top100 tem melhor relacao risco retorno?",
        "bounce": "quais do top100 confirmaram reversao?",
        "delta": "o que mudou no top100 desde ontem?",
    }
    prompt = prompts.get((mode or "score").strip(), prompts["score"])
    return alerts._answer_top100_buy_watchlist(prompt=prompt)


def get_listing_predictions() -> Dict[str, Any]:
    items = alerts.get_predictions()
    if not items:
        return _answer_payload("Nao encontrei potenciais listings visiveis agora.", count=0, items=[])

    lines = [f"**Potenciais listings atuais ({len(items)} visiveis)**"]
    for i, item in enumerate(items[:10], 1):
        token = item.get("token") or "N/A"
        exchange = alerts._normalize_exchange(item.get("exchange") or "")
        score = float(item.get("score") or 0)
        value = alerts._fmt_money(item.get("value_usd"))
        liquidity = alerts._fmt_money(item.get("liquidity"))
        lines.append(f"{i}. **{token}** - {exchange} - score {score:.0f}/100 - valor {value} - liquidez {liquidity}")
    return _answer_payload("\n".join(lines), count=len(items), items=items)


def get_recent_holdings() -> Dict[str, Any]:
    data = alerts.get_holdings()
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        return _answer_payload("Nao encontrei holdings recentes visiveis agora.", count=0, items=[])

    lines = [f"**Holdings recentes em wallets de exchanges ({min(len(items), 10)})**"]
    for i, item in enumerate(items[:10], 1):
        token = item.get("token") or "N/A"
        exchange = alerts._normalize_exchange(item.get("exchange") or "")
        score = float(item.get("score") or 0)
        value = alerts._fmt_money(item.get("value_usd"))
        lines.append(f"{i}. **{token}** - {exchange} - score {score:.0f}/100 - valor {value}")
    return _answer_payload("\n".join(lines), count=len(items), items=items)


def get_top100_delta() -> Dict[str, Any]:
    return alerts._answer_top100_buy_watchlist(prompt="o que mudou no top100 desde ontem?")


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_coin",
            "description": "Analisa tecnicamente uma criptomoeda por simbolo, com RSI, suporte, resistencia, stop e targets.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Simbolo da moeda, por exemplo BTC, SOL, PEPE."}},
                "required": ["symbol"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top100_rankings",
            "description": "Consulta o ranking tecnico diario do top100 por score, risco, suporte, RSI, risco/retorno ou reversao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["score", "low_risk", "near_support", "low_rsi", "risk_reward", "bounce", "delta"],
                    }
                },
                "required": ["mode"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_listing_predictions",
            "description": "Lista potenciais listings com base em tokens acumulados por wallets de exchanges e ainda nao listados na propria exchange.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_holdings",
            "description": "Lista holdings recentes detectados em wallets de exchanges, mesmo que ja estejam listados.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top100_delta",
            "description": "Compara o ranking tecnico top100 de hoje com ontem e mostra as maiores mudancas.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


async def execute_tool(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    args = arguments or {}
    if name == "analyze_coin":
        return await analyze_coin(str(args.get("symbol") or ""))
    if name == "get_top100_rankings":
        return get_top100_rankings(str(args.get("mode") or "score"))
    if name == "get_listing_predictions":
        return get_listing_predictions()
    if name == "get_recent_holdings":
        return get_recent_holdings()
    if name == "get_top100_delta":
        return get_top100_delta()
    return {"ok": False, "error": f"Ferramenta desconhecida: {name}", "answer": "Ferramenta desconhecida."}


def parse_tool_arguments(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
