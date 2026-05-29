from Api.main import (
    ChatHistoryMessage,
    _format_text_analysis_detail_followup,
    _format_text_analysis_followup,
    _format_text_sell_followup,
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


def _history():
    return [ChatHistoryMessage(role="assistant", content=SNAPSHOT)]


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
