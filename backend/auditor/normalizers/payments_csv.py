from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

# Deteta colunas por nome (aceita variantes PT/EN). Delimitador auto (; , \t).
_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "date": ("data", "date", "dat", "fecha", "vencimento"),
    "amount": ("montante", "amount", "valor", "value", "importe", "quantia", "ammount"),
    "description": ("descricao", "description", "desc", "detalhe", "conceito", "narrative", "texto", "concepto"),
    "reference": ("referencia", "reference", "ref", "ndoc", "doc", "numero", "número"),
    "supplier": ("fornecedor", "supplier", "beneficiario", "beneficiary", "payee", "credor", "nome"),
}


def _pick_columns(header: list[str]) -> dict[str, int | None]:
    """Atribui cada coluna real a no máximo UM campo semântico (primeiro a casar)."""
    cols: dict[str, int | None] = {key: None for key in _COLUMN_CANDIDATES}
    taken: set[str] = set()
    for idx, raw in enumerate(header):
        name = re.sub(r"[^a-z0-9]", "", (raw or "").lower())
        if not name:
            continue
        for key, candidates in _COLUMN_CANDIDATES.items():
            if key in taken:
                continue
            for cand in candidates:
                cand_norm = re.sub(r"[^a-z0-9]", "", cand.lower())
                if name == cand_norm or name.startswith(cand_norm) or cand_norm.startswith(name):
                    cols[key] = idx
                    taken.add(key)
                    break
            if key in taken:
                break
    return cols


def _to_amount(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(" ", " ").strip()
    text = text.replace("€", "").replace("EUR", "").replace("USD", "").strip()
    negative = text.startswith("-") or text.startswith("(")
    digits = re.sub(r"[^\d,.\-()]", "", text)
    if not digits or digits in {"-", "()", "( )"}:
        return None
    if "," in digits and "." in digits:
        digits = digits.replace(".", "").replace(",", ".")
    elif "," in digits:
        digits = digits.replace(",", ".")
    try:
        value = float(digits)
    except ValueError:
        return None
    if negative:
        value = -abs(value)
    return value


def parse_payments_csv(path: Path) -> list[dict[str, Any]]:
    """Lê um CSV de extrato bancário e devolve pagamentos normalizados.

    Só considera linhas com valor negativo (saídas = pagamentos). Colunas
    detetadas automaticamente por nome do cabeçalho.
    """
    for delimiter in (";", ",", "\t"):
        try:
            with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                sample = fh.read(4000)
            has_header = any(
                re.search(rf"(?i)\b({k})\b", sample)
                for k in ("data", "date", "montante", "amount", "descricao", "description")
            )
            if not has_header:
                continue
            rows = list(csv.DictReader(open(path, encoding="utf-8-sig", errors="replace", newline=""), delimiter=delimiter))
            if not rows:
                continue
            cols = _pick_columns(list(rows[0].keys()))
            if cols["amount"] is None:
                continue
            payments: list[dict[str, Any]] = []
            for row in rows:
                amount = _to_amount(row.get(list(row.keys())[cols["amount"]]) if cols["amount"] is not None else None)
                if amount is None or amount >= 0:
                    continue  # só saídas (pagamentos)
                payments.append(
                    {
                        "date": row.get(list(row.keys())[cols["date"]]) if cols["date"] is not None else None,
                        "amount": abs(amount),
                        "description": (
                            row.get(list(row.keys())[cols["description"]]) if cols["description"] is not None else None
                        ),
                        "reference": row.get(list(row.keys())[cols["reference"]]) if cols["reference"] is not None else None,
                        "supplier": row.get(list(row.keys())[cols["supplier"]]) if cols["supplier"] is not None else None,
                    }
                )
            if payments:
                return payments
        except (csv.Error, UnicodeDecodeError, OSError):
            continue
    return []
