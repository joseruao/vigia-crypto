from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field


class CommercialTerm(BaseModel):
    type: str
    label: str
    quantity: Decimal = Field(default=Decimal("1"))
    unit: str = ""
    estimated_unit_value: Decimal = Field(default=Decimal("0"))
    estimated_total_value: Decimal = Field(default=Decimal("0"))
    confidence: str = "medium"
    raw_text: str = ""


class CatalogItem(BaseModel):
    supplier: str
    product: str
    description: str = ""
    quantity: Decimal = Field(default=Decimal("1"))
    unit: str = "un"
    unit_price: Decimal
    total_price: Decimal | None = None
    promotions: str = ""
    notes: str = ""
    source_file: str = ""
    normalized_product: str
    effective_unit_price: Decimal
    confidence: str = "medium"
    commercial_terms: list[CommercialTerm] = Field(default_factory=list)
    commercial_value: Decimal = Field(default=Decimal("0"))


class PurchaseNeed(BaseModel):
    product: str
    quantity: Decimal = Field(default=Decimal("1"))
    normalized_product: str


class ProcurementRecommendation(BaseModel):
    product: str
    recommended_supplier: str
    price: Decimal
    requested_quantity: Decimal = Field(default=Decimal("1"))
    estimated_total_cost: Decimal = Field(default=Decimal("0"))
    baseline_total_cost: Decimal = Field(default=Decimal("0"))
    reason: str
    estimated_savings: Decimal
    alternatives: list[CatalogItem]


class ProcurementAnalysisResponse(BaseModel):
    total_items: int
    products_compared: int
    estimated_savings_week: Decimal
    recommendations: list[ProcurementRecommendation]
    warnings: list[str]


@dataclass
class RawCatalog:
    filename: str
    text: str


HEADER_ALIASES = {
    "supplier": {"supplier", "fornecedor", "vendor"},
    "product": {"product", "produto", "artigo", "item", "designacao", "designação", "nome"},
    "description": {"description", "descricao", "descrição", "desc"},
    "quantity": {"quantity", "quantidade", "qtd", "qty", "embalagem"},
    "unit": {"unit", "unidade", "un", "medida"},
    "unit_price": {"unit_price", "preco_unitario", "preço_unitário", "preco", "preço", "pre_o", "price", "p_unit"},
    "total_price": {"total_price", "preco_total", "preço_total", "total"},
    "promotions": {"promotions", "promocoes", "promoções", "promo_es", "promo", "oferta", "bonus", "bónus"},
    "notes": {"notes", "notas", "observacoes", "observações", "condicoes", "condições"},
}

PROMO_VALUE_HINTS = (
    ("gratis", Decimal("0.03")),
    ("grátis", Decimal("0.03")),
    ("oferta", Decimal("0.03")),
    ("bonus", Decimal("0.02")),
    ("bónus", Decimal("0.02")),
    ("copos", Decimal("0.02")),
    ("glasses", Decimal("0.02")),
    ("desconto", Decimal("0.02")),
    ("leve", Decimal("0.03")),
    ("pague", Decimal("0.03")),
)


DEFAULT_COMMERCIAL_VALUES = {
    "copo": Decimal("0.80"),
    "copos": Decimal("0.80"),
    "glass": Decimal("0.80"),
    "glasses": Decimal("0.80"),
    "taca": Decimal("1.20"),
    "tacas": Decimal("1.20"),
    "jarro": Decimal("3.00"),
    "jarros": Decimal("3.00"),
    "guarda sol": Decimal("25.00"),
    "guardasol": Decimal("25.00"),
}

CommercialValueMap = dict[str, Decimal]


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )


def _key(value: str) -> str:
    cleaned = _strip_accents(value or "").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return cleaned


def normalize_product_name(value: str) -> str:
    text = _strip_accents(value or "").lower()
    text = re.sub(r"\b(pack|cx|caixa|garrafa|lata|unid|un|ud|pet)\b", " ", text)
    text = re.sub(r"\b\d+\s*x\s*\d+([,.]\d+)?\s*(ml|cl|l|lt|kg|g)\b", " ", text)
    text = re.sub(r"\b\d+([,.]\d+)?\s*(ml|cl|l|lt|kg|g)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_purchase_needs(text: str = "") -> list[PurchaseNeed]:
    needs: list[PurchaseNeed] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in re.split(r"[;,\t|]", line) if part.strip()]
        quantity = Decimal("1")
        product = line
        if len(parts) >= 2:
            first = _decimal(parts[0])
            last = _decimal(parts[-1])
            if first is not None:
                quantity = first
                product = " ".join(parts[1:])
            elif last is not None:
                quantity = last
                product = " ".join(parts[:-1])
        else:
            match = re.match(r"^(\d+(?:[,.]\d+)?)\s+(.+)$", line)
            if match:
                quantity = _decimal(match.group(1), Decimal("1")) or Decimal("1")
                product = match.group(2).strip()
        normalized = normalize_product_name(product)
        if normalized:
            needs.append(
                PurchaseNeed(
                    product=product,
                    quantity=quantity if quantity > 0 else Decimal("1"),
                    normalized_product=normalized,
                )
            )
    return needs


def _decimal(value: object, default: Decimal | None = None) -> Decimal | None:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = text.replace("€", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample[:2048], delimiters=";,|\t,").delimiter
    except csv.Error:
        return ";"


def _map_headers(headers: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for header in headers:
        header_key = _key(header)
        for field, aliases in HEADER_ALIASES.items():
            if header_key in {_key(alias) for alias in aliases}:
                mapped[field] = header
                break
    return mapped


def _supplier_from_filename(filename: str) -> str:
    stem = Path(filename or "Fornecedor").stem
    cleaned = re.sub(r"[_\-]+", " ", stem).strip()
    return cleaned.title() or "Fornecedor"


def _normalized_offer_text(promotions: str, notes: str) -> str:
    return _strip_accents(f"{promotions} {notes}").lower().strip()


def parse_commercial_values(text: str = "") -> CommercialValueMap:
    values = dict(DEFAULT_COMMERCIAL_VALUES)
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, raw_value = line.split("=", 1)
        elif ";" in line:
            key, raw_value = line.split(";", 1)
        elif "," in line:
            key, raw_value = line.split(",", 1)
        else:
            continue
        normalized_key = _normalized_offer_text(key, "")
        value = _decimal(raw_value)
        if normalized_key and value is not None and value >= 0:
            values[normalized_key] = value
    return values


def _commercial_value_for_unit(unit: str, commercial_values: CommercialValueMap) -> Decimal | None:
    normalized = _normalized_offer_text(unit, "")
    return commercial_values.get(normalized)


def extract_commercial_terms(
    promotions: str,
    notes: str,
    unit_price: Decimal,
    commercial_values: CommercialValueMap | None = None,
) -> list[CommercialTerm]:
    values = commercial_values or DEFAULT_COMMERCIAL_VALUES
    raw = f"{promotions} {notes}".strip()
    text = _normalized_offer_text(promotions, notes)
    if not text:
        return []

    terms: list[CommercialTerm] = []

    for match in re.finditer(r"(\d+(?:[,.]\d+)?)\s*(copos?|glasses?|tacas?|jarros?)\b", text):
        qty = _decimal(match.group(1), Decimal("1")) or Decimal("1")
        unit = match.group(2)
        unit_value = _commercial_value_for_unit(unit, values) or Decimal("0")
        terms.append(
            CommercialTerm(
                type="gift",
                label=f"{qty:g} {unit}",
                quantity=qty,
                unit=unit,
                estimated_unit_value=_money(unit_value),
                estimated_total_value=_money(qty * unit_value),
                confidence="medium",
                raw_text=raw,
            )
        )

    for match in re.finditer(r"(\d+(?:[,.]\d+)?)\s*(?:caixas?|packs?|unidades?)\s*(?:gratis|gratuitas|oferta)", text):
        qty = _decimal(match.group(1), Decimal("1")) or Decimal("1")
        terms.append(
            CommercialTerm(
                type="free_product",
                label=f"{qty:g} unidade(s) gratis",
                quantity=qty,
                unit="un",
                estimated_unit_value=_money(unit_price),
                estimated_total_value=_money(qty * unit_price),
                confidence="high",
                raw_text=raw,
            )
        )

    for match in re.finditer(r"(\d+)\s*\+\s*(\d+)", text):
        paid = Decimal(match.group(1))
        free = Decimal(match.group(2))
        if paid > 0 and free > 0:
            value = unit_price * (free / (paid + free))
            terms.append(
                CommercialTerm(
                    type="bundle",
                    label=f"{int(paid)}+{int(free)}",
                    quantity=free,
                    unit="bundle",
                    estimated_unit_value=_money(unit_price),
                    estimated_total_value=_money(value),
                    confidence="medium",
                    raw_text=raw,
                )
            )

    for match in re.finditer(r"(\d+(?:[,.]\d+)?)\s*%\s*(?:desconto|desc)", text):
        pct = (_decimal(match.group(1), Decimal("0")) or Decimal("0")) / Decimal("100")
        if pct > 0:
            terms.append(
                CommercialTerm(
                    type="discount_pct",
                    label=f"{pct * 100:g}% desconto",
                    quantity=Decimal("1"),
                    unit="percent",
                    estimated_unit_value=_money(unit_price * pct),
                    estimated_total_value=_money(unit_price * pct),
                    confidence="high",
                    raw_text=raw,
                )
            )

    for match in re.finditer(r"(?:desconto|vale|cupao|cupom)\s*(?:de)?\s*(\d+(?:[,.]\d+)?)\s*(?:eur|euro|euros)", text):
        value = _decimal(match.group(1), Decimal("0")) or Decimal("0")
        if value > 0:
            terms.append(
                CommercialTerm(
                    type="discount_value",
                    label=f"{value:g} euros desconto",
                    quantity=Decimal("1"),
                    unit="eur",
                    estimated_unit_value=_money(value),
                    estimated_total_value=_money(value),
                    confidence="high",
                    raw_text=raw,
                )
            )

    return terms


def _promo_adjustment(promotions: str, notes: str) -> Decimal:
    text = f"{promotions} {notes}".lower()
    adjustment = Decimal("0")
    for marker, value in PROMO_VALUE_HINTS:
        if marker in text:
            adjustment += value
    return min(adjustment, Decimal("0.10"))


def _make_item(
    row: dict[str, str],
    mapped: dict[str, str],
    filename: str,
    commercial_values: CommercialValueMap | None = None,
) -> CatalogItem | None:
    def val(field: str) -> str:
        header = mapped.get(field)
        return (row.get(header, "") if header else "").strip()

    product = val("product")
    price = _decimal(val("unit_price"))
    total = _decimal(val("total_price"))
    quantity = _decimal(val("quantity"), Decimal("1")) or Decimal("1")
    if not product or (price is None and total is None):
        return None

    if price is None and total is not None and quantity:
        price = total / quantity
    if total is None and price is not None:
        total = price * quantity

    supplier = val("supplier") or _supplier_from_filename(filename)
    promotions = val("promotions")
    notes = val("notes")
    unit_price = price or Decimal("0")
    commercial_terms = extract_commercial_terms(promotions, notes, unit_price, commercial_values)
    commercial_value = sum((term.estimated_total_value for term in commercial_terms), Decimal("0"))
    effective = max(Decimal("0"), unit_price - commercial_value)
    description = val("description")
    unit = val("unit") or "un"
    normalized = normalize_product_name(f"{product} {description}") or normalize_product_name(product)
    confidence = "high" if mapped.get("supplier") and mapped.get("product") and mapped.get("unit_price") else "medium"

    return CatalogItem(
        supplier=supplier,
        product=product,
        description=description,
        quantity=quantity,
        unit=unit,
        unit_price=_money(unit_price),
        total_price=_money(total or unit_price),
        promotions=promotions,
        notes=notes,
        source_file=filename,
        normalized_product=normalized,
        effective_unit_price=_money(effective),
        confidence=confidence,
        commercial_terms=commercial_terms,
        commercial_value=_money(commercial_value),
    )


def _make_loose_item(
    line: str,
    filename: str,
    commercial_values: CommercialValueMap | None = None,
) -> CatalogItem | None:
    cleaned = re.sub(r"\s+", " ", line).strip()
    if len(cleaned) < 5:
        return None
    price_matches = list(
        re.finditer(r"(?<!\d)(\d{1,4}(?:[.,]\d{2,4}))\s*(?:€|eur|euro|euros)?(?!\d)", cleaned, flags=re.I)
    )
    if not price_matches:
        return None
    match = price_matches[-1]
    price = _decimal(match.group(1))
    if price is None:
        return None
    product = cleaned[: match.start()].strip(" -:;|")
    trailing = cleaned[match.end() :].strip(" -:;|")
    if not product or len(product) < 3:
        return None
    commercial_terms = extract_commercial_terms(trailing, "", price, commercial_values)
    commercial_value = sum((term.estimated_total_value for term in commercial_terms), Decimal("0"))
    effective = max(Decimal("0"), price - commercial_value)
    normalized = normalize_product_name(product)
    if not normalized:
        return None
    return CatalogItem(
        supplier=_supplier_from_filename(filename),
        product=product,
        unit_price=_money(price),
        total_price=_money(price),
        promotions=trailing,
        source_file=filename,
        normalized_product=normalized,
        effective_unit_price=_money(effective),
        confidence="low",
        commercial_terms=commercial_terms,
        commercial_value=_money(commercial_value),
    )


def parse_catalog_text(
    filename: str,
    text: str,
    commercial_values: CommercialValueMap | None = None,
) -> tuple[list[CatalogItem], list[str]]:
    warnings: list[str] = []
    if not text.strip():
        return [], [f"{filename}: ficheiro vazio."]

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        loose_items = [_make_loose_item(line, filename, commercial_values) for line in text.splitlines()]
        items = [item for item in loose_items if item]
        if items:
            return items, [f"{filename}: lido em modo texto sem cabeçalhos; reveja correspondências."]
        return [], [f"{filename}: não encontrei cabeçalhos de tabela."]
    mapped = _map_headers(reader.fieldnames)
    required = {"product", "unit_price"}
    if not required.issubset(mapped):
        warnings.append(
            f"{filename}: use cabeçalhos como produto/fornecedor/preço/promoções para melhor leitura."
        )

    items: list[CatalogItem] = []
    for row in reader:
        item = _make_item(row, mapped, filename, commercial_values)
        if item:
            items.append(item)
            has_offer_text = bool((item.promotions or item.notes).strip())
            if has_offer_text and not item.commercial_terms:
                warnings.append(
                    f"{filename}: '{item.product}' tem oferta/nota sem valor automático. Reveja manualmente."
                )
    if not items:
        loose_items = [_make_loose_item(line, filename, commercial_values) for line in text.splitlines()]
        items = [item for item in loose_items if item]
        if items:
            warnings.append(f"{filename}: lido em modo texto sem cabeçalhos; reveja correspondências.")
        else:
            warnings.append(f"{filename}: não consegui extrair linhas com produto e preço.")
    return items, warnings


def _matches_need(product_key: str, need_key: str) -> bool:
    return product_key == need_key or product_key in need_key or need_key in product_key


def _need_for_group(product_key: str, needs: list[PurchaseNeed]) -> PurchaseNeed | None:
    for need in needs:
        if _matches_need(product_key, need.normalized_product):
            return need
    return None


def compare_catalogs(
    catalogs: Iterable[RawCatalog],
    purchase_needs: Iterable[PurchaseNeed] | None = None,
    commercial_values: CommercialValueMap | None = None,
) -> ProcurementAnalysisResponse:
    all_items: list[CatalogItem] = []
    warnings: list[str] = []
    for catalog in catalogs:
        items, item_warnings = parse_catalog_text(catalog.filename, catalog.text, commercial_values)
        all_items.extend(items)
        warnings.extend(item_warnings)

    grouped: dict[str, list[CatalogItem]] = defaultdict(list)
    for item in all_items:
        if item.normalized_product:
            grouped[item.normalized_product].append(item)

    recommendations: list[ProcurementRecommendation] = []
    savings_total = Decimal("0")
    needs = list(purchase_needs or [])
    matched_needs: set[str] = set()

    for normalized, items in grouped.items():
        need = _need_for_group(normalized, needs) if needs else None
        if needs and not need:
            continue
        requested_quantity = need.quantity if need else Decimal("1")
        if need:
            matched_needs.add(need.normalized_product)
        suppliers = {item.supplier for item in items}
        if len(items) < 2 or len(suppliers) < 2:
            continue
        ordered = sorted(items, key=lambda item: (item.effective_unit_price, item.unit_price))
        best = ordered[0]
        baseline = ordered[1]
        unit_savings = max(Decimal("0"), baseline.effective_unit_price - best.effective_unit_price)
        savings = unit_savings * requested_quantity
        estimated_total_cost = best.effective_unit_price * requested_quantity
        baseline_total_cost = baseline.effective_unit_price * requested_quantity
        savings_total += savings
        promo_note = ""
        if best.commercial_terms:
            term_labels = ", ".join(term.label for term in best.commercial_terms)
            promo_note = (
                f" Valor comercial estimado: {best.commercial_value}€"
                f" ({term_labels})."
            )
        elif best.promotions or best.notes:
            promo_note = f" Condição comercial ainda sem valorização automática: {(best.promotions or best.notes).strip()}."
        reason = (
            f"Melhor custo efetivo por {best.unit}: {best.effective_unit_price}€"
            f" vs {baseline.effective_unit_price}€ em {baseline.supplier}.{promo_note}"
        )
        display_name = max((item.product for item in items), key=len)
        recommendations.append(
            ProcurementRecommendation(
                product=display_name,
                recommended_supplier=best.supplier,
                price=best.unit_price,
                requested_quantity=requested_quantity,
                estimated_total_cost=_money(estimated_total_cost),
                baseline_total_cost=_money(baseline_total_cost),
                reason=reason,
                estimated_savings=_money(savings),
                alternatives=ordered,
            )
        )

    for need in needs:
        if need.normalized_product not in matched_needs:
            warnings.append(f"Lista de compra: '{need.product}' não teve comparação suficiente nos catálogos.")

    recommendations.sort(key=lambda rec: rec.estimated_savings, reverse=True)
    return ProcurementAnalysisResponse(
        total_items=len(all_items),
        products_compared=len(recommendations),
        estimated_savings_week=_money(savings_total),
        recommendations=recommendations,
        warnings=warnings,
    )
