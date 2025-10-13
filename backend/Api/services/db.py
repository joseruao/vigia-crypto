# backend/Api/services/db.py
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
from supabase import create_client, Client

def _req(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

SUPABASE_URL = _req("SUPABASE_URL")
SUPABASE_KEY = _req("SUPABASE_SERVICE_ROLE_KEY")
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

COLUMNS = (
    "exchange, token, token_address, signature, amount, value_usd, price, "
    "liquidity, volume_24h, pair_url, listed_exchanges, special, ts, "
    "score, listing_probability, confidence, txns_buys, txns_sells, holders_concentration, analysis_text"
)

def fetch_alerts(
    min_score: float = 50,
    hours: int = 24,
    exchange: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    order_by: str = "score",
    order_dir: str = "desc"
) -> Tuple[List[dict], int]:
    since_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    since_iso = since_dt.isoformat()

    q = sb.table("transacted_tokens").select(COLUMNS, count="exact").gte("score", min_score).gte("ts", since_iso)
    if exchange:
        q = q.eq("exchange", exchange)

    if order_by not in {"score","ts","liquidity","volume_24h"}:
        order_by = "score"
    desc = (order_dir.lower() != "asc")
    q = q.order(order_by, desc=desc, nullsfirst=False)
    q = q.range(offset, offset + limit - 1)

    res = q.execute()
    data = getattr(res, "data", []) or []
    total = getattr(res, "count", 0) or 0
    return data, int(total)
