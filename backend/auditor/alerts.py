"""Alertas de auditoria.

- Estado de cada achado (novo/confirmado/ignorado) — gerido na BD e na UI.
- Notificação opcional por Telegram quando um run termina com achados de
  confiança alta. DESLIGADA por defeito: só ativa com AUDITOR_TELEGRAM_ENABLED=1
  e token/chat id no .env (reutiliza TELEGRAM_BOT_TOKEN_SOL / TELEGRAM_CHAT_ID_SOL
  do projeto, ou AUDITOR_TELEGRAM_BOT_TOKEN / AUDITOR_TELEGRAM_CHAT_ID).
"""
from __future__ import annotations

import os
from typing import Any

import requests

from .storage.db import AuditDB


def set_finding_state(db: AuditDB, finding_id: int, state: str) -> bool:
    if state not in {"novo", "confirmado", "ignorado"}:
        return False
    cur = db.conn.execute(
        "UPDATE audit_findings SET estado = ? WHERE id = ?", (state, finding_id)
    )
    db.conn.commit()
    return cur.rowcount > 0


def notify_high_confidence(findings: list[dict[str, Any]]) -> str:
    """Envia alerta Telegram com achados de confiança alta (só se ativado)."""
    if os.getenv("AUDITOR_TELEGRAM_ENABLED", "0") != "1":
        return "Alertas Telegram desativados (AUDITOR_TELEGRAM_ENABLED=1 para ativar)."
    token = os.getenv("AUDITOR_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN_SOL")
    chat_id = os.getenv("AUDITOR_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID_SOL")
    if not token or not chat_id:
        return "Telegram ativado mas sem token/chat_id no .env."
    high = [f for f in findings if str(f.get("confianca") or "").lower() == "alta"]
    if not high:
        return "Sem achados de confiança alta para notificar."
    lines = [f"🧾 AUDITOR — {len(high)} alerta(s) de alta confiança:"]
    for f in high[:5]:
        impact = f.get("impacto_eur")
        lines.append(f"• {f['titulo']}" + (f" ({float(impact):.2f}€)" if impact else ""))
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines)},
            timeout=15,
        )
        if resp.ok:
            return f"Telegram: {len(high)} alerta(s) enviados."
        return f"Telegram falhou: {resp.text[:120]}"
    except requests.RequestException as exc:
        return f"Telegram indisponível: {str(exc)[:120]}"
