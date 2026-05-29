from Api.main import (
    ChatHistoryMessage,
    _extract_position_size,
    _format_text_analysis_detail_followup,
    _format_text_analysis_followup,
    _format_text_sell_followup,
    _normalize_coin_symbol,
)


SNAPSHOT = """# Snapshot de mercado de BOINK

Nao encontrei candles historicos suficientes nos providers principais.

## Dados rapidos

- Preco atual: **$0.00000246**
- Chain/DEX: **solana / raydium**
- Liquidez: **$3.8K**
- Volume 24h: **$3**
- Market cap: **$2.5K**

Sem candles fiaveis, eu nao calcularia RSI, suportes ou targets tecnicos aqui.
"""

TECHNICAL = """# Analise tecnica de NEAR

**Resumo:** AGUARDAR PULLBACK com confianca MÉDIA. Score tecnico 40/100. O preco esta em **zona de venda**.

## Leitura rapida

- Preco atual: **$2.50**
- RSI 14: **75.0**

## Plano

- Stop loss: $1.14
- Targets:
  - 2.76 - 2.82 (30%)
  - 2.82 - 2.96 (50%)
  - 2.96 + (20%)

Risco: **RISCO MODERADO**
"""


def _history():
    return [ChatHistoryMessage(role="assistant", content=SNAPSHOT)]


def _technical_history():
    return [ChatHistoryMessage(role="assistant", content=TECHNICAL)]


def test_snapshot_buy_followup_does_not_invent_technicals():
    response = "".join(_format_text_analysis_followup(_history())())

    assert "BOINK" in response
    assert "RISCO MUITO ELEVADO" in response
    assert "nao ha RSI" in response
    assert "targets tecnicos confiaveis" in response


def test_snapshot_sell_followup_asks_entry_price():
    response = "".join(_format_text_sell_followup("devo vender?", _history())())

    assert "preco medio de entrada" in response
    assert "$0.00000246" in response


def test_snapshot_sell_followup_uses_entry_price():
    response = "".join(_format_text_sell_followup("comprei a 0.000003", _history())())

    assert "Teu preco medio" in response
    assert "Resultado aproximado" in response
    assert "nao inventaria targets" in response


def test_snapshot_detail_followup_explains_missing_targets():
    response = "".join(_format_text_analysis_detail_followup("quais os targets?", _history())())

    assert "Nao ha candles historicos suficientes" in response
    assert "targets" in response


def test_coin_symbol_aliases_normalize_common_inputs():
    assert _normalize_coin_symbol("nea") == "NEAR"
    assert _normalize_coin_symbol("rndr") == "RENDER"
    assert _normalize_coin_symbol("hyperliquid") == "HYPE"


def test_extract_position_size_from_fiat_and_units():
    assert _extract_position_size("tenho 1000€ comprei a 5.5", "NEAR") == {"type": "fiat", "amount": 1000.0}
    assert _extract_position_size("tenho 200 NEAR comprei a 5.5", "NEAR") == {"type": "units", "amount": 200.0}


def test_sell_followup_includes_position_math_for_fiat_position():
    response = "".join(
        _format_text_sell_followup("tenho 1000€ comprei a 5.5, devo vender?", _technical_history())()
    )

    assert "Capital investido" in response
    assert "Valor atual estimado" in response
    assert "PnL estimado" in response
    assert "Plano faseado possivel" in response
