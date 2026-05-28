from __future__ import annotations

from typing import Any, Dict

from analisegrafica.coin_analysis import AdvancedCoinAnalyzer


async def analyze_coin_tool(symbol: str, period: str = "60d") -> Dict[str, Any]:
    """Internal tool wrapper used by chat/agent flows."""
    analyzer = AdvancedCoinAnalyzer()
    return await analyzer.analyze_coin(symbol.upper(), period)


CRYPTO_TOOLS = {
    "analyze_coin": analyze_coin_tool,
}
