"""
Cron job: atualiza o ranking tecnico diario do top100.
Configurado no Render como: python worker/vigia_solana_pro_supabase.py
Schedule: render.yaml (0 8 * * *)
v2: Wilder RSI, MACD, Bollinger Bands, SMA200, pivot support/resistance
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Permite importar dailyworker/ a partir de backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
for _env in (
    Path(__file__).resolve().parents[1] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
):
    if _env.exists():
        load_dotenv(_env, override=False)
        break

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


def supabase_upsert(table: str, row: dict, conflict_cols: list) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {"on_conflict": ",".join(conflict_cols)}
    r = requests.post(url, json=row, params=params, headers=SUPABASE_HEADERS, timeout=15)
    return r.status_code in (200, 201)


def supabase_upsert_many(table: str, rows: list, conflict_cols: list) -> int:
    if not rows:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {"on_conflict": ",".join(conflict_cols)}
    r = requests.post(url, json=rows, params=params, headers=SUPABASE_HEADERS, timeout=30)
    if r.status_code in (200, 201):
        return len(rows)
    print(f"Supabase bulk upsert falhou: HTTP {r.status_code} — {r.text[:300]}", flush=True)
    return 0


def supabase_count_rows(table: str) -> int | None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {**SUPABASE_HEADERS, "Prefer": "count=exact"}
    r = requests.get(url, params={"select": "id", "limit": "1"}, headers=headers, timeout=10)
    raw = r.headers.get("content-range", "")
    try:
        return int(raw.split("/")[-1])
    except Exception:
        return None


async def main():
    from dailyworker.top100_rankings_worker import update_top100_rankings

    print("🔎 TOP100 TECHNICAL RANKINGS — CRON INICIADO", flush=True)
    start = time.time()

    saved = await update_top100_rankings(supabase_upsert, supabase_upsert_many)

    visible = supabase_count_rows("top100_technical_rankings")
    elapsed = round(time.time() - start, 1)

    print(f"✅ {saved} moedas guardadas em top100_technical_rankings", flush=True)
    if visible is not None:
        print(f"   Confirmacao Supabase: {visible} linhas visiveis em top100_technical_rankings", flush=True)
    print(f"   Duracao: {elapsed}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
