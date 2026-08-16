from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from ..storage.db import AuditDB

CSS = """
:root { --bg:#0f1115; --card:#171a21; --border:#262b36; --text:#e6e9ef; --muted:#8b93a3;
        --accent:#4f8cff; --good:#3ecf8e; --warn:#ffb020; --bad:#ff5d5d; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; padding:32px 8vw; }
h1 { font-size:22px; margin-bottom:4px; }
h2 { font-size:15px; margin:28px 0 12px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }
.sub { color:var(--muted); font-size:13px; margin-bottom:20px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:8px; }
.card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:14px 16px; }
.card .n { font-size:26px; font-weight:600; }
.card .l { font-size:12px; color:var(--muted); }
table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); padding:10px 12px; border-bottom:1px solid var(--border); }
td { font-size:13px; padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:top; }
tr:last-child td { border-bottom:none; }
.badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; }
.b-alta { background:rgba(255,93,93,.15); color:var(--bad); }
.b-media { background:rgba(255,176,32,.15); color:var(--warn); }
.b-baixa { background:rgba(143,147,163,.15); color:var(--muted); }
.pos { color:var(--good); font-weight:600; }
.neg { color:var(--bad); font-weight:600; }
.summary { background:var(--card); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:8px; padding:14px 16px; font-size:14px; line-height:1.6; margin-bottom:8px; }
footer { margin-top:32px; color:var(--muted); font-size:12px; }
"""


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _money(value: object) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",") + " €"
    except (TypeError, ValueError):
        return "—"


def render_report(db: AuditDB, workspace_name: str, run_id: int | None = None) -> str:
    findings = [dict(r) for r in db.all_findings(run_id)]
    invoices = [dict(r) for r in db.all_invoices()]
    payments = [dict(r) for r in db.all_payments()]
    ai_rows = db.conn.execute("SELECT * FROM ai_calls ORDER BY id").fetchall()
    docs_count = db.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    total_impact = sum(f.get("impacto_eur") or 0 for f in findings)
    ai_tokens = db.total_ai_tokens()

    # --- resumo executivo (IA, só se houver achados) ---
    summary_html = ""
    from ..ai.providers import build_ai_client  # import tardio para não encarecer import

    if findings:
        client = build_ai_client()
        if client.__class__.__name__ != "NoAIClient":
            text = client.explain_findings(findings)
            if text:
                summary_html = f'<div class="summary">{_e(text)}</div>'

    # --- achados ---
    rows = ""
    for f in findings:
        conf_class = {"alta": "b-alta", "media": "b-media", "baixa": "b-baixa"}.get(
            str(f.get("confianca") or "").lower(), "b-media"
        )
        rows += (
            f"<tr><td><span class='badge {conf_class}'>{_e(f.get('confianca'))}</span></td>"
            f"<td>{_e(f.get('tipo'))}</td><td><strong>{_e(f.get('titulo'))}</strong><br>"
            f"<span style='color:var(--muted);font-size:12px'>{_e(f.get('descricao'))}</span></td>"
            f"<td class='neg'>{_money(f.get('impacto_eur'))}</td>"
            f"<td><span style='color:var(--muted);font-size:12px'>{_e(f.get('evidencia'))}<br>"
            f"{_e(f.get('documentos'))}</span></td></tr>"
        )
    findings_html = (
        "<table><tr><th>Confiança</th><th>Tipo</th><th>Achado</th><th>Impacto</th><th>Evidência</th></tr>"
        f"{rows}</table>"
        if rows
        else "<p style='color:var(--muted)'>Sem achados — nenhuma anomalia detetada.</p>"
    )

    # --- faturas ---
    inv_rows = ""
    for inv in invoices:
        inv_rows += (
            f"<tr><td>{_e(inv.get('invoice_number'))}</td><td>{_e(inv.get('supplier'))}</td>"
            f"<td>{_e(inv.get('supplier_nif'))}</td><td>{_e(inv.get('date'))}</td>"
            f"<td>{_money(inv.get('total'))}</td><td>{_e(inv.get('payment_reference'))}</td></tr>"
        )
    invoices_html = (
        "<table><tr><th>Nº</th><th>Fornecedor</th><th>NIF</th><th>Data</th><th>Total</th><th>Ref. pag.</th></tr>"
        f"{inv_rows}</table>"
        if inv_rows
        else "<p style='color:var(--muted)'>Nenhuma fatura extraída.</p>"
    )

    # --- pagamentos ---
    pay_rows = ""
    for pay in payments:
        pay_rows += (
            f"<tr><td>{_e(pay.get('date'))}</td><td>{_money(pay.get('amount'))}</td>"
            f"<td>{_e(pay.get('supplier'))}</td><td>{_e(pay.get('description'))}</td>"
            f"<td>{_e(pay.get('reference'))}</td></tr>"
        )
    payments_html = (
        "<table><tr><th>Data</th><th>Montante</th><th>Fornecedor</th><th>Descrição</th><th>Ref.</th></tr>"
        f"{pay_rows}</table>"
        if pay_rows
        else "<p style='color:var(--muted)'>Nenhum extrato de pagamentos fornecido.</p>"
    )

    # --- chamadas IA (transparência) ---
    ai_rows_html = ""
    for call in ai_rows:
        ai_rows_html += (
            f"<tr><td>{_e(call['model'])}</td><td>{_e(call['prompt_tokens'])}</td>"
            f"<td>{_e(call['completion_tokens'])}</td><td>{_e(call['reasoning_tokens'])}</td>"
            f"<td>{_e(call['total_tokens'])}</td></tr>"
        )
    ai_html = (
        "<table><tr><th>Modelo</th><th>Input</th><th>Output</th><th>Raciocínio</th><th>Total</th></tr>"
        f"{ai_rows_html}</table>"
        if ai_rows_html
        else "<p style='color:var(--muted)'>Sem chamadas a IA nesta base.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="pt"><head><meta charset="utf-8"><title>Relatório de Auditoria — {_e(workspace_name)}</title>
<style>{CSS}</style></head><body>
<h1>Relatório de Auditoria — {_e(workspace_name)}</h1>
<div class="sub">Gerado localmente · dados na região UE (Azure germanywestcentral) · {docs_count} documentos</div>
<div class="cards">
  <div class="card"><div class="n">{len(findings)}</div><div class="l">Achados</div></div>
  <div class="card"><div class="n neg">{_money(total_impact)}</div><div class="l">Impacto total estimado</div></div>
  <div class="card"><div class="n">{len(invoices)}</div><div class="l">Faturas estruturadas</div></div>
  <div class="card"><div class="n">{len(payments)}</div><div class="l">Pagamentos (extratos)</div></div>
  <div class="card"><div class="n">{ai_tokens:,}</div><div class="l">Tokens IA usados</div></div>
</div>
{summary_html}
<h2>Achados</h2>{findings_html}
<h2>Faturas extraídas</h2>{invoices_html}
<h2>Pagamentos (extratos bancários)</h2>{payments_html}
<h2>Chamadas à IA (transparência)</h2>{ai_html}
<footer>AI Business Auditor · {_e(workspace_name)} · gerado a {__import__("datetime").datetime.now().isoformat(timespec="seconds")}</footer>
</body></html>"""


def write_report(db: AuditDB, workspace: Path, run_id: int | None = None) -> Path:
    report_dir = workspace / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / "report.html"
    out.write_text(render_report(db, workspace.name, run_id), encoding="utf-8")
    return out
