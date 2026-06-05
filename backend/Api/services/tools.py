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
    rows = alerts.get_predictions()
    if not rows:
        return _answer_payload("No fresh unlisted-token signals in the last 2 weeks. Monitoring continues.")

    grouped: dict = {}
    for r in rows:
        key = f"{(r.get('token') or '').upper()}@{r.get('exchange') or ''}"
        if key not in grouped:
            grouped[key] = {
                "rows": [],
                "token": r.get("token") or "-",
                "exchange": r.get("exchange") or "-",
                "chain": r.get("chain") or "-",
                "score": r.get("score"),
                "pair_url": r.get("pair_url"),
            }
        grouped[key]["rows"].append(r)

    entries = list(grouped.values())
    entries.sort(key=lambda x: x["score"] or 0, reverse=True)

    total = len(entries)
    limit = 3
    lines = [f"**Top signals on-chain detected**\n\n{total} signals filtered. Showing the {min(limit, total)} most relevant.\n"]
    for i, entry in enumerate(entries[:limit], 1):
        token = entry["token"]
        exchange = entry["exchange"]
        chain = str(entry["chain"] or "-").capitalize()
        score = entry["score"]
        score_txt = f"{score:.0f}/100" if isinstance(score, (int, float)) else "N/A"
        wallets = entry["rows"]
        total_val = sum(float(r.get("value_usd") or 0) for r in wallets)
        liq = wallets[0].get("liquidity")
        liq_txt = f"${liq:,.0f}" if isinstance(liq, (int, float)) else None

        line = f"{i}. **{token}** - {exchange} - {chain}\n   Score: {score_txt}"
        if len(wallets) > 1:
            line += f" - {len(wallets)} wallets - Total: ${total_val:,.0f}"
            for w in wallets:
                val = w.get("value_usd")
                if isinstance(val, (int, float)):
                    line += f"\n   - wallet: ${val:,.0f}"
        else:
            val = wallets[0].get("value_usd")
            line += f" - Wallet: ${val:,.0f}" if isinstance(val, (int, float)) else ""
        if liq_txt:
            line += f" - Liquidity: {liq_txt}"
        pair_url = entry.get("pair_url")
        if pair_url:
            line += f" - [DexScreener]({pair_url})"
        lines.append(line)

    if total > limit:
        lines.append(f"\n+ {total - limit} more signals. Ask *show more listings* to expand.")
    return _answer_payload("\n".join(lines), count=total, items=rows)


def get_recent_holdings() -> Dict[str, Any]:
    return alerts.ask_alerts(alerts.AskIn(prompt="mostra holdings recentes"))


def get_top100_delta() -> Dict[str, Any]:
    return alerts._answer_top100_buy_watchlist(prompt="o que mudou no top100 desde ontem?")


def get_smart_money(lang: str = "en") -> Dict[str, Any]:
    params = {
        "entity_type": "eq.smart_money",
        "signal_direction": "in.(new,increased,decreased)",
        "select": "entity,exchange,token,chain,score,value_usd,value_delta_usd,signal_direction,ts,pair_url",
        "order": "ts.desc",
        "limit": "100",
    }
    try:
        response = alerts.supa.rest_get("arkham_signals", params=params, timeout=10)
        if response.status_code != 200:
            legacy_params = {
                "type": "eq.smart_money",
                "select": "exchange,token,chain,score,value_usd,ts,pair_url",
                "order": "score.desc",
                "limit": "10",
            }
            response = alerts.supa.rest_get("transacted_tokens", params=legacy_params, timeout=10)
        if response.status_code != 200:
            return _answer_payload(
                f"Could not fetch smart money signals now. Supabase HTTP {response.status_code}.",
                count=0,
                items=[],
            )
        rows = response.json() or []
    except Exception as exc:
        return _answer_payload(f"Could not fetch smart money signals now: {exc}", count=0, items=[])

    english = str(lang or "en").lower().startswith("en")
    if not rows:
        msg = (
            "No smart money moves stored yet. Let the Arkham scanner run twice so it can compare deltas."
            if english else
            "Ainda nao ha movimentos de smart money guardados. Deixa o scanner Arkham correr duas vezes para conseguir comparar deltas."
        )
        return _answer_payload(msg, count=0, items=[])

    rows = sorted(
        rows,
        key=lambda row: (
            abs(float(row.get("value_delta_usd") or 0)),
            float(row.get("value_usd") or 0),
        ),
        reverse=True,
    )[:10]

    def _direction_label(value: str) -> str:
        if english:
            return {"new": "new position", "increased": "increased", "decreased": "reduced"}.get(value, "changed")
        return {"new": "nova posicao", "increased": "aumentou", "decreased": "reduziu"}.get(value, "mudou")

    title = "**Smart money / whale moves**\n" if english else "**Movimentos de whales / insiders**\n"
    subtitle = (
        "Largest Arkham-tracked position changes. This is not automatically a buy or sell.\n"
        if english else
        "Maiores alteracoes de posicao detectadas via Arkham. Isto nao e automaticamente compra ou venda.\n"
    )
    lines = [title, subtitle]
    for row in rows:
        token = str(row.get("token") or "?").upper()
        fund = row.get("entity") or row.get("exchange") or "Unknown fund"
        chain = str(row.get("chain") or "unknown").capitalize()
        score = row.get("score")
        value = row.get("value_usd")
        delta = row.get("value_delta_usd")
        direction = _direction_label(str(row.get("signal_direction") or "changed"))
        score_txt = f"{score:.0f}/100" if isinstance(score, (int, float)) else "N/A"
        value_txt = f"${value:,.0f}" if isinstance(value, (int, float)) else "N/A"
        if isinstance(delta, (int, float)):
            delta_label = "Delta" if english else "Variacao"
            delta_txt = f"{delta_label} ${delta:,.0f}"
        else:
            delta_txt = "Delta N/A" if english else "Variacao N/A"
        position_label = "Position" if english else "Posicao"
        line = f"- **{token}** - {fund} - {chain} - {direction} - {delta_txt} - {position_label} {value_txt} - Score {score_txt}"
        pair_url = row.get("pair_url")
        if pair_url:
            line += f" - [DexScreener]({pair_url})"
        lines.append(line)

    lines.append(
        "\n_Note: a position change can be a transfer, bridge, custody move or LP action._"
        if english else
        "\n_Nota: uma alteracao de posicao pode ser transferencia, bridge, custodia ou movimento de LP._"
    )
    return _answer_payload("\n".join(lines), count=len(rows), items=rows)


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
            "parameters": {
                "type": "object",
                "properties": {"lang": {"type": "string", "enum": ["pt", "en"]}},
                "additionalProperties": False,
            },
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
    {
        "type": "function",
        "function": {
            "name": "get_smart_money",
            "description": "Lista tokens relevantes em carteiras de fundos, market makers e whales monitorizados via Arkham.",
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
    if name == "get_smart_money":
        return get_smart_money(str(args.get("lang") or "en"))
    return {"ok": False, "error": f"Ferramenta desconhecida: {name}", "answer": "Ferramenta desconhecida."}


def parse_tool_arguments(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
