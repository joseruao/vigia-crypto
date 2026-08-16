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


def reconcile_payments(db: AuditDB, run_id: int) -> list[dict[str, Any]]:
    """Faturas vs pagamentos: pagamento sem fatura / fatura sem pagamento."""
    findings: list[dict[str, Any]] = []
    invoices = [dict(r) for r in db.all_invoices()]
    payments = [dict(r) for r in db.all_payments()]
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
            findings.append(
                {
                    "tipo": "fatura_sem_pagamento",
                    "titulo": f"Fatura {inv.get('invoice_number') or '?'} sem pagamento detetado",
                    "descricao": (
                        f"Fatura de {inv.get('supplier') or '?'} no valor de {float(inv['total']):.2f}€ "
                        f"({inv.get('date') or 'data desconhecida'}) não tem pagamento correspondente nos extratos."
                    ),
                    "impacto_eur": float(inv["total"]),
                    "confianca": "baixa",
                    "evidencia": "Sem pagamento com montante igual nos extratos fornecidos",
                    "documentos": f"doc#{inv.get('document_id')}",
                }
            )

    for f in findings:
        db.insert_finding(run_id, f)
    return findings
