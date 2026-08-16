from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime
from typing import Any, Iterable

from ..storage.db import AuditDB


def _norm_number(value: Any) -> str:
    """Normaliza número de fatura: letras/dígitos apenas, maiúsculas."""
    if value is None:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _fmt_date(d: date | None) -> str:
    return d.isoformat() if d else ""


def _norm_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def find_duplicate_payments(db: AuditDB, run_id: int) -> list[dict[str, Any]]:
    """Pagamentos duplicados: mesmo montante + descrição/fornecedor igual + datas a ≤30 dias."""
    findings: list[dict[str, Any]] = []
    payments = [dict(r) for r in db.all_payments()]
    for i, pay_a in enumerate(payments):
        for pay_b in payments[i + 1 :]:
            amount_a, amount_b = pay_a.get("amount"), pay_b.get("amount")
            if amount_a is None or amount_b is None or abs(float(amount_a) - float(amount_b)) > 0.01:
                continue
            key_a = _norm_text(pay_a.get("supplier") or pay_a.get("description"))
            key_b = _norm_text(pay_b.get("supplier") or pay_b.get("description"))
            if not key_a or key_a != key_b:
                continue
            d_a, d_b = _parse_date(pay_a.get("date")), _parse_date(pay_b.get("date"))
            if not d_a or not d_b or abs((d_a - d_b).days) > 30:
                continue
            desc = pay_a.get("description") or pay_a.get("supplier") or "pagamento"
            findings.append(
                {
                    "tipo": "pagamento_duplicado",
                    "titulo": f"Pagamento duplicado: {float(amount_a):.2f}€",
                    "descricao": (
                        f"O mesmo montante ({float(amount_a):.2f}€) com a mesma referência "
                        f"('{desc}') aparece {_fmt_date(d_a)} e {_fmt_date(d_b)} "
                        f"(diferença de {abs((d_a - d_b).days)} dias). Risco de pagamento a dobrar."
                    ),
                    "impacto_eur": float(amount_a),
                    "confianca": "alta",
                    "evidencia": f"Montante {float(amount_a):.2f}€ repetido nos extratos",
                    "documentos": f"doc#{pay_a.get('document_id')} | doc#{pay_b.get('document_id')}",
                    "_payment_ids": [pay_a.get("id"), pay_b.get("id")],
                }
            )
    for f in findings:
        db.insert_finding(run_id, f)
    return findings


def find_missing_invoice_sequences(db: AuditDB, run_id: int) -> list[dict[str, Any]]:
    """Faturas em falta: buracos na sequência de números por fornecedor (ex.: 0113, 0115 → falta 0114)."""
    findings: list[dict[str, Any]] = []
    invoices = [dict(r) for r in db.all_invoices()]
    by_supplier_year: dict[tuple[str, str], list[int]] = {}
    for inv in invoices:
        raw_number = str(inv.get("invoice_number") or "")
        if len(_norm_number(raw_number)) < 6:
            continue
        supplier = _norm_text(inv.get("supplier"))
        if not supplier:
            continue
        # Segmento numérico final do número ORIGINAL (ex.: A2026-0114 -> 0114, ano 2026)
        digits = re.findall(r"\d+", raw_number)
        if not digits:
            continue
        seq_digits = digits[-1]
        year = ""
        if len(digits) >= 2:
            year = digits[-2][:4]
        key = (supplier, year)
        try:
            by_supplier_year.setdefault(key, []).append(int(seq_digits))
        except ValueError:
            continue

    for (supplier_key, year), seqs in by_supplier_year.items():
        unique = sorted(set(seqs))
        if len(unique) < 3:
            continue
        gaps = []
        for a, b in zip(unique, unique[1:]):
            if 0 < b - a <= 10:  # buracos pequenos são os sinalizadores (grandes = sequências distintas)
                for missing in range(a + 1, b):
                    gaps.append(missing)
        if not gaps:
            continue
        gap_text = ", ".join(f"{g:04d}" for g in gaps[:6])
        findings.append(
            {
                "tipo": "fatura_em_falta",
                "titulo": f"Possíveis faturas em falta no fornecedor ({year or '?'}): {gap_text}",
                "descricao": (
                    f"A sequência de faturas deste fornecedor tem buracos: {gap_text}. "
                    f"Faturas em falta podem significar compras não registadas ou documentos escondidos."
                ),
                "impacto_eur": None,
                "confianca": "baixa",
                "evidencia": f"Sequência detetada: {min(unique)}…{max(unique)} ({len(unique)} faturas)",
                "documentos": f"fornecedor #{supplier_key}",
            }
        )
    for f in findings:
        db.insert_finding(run_id, f)
    return findings


def find_duplicate_invoices(db: AuditDB, run_id: int) -> list[dict[str, Any]]:
    """Faturas iguais ou quase iguais pagas mais de uma vez."""
    findings: list[dict[str, Any]] = []
    invoices = [dict(r) for r in db.all_invoices()]
    seen_by_number: dict[str, list[dict[str, Any]]] = {}

    for inv in invoices:
        key = _norm_number(inv.get("invoice_number"))
        if key:
            seen_by_number.setdefault(key, []).append(inv)

    for number, group in seen_by_number.items():
        if len(group) < 2:
            continue
        docs = " | ".join(sorted({f"doc#{i['document_id']}" for i in group}))
        total = sum(i.get("total") or 0 for i in group[1:])
        findings.append(
            {
                "tipo": "fatura_duplicada",
                "titulo": f"Fatura {number} aparece {len(group)} vezes",
                "descricao": (
                    f"O mesmo número de fatura ({number}) foi registado {len(group)} vezes "
                    f"({', '.join(i.get('supplier') or '?' for i in group)}). "
                    f"Risco de pagamento duplicado."
                ),
                "impacto_eur": total,
                "confianca": "alta",
                "evidencia": f"Número de fatura repetido: {number}",
                "documentos": docs,
            }
        )

    # Quase-duplicados: mesmo fornecedor + mesmo total + datas a <30 dias
    for i, inv_a in enumerate(invoices):
        for inv_b in invoices[i + 1 :]:
            if inv_a.get("id") == inv_b.get("id"):
                continue
            if _norm_number(inv_a.get("invoice_number")) and _norm_number(
                inv_a.get("invoice_number")
            ) == _norm_number(inv_b.get("invoice_number")):
                continue  # já apanhado acima
            same_supplier = (inv_a.get("supplier") or "").strip().lower() == (
                inv_b.get("supplier") or ""
            ).strip().lower() and bool(inv_a.get("supplier"))
            if not same_supplier:
                continue
            t_a, t_b = inv_a.get("total"), inv_b.get("total")
            if t_a is None or t_b is None or abs(float(t_a) - float(t_b)) > 0.01:
                continue
            d_a, d_b = _parse_date(inv_a.get("date")), _parse_date(inv_b.get("date"))
            if not d_a or not d_b or abs((d_a - d_b).days) >= 30:
                continue
            findings.append(
                {
                    "tipo": "fatura_duplicada_provavel",
                    "titulo": f"Provável duplicado: {inv_a.get('supplier')} — {t_a:.2f}€",
                    "descricao": (
                        f"Duas faturas do mesmo fornecedor com o mesmo total "
                        f"({t_a:.2f}€) em {_fmt_date(d_a)} e {_fmt_date(d_b)} "
                        f"(diferença de {abs((d_a - d_b).days)} dias)."
                    ),
                    "impacto_eur": float(t_a),
                    "confianca": "media",
                    "evidencia": f"Total {t_a:.2f}€, fornecedor '{inv_a.get('supplier')}'",
                    "documentos": f"doc#{inv_a.get('document_id')} | doc#{inv_b.get('document_id')}",
                }
            )

    for f in findings:
        db.insert_finding(run_id, f)
    return findings


def reconcile_payments(
    db: AuditDB, run_id: int, skip_payment_ids: set[int] | None = None
) -> list[dict[str, Any]]:
    """Faturas vs pagamentos: pagamento sem fatura / fatura sem pagamento.

    skip_payment_ids: pagamentos já sinalizados como duplicados (não são
    re-sinalizados como "sem fatura" — o problema já está reportado).
    """
    skip = skip_payment_ids or set()
    findings: list[dict[str, Any]] = []
    invoices = [dict(r) for r in db.all_invoices()]
    payments = [dict(r) for r in db.all_payments() if r["id"] not in skip]
    if not payments:
        return findings

    def _supplier_key(v: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", (v or "").lower())

    paid_invoice_ids: set[int] = set()
    for pay in payments:
        amount = float(pay.get("amount") or 0)
        pay_supplier = _supplier_key(pay.get("supplier"))
        matched = None
        for inv in invoices:
            if inv["id"] in paid_invoice_ids:
                continue
            if inv.get("total") is None or abs(float(inv["total"]) - amount) > 0.01:
                continue
            inv_supplier = _supplier_key(inv.get("supplier"))
            if pay_supplier and inv_supplier and pay_supplier != inv_supplier:
                continue
            if pay_supplier or inv_supplier:
                matched = inv
                break
        if matched:
            paid_invoice_ids.add(matched["id"])
        else:
            findings.append(
                {
                    "tipo": "pagamento_sem_fatura",
                    "titulo": f"Pagamento {amount:.2f}€ sem fatura correspondente",
                    "descricao": (
                        f"Pagamento de {amount:.2f}€ em {pay.get('date') or 'data desconhecida'} "
                        f"{('(' + str(pay.get('description') or '') + ')') if pay.get('description') else ''} "
                        f"não bate certo com nenhuma fatura registada."
                    ),
                    "impacto_eur": amount,
                    "confianca": "media",
                    "evidencia": f"Montante {amount:.2f}€ sem correspondência nas faturas",
                    "documentos": f"doc#{pay.get('document_id')}",
                }
            )

    for inv in invoices:
        if inv["id"] not in paid_invoice_ids and inv.get("total") is not None:
            is_sale = inv.get("type") == "venda"
            findings.append(
                {
                    "tipo": "fatura_sem_pagamento",
                    "titulo": (
                        f"Fatura {inv.get('invoice_number') or '?'} sem {'recebimento' if is_sale else 'pagamento'} detetado"
                    ),
                    "descricao": (
                        f"{'Venda a' if is_sale else 'Fatura de'} {inv.get('supplier') or '?'} no valor de "
                        f"{float(inv['total']):.2f}€ ({inv.get('date') or 'data desconhecida'}) "
                        f"não tem {'recebimento' if is_sale else 'pagamento'} correspondente nos extratos."
                    ),
                    "impacto_eur": float(inv["total"]),
                    "confianca": "baixa",
                    "evidencia": f"Sem {'recebimento' if is_sale else 'pagamento'} com montante igual nos extratos fornecidos",
                    "documentos": f"doc#{inv.get('document_id')}",
                }
            )

    for f in findings:
        db.insert_finding(run_id, f)
    return findings
