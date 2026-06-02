import pytest

from Api.services import chat_helpers as ch


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("achas boa compra?", True),
        ("vale a pena comprar?", True),
        ("onde entro?", True),
        ("should i buy BTC?", True),
        ("e agora ainda achas o mesmo?", True),
        ("que tokens vao ser listados?", False),
        ("previsao de listing", False),
        ("que moedas do top100 compro?", False),
        ("explica RSI", False),
        ("bom dia", False),
    ],
)
def test_trade_followup_classifier(prompt, expected):
    assert ch._is_trade_followup(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("devo vender?", True),
        ("onde vendo?", True),
        ("onde saio?", True),
        ("realizo lucro?", True),
        ("take profit aqui?", True),
        ("qual o risco?", False),
        ("onde entro?", False),
        ("analisa BTC", False),
    ],
)
def test_sell_followup_classifier(prompt, expected):
    assert ch._is_sell_followup(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("comprei a 5.5", True),
        ("preco medio 2.4", True),
        ("entrada a $10", True),
        ("medio de 0.3", True),
        ("qual o stop?", False),
        ("analisa near", False),
    ],
)
def test_entry_price_classifier(prompt, expected):
    assert ch._is_entry_price_followup(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("qual o risco?", True),
        ("quais os targets?", True),
        ("explica porque", True),
        ("qual o stop?", True),
        ("onde entro?", True),
        ("analisa BTC", False),
        ("bom dia", False),
    ],
)
def test_analysis_detail_classifier(prompt, expected):
    assert ch._is_analysis_detail_followup(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("como funciona?", True),
        ("o que fazes?", True),
        ("what can you do?", True),
        ("how does this work?", True),
        ("analisa BTC", False),
        ("devo comprar?", False),
    ],
)
def test_onboarding_classifier(prompt, expected):
    assert ch._is_onboarding_question(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("analisa BTC", True),
        ("analise tecnica de SOL", True),
        ("analisa-me graficamente PEPE", True),
        ("quero ver o grafico de NEAR", True),
        ("que moedas do top100 analiso?", False),
        ("que tokens vao ser listados?", False),
        ("achas boa compra?", False),
    ],
)
def test_coin_analysis_classifier(prompt, expected):
    assert ch._should_use_coin_analysis(prompt) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("nea", "NEAR"),
        ("RNDR", "RENDER"),
        ("hyperliquid", "HYPE"),
        ("dogwifhat", "WIF"),
        ("fetch", "FET"),
        ("btc", "BTC"),
        ("$pepe!", "PEPE"),
    ],
)
def test_coin_symbol_normalization_matrix(raw, expected):
    assert ch._normalize_coin_symbol(raw) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("comprei a 5.5", 5.5),
        ("preco medio 2,4", 2.4),
        ("entrada a $10", 10),
        ("medio de 0.000003", 0.000003),
    ],
)
def test_extract_entry_price_matrix(prompt, expected):
    assert ch._extract_entry_price(prompt) == expected


@pytest.mark.parametrize(
    ("prompt", "coin", "expected"),
    [
        ("tenho 1000 euros comprei a 5", "NEAR", {"type": "fiat", "amount": 1000.0}),
        ("tenho $250 em posicao", "BTC", {"type": "fiat", "amount": 250.0}),
        ("tenho 200 NEAR", "NEAR", {"type": "units", "amount": 200.0}),
        ("tenho 50 moedas", None, {"type": "units", "amount": 50.0}),
    ],
)
def test_extract_position_size_matrix(prompt, coin, expected):
    assert ch._extract_position_size(prompt, coin) == expected


def test_portfolio_context_line_from_history():
    history = [ch.ChatHistoryMessage(role="user", content="comprei BTC a 65000 e SOL a 150")]

    context = ch._portfolio_context_line(history)

    assert "BTC" in context
    assert "SOL" in context


def test_extract_targets_from_plain_block():
    content = "Targets:\n10.71 - 10.93 (30%)\n10.93 - 11.48 (50%)\n"

    assert ch._extract_targets(content) == ["10.71 - 10.93 (30%)", "10.93 - 11.48 (50%)"]

