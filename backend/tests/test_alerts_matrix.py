import pytest

from Api.routes import alerts


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("o que mudou no top100 desde ontem?", "delta"),
        ("quais moedas do top100 tem menos risco?", "low_risk"),
        ("melhor relacao risco retorno top100", "risk_reward"),
        ("best risk reward top100", "risk_reward"),
        ("comprar hoje top100 confirmado", "bounce"),
        ("best confirmed buy in the top100", "bounce"),
        ("quais estao perto do suporte top100?", "near_support"),
        ("which top 100 coins are near support?", "near_support"),
        ("rsi mais baixo top100", "low_rsi"),
        ("which top 100 coins have the lowest RSI?", "low_rsi"),
        ("que moedas analisar hoje top100?", "score"),
    ],
)
def test_top100_mode_matrix(prompt, expected):
    assert alerts._top100_mode(prompt) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("que moedas me aconselhas a comprar hoje do top100?", True),
        ("quais as melhores moedas para analisar hoje?", True),
        ("quais moedas estao perto do suporte?", True),
        ("top 100 crypto buy opportunities", True),
        ("which top 100 coins are near support?", True),
        ("which top 100 coins have the lowest RSI?", True),
        ("analisa BTC", False),
        ("que tempo faz hoje?", False),
    ],
)
def test_buy_watchlist_question_matrix(prompt, expected):
    assert alerts._is_buy_watchlist_question(prompt) is expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("top100 comprar hoje", True),
        ("top 100 rsi baixo", True),
        ("top100 perto do suporte", True),
        ("top 100 near support", True),
        ("top100 changed since yesterday", True),
        ("top100", False),
        ("comprar BTC", False),
    ],
)
def test_top100_buy_question_matrix(prompt, expected):
    assert alerts._is_top100_buy_question(prompt) is expected


def _rows():
    return [
        {
            "symbol": "HIGH",
            "score": 90,
            "risk": "ELEVADO",
            "current_position": 85,
            "rsi": 75,
            "price": 10,
            "support": 8,
            "resistance": 12,
            "entry_zone": "ZONA_DE_VENDA",
            "macd_signal": "BEARISH",
        },
        {
            "symbol": "SAFE",
            "score": 70,
            "risk": "BAIXO/MODERADO",
            "current_position": 30,
            "rsi": 34,
            "price": 10,
            "support": 9,
            "resistance": 14,
            "entry_zone": "ZONA_DE_COMPRA",
            "macd_signal": "BULLISH_STRONG",
        },
        {
            "symbol": "MID",
            "score": 80,
            "risk": "MODERADO",
            "current_position": 50,
            "rsi": 45,
            "price": 10,
            "support": 6,
            "resistance": 16,
            "entry_zone": "ZONA_NEUTRA",
            "macd_signal": "NEUTRO",
        },
    ]


@pytest.mark.parametrize(
    ("mode", "expected_first"),
    [
        ("score", "HIGH"),
        ("low_risk", "SAFE"),
        ("near_support", "SAFE"),
        ("low_rsi", "SAFE"),
        ("risk_reward", "SAFE"),
        ("bounce", "SAFE"),
    ],
)
def test_sort_top100_rows_matrix(mode, expected_first):
    assert alerts._sort_top100_rows(_rows(), mode)[0]["symbol"] == expected_first


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BAIXO/MODERADO", 0),
        ("MODERADO", 1),
        ("MODERADO/ELEVADO", 2),
        ("ELEVADO", 3),
        ("", 1),
    ],
)
def test_risk_rank_matrix(value, expected):
    assert alerts._risk_rank(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "$0.00"),
        (0.0000123, "$1.23e-05"),
        (2.5, "$2.50"),
        (1500, "$1.5K"),
        (2_000_000, "$2.00M"),
        (3_000_000_000, "$3.00B"),
    ],
)
def test_fmt_money_matrix(value, expected):
    assert alerts._fmt_money(value) == expected


@pytest.mark.parametrize(
    ("zone", "expected"),
    [
        ("ZONA_DE_COMPRA", "compra"),
        ("ZONA_DE_VENDA", "venda"),
        ("ZONA_NEUTRA", "neutra"),
        ("OUTRA", "outra"),
    ],
)
def test_human_zone_label_matrix(zone, expected):
    assert alerts._human_zone_label(zone) == expected


def test_format_top100_block_contains_actionable_fields():
    block = alerts._format_top100_block(1, _rows()[1], "near_support")

    assert "SAFE" in block
    assert "Entrada" in block or "Suporte" in block


def test_merge_prediction_backfill_deduplicates_by_exchange_token_chain():
    recent = [{"exchange": "Gate.io", "token": "AAA", "chain": "solana", "score": 80}]
    fallback = [
        {"exchange": "Gate.io", "token": "AAA", "chain": "solana", "score": 75},
        {"exchange": "Binance 2", "token": "AAA", "chain": "solana", "score": 70},
    ]

    merged = alerts._merge_prediction_backfill(recent, fallback)

    assert len(merged) == 2
    assert merged[0]["exchange"] == "Gate.io"
