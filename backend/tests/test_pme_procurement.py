from decimal import Decimal

from Api.services.pme_procurement import (
    RawCatalog,
    compare_catalogs,
    normalize_product_name,
    parse_purchase_needs,
    parse_commercial_values,
)


def test_normalize_product_name_groups_pack_sizes():
    assert normalize_product_name("Coca Cola 24x33cl lata") == "coca cola"
    assert normalize_product_name("Coca-Cola 33 cl") == "coca cola"


def test_compare_catalogs_uses_effective_price_with_promotions():
    supplier_a = RawCatalog(
        filename="sumol.csv",
        text=(
            "fornecedor;produto;quantidade;unidade;preço;promoções\n"
            "Sumol;Coca Cola 24x33cl;1;caixa;18,90;\n"
        ),
    )
    supplier_b = RawCatalog(
        filename="super_bock.csv",
        text=(
            "fornecedor;produto;quantidade;unidade;preço;promoções\n"
            "Super Bock;Coca-Cola 24x33cl;1;caixa;19,40;Oferta de 10 copos\n"
        ),
    )

    result = compare_catalogs([supplier_a, supplier_b])

    assert result.products_compared == 1
    recommendation = result.recommendations[0]
    assert recommendation.recommended_supplier == "Super Bock"
    assert recommendation.estimated_savings == Decimal("7.50")
    best = recommendation.alternatives[0]
    assert best.effective_unit_price == Decimal("11.40")
    assert best.commercial_value == Decimal("8.00")
    assert best.commercial_terms[0].label == "10 copos"


def test_compare_catalogs_warns_on_missing_headers():
    result = compare_catalogs(
        [
            RawCatalog(
                filename="bad.csv",
                text="nome;valor\nSem preço;10\n",
            )
        ]
    )

    assert result.total_items == 0
    assert result.warnings


def test_offer_without_quantity_is_not_valued_automatically():
    result = compare_catalogs(
        [
            RawCatalog(
                filename="supplier.csv",
                text=(
                    "fornecedor;produto;preco;promocoes\n"
                    "Fornecedor;Coca Cola 24x33cl;18,90;Oferta de copos\n"
                ),
            )
        ]
    )

    assert result.total_items == 1
    assert result.warnings
    assert "sem valor automático" in result.warnings[0]


def test_purchase_needs_multiply_weekly_savings():
    supplier_a = RawCatalog(
        filename="a.csv",
        text="fornecedor;produto;preco;promocoes\nA;Coca Cola 24x33cl;18,90;\n",
    )
    supplier_b = RawCatalog(
        filename="b.csv",
        text="fornecedor;produto;preco;promocoes\nB;Coca-Cola 24x33cl;18,91;Oferta de 10 copos\n",
    )

    result = compare_catalogs(
        [supplier_a, supplier_b],
        parse_purchase_needs("20; Coca Cola 24x33cl"),
    )

    rec = result.recommendations[0]
    assert rec.requested_quantity == 20
    assert rec.estimated_savings == Decimal("159.80")
    assert result.estimated_savings_week == Decimal("159.80")


def test_loose_text_catalog_lines_are_parsed():
    result = compare_catalogs(
        [
            RawCatalog(filename="a.txt", text="Coca Cola 24x33cl 18,90\n"),
            RawCatalog(filename="b.txt", text="Coca-Cola 24x33cl 18,91 Oferta de 10 copos\n"),
        ]
    )

    assert result.products_compared == 1
    assert result.recommendations[0].recommended_supplier == "B"
    assert result.recommendations[0].estimated_savings == Decimal("7.99")


def test_custom_commercial_values_override_defaults():
    result = compare_catalogs(
        [
            RawCatalog(filename="a.csv", text="fornecedor;produto;preco;promocoes\nA;Coca Cola 24x33cl;18,90;\n"),
            RawCatalog(filename="b.csv", text="fornecedor;produto;preco;promocoes\nB;Coca-Cola 24x33cl;18,91;Oferta de 10 copos\n"),
        ],
        commercial_values=parse_commercial_values("copos=0.50"),
    )

    best = result.recommendations[0].alternatives[0]
    assert best.commercial_value == Decimal("5.00")
    assert result.recommendations[0].estimated_savings == Decimal("4.99")
