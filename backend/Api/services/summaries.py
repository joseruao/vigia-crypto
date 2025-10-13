# backend/Api/services/summaries.py
# -*- coding: utf-8 -*-

from typing import List

def _fmt_money(v: float) -> str:
    try:
        return f"\"
    except Exception:
        return str(v)

def items_to_markdown(items: List[dict]) -> str:
    if not items:
        return "_Sem resultados para os filtros atuais._"
    lines: List[str] = []
    for it in items:
        if it.get("analysis_text"):
            lines.append(f"- {it['analysis_text']}")
            continue
        tok = it.get("token","?")
        ex = it.get("exchange","?")
        score = it.get("score",0.0)
        liq = _fmt_money(float(it.get("liquidity") or 0.0))
        vol = _fmt_money(float(it.get("volume_24h") or 0.0))
        pair_url = it.get("pair_url") or ""
        sig = it.get("signature") or ""
        solscan = f"https://solscan.io/tx/{sig}" if sig else ""
        links = []
        if pair_url: links.append(f"[DexScreener]({pair_url})")
        if solscan: links.append(f"[Solscan]({solscan})")
        links_str = " · ".join(links) if links else ""
        lines.append(f"- **{tok}** em **{ex}** — score **{score:.0f}/100** · Liq {liq} · Vol24h {vol} {('· ' + links_str) if links_str else ''}")
    return "\n".join(lines)
