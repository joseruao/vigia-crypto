# backend/Api/routes/alerts.py
from __future__ import annotations
import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter, Retry

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/alerts", tags=["alerts"])

# =========================
# ENV / Const
# =========================
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "").strip()
HELIUS_BASE = "https://api.helius.xyz"

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE") or ""
SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

# =========================
# HTTP Session (requests) com retries
# =========================
def build_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=16)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "VigiaCrypto/alerts"})
    return s

HTTP = build_session()

# =========================
# Pydantic Models
# =========================
class AskIn(BaseModel):
    wallets: List[str] = Field(..., description="Wallets Solana (base58)")
    limit: int = Field(10, ge=1, le=100)
    min_usd: float = Field(0, ge=0)

class TxLite(BaseModel):
    signature: str
    slot: Optional[int] = None
    timestamp: Optional[int] = None
    wallet: str
    source: Optional[str] = None           # "JUPITER", "PHANTOM", etc.
    direction: Optional[str] = None        # "buy"|"sell"|"swap"|"in"|"out"|"transfer"
    usd_value: Optional[float] = None
    tokens_in: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_out: List[Dict[str, Any]] = Field(default_factory=list)
    explorer: Optional[str] = None

class AlertOut(BaseModel):
    wallet: str
    txs: List[TxLite]
    score: int
    explanation: str

class AskOut(BaseModel):
    alerts: List[AlertOut]
    meta: Dict[str, Any]

# =========================
# Helius helpers
# =========================
def _fetch_wallet_txs_helius(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Helius enhanced txs: /v0/addresses/:address/transactions"""
    if not HELIUS_API_KEY:
        return []
    url = f"{HELIUS_BASE}/v0/addresses/{address}/transactions"
    params = {"api-key": HELIUS_API_KEY, "limit": str(limit)}
    r = HTTP.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []

def _simplify_tx(address: str, tx: Dict[str, Any]) -> TxLite:
    sig = tx.get("signature", "")
    slot = tx.get("slot")
    ts = tx.get("timestamp")
    source = tx.get("source")
    direction = None
    usd = None
    tokens_in: List[Dict[str, Any]] = []
    tokens_out: List[Dict[str, Any]] = []

    events = tx.get("events") or {}

    swap = events.get("swap")
    if swap:
        # heurística simples para direção com base em estáveis
        def is_stable(t):
            sym = (t.get("symbol") or "").lower()
            mint = (t.get("mint") or "").lower()
            return "usdc" in sym or "usdt" in sym or "usd" in sym or "usdc" in mint or "usdt" in mint

        tokens_in = swap.get("tokenInputs", []) or []
        tokens_out = swap.get("tokenOutputs", []) or []
        stables_in = sum(float(t.get("tokenAmount", 0) or 0) for t in tokens_in if is_stable(t))
        stables_out = sum(float(t.get("tokenAmount", 0) or 0) for t in tokens_out if is_stable(t))
        if stables_in > stables_out:
            direction = "buy"
        elif stables_out > stables_in:
            direction = "sell"
        else:
            direction = "swap"

        # usd_value nem sempre disponível em enhanced – deixamos None
        source = swap.get("programInfo", {}).get("source") or source
    else:
        transfers = events.get("tokenTransfers") or []
        tokens_in = [t for t in transfers if t.get("toUserAccount") == address]
        tokens_out = [t for t in transfers if t.get("fromUserAccount") == address]
        direction = "in" if tokens_in and not tokens_out else ("out" if tokens_out and not tokens_in else "transfer")

    explorer = f"https://solscan.io/tx/{sig}" if sig else None

    return TxLite(
        signature=sig,
        slot=slot,
        timestamp=ts,
        wallet=address,
        source=source,
        direction=direction,
        usd_value=usd,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        explorer=explorer,
    )

def _mock_txs(address: str, limit: int) -> List[TxLite]:
    now = int(time.time())
    out: List[TxLite] = []
    for i in range(limit):
        out.append(TxLite(
            signature=f"FAKE_SIG_{i}_{address[:6]}",
            slot=123456 + i,
            timestamp=now - i * 120,
            wallet=address,
            source="MOCK",
            direction=("buy" if i % 2 == 0 else "sell"),
            usd_value=100 + 5 * i,
            tokens_in=[{"symbol": "SOL", "tokenAmount": 0.5}],
            tokens_out=[{"symbol": "USDC", "tokenAmount": 50}],
            explorer=None,
        ))
    return out

# =========================
# Scoring
# =========================
def _score_wallet_txs(txs: List[TxLite]) -> int:
    if not txs:
        return 0
    swaps = sum(1 for t in txs if t.direction in {"buy", "sell", "swap"})
    ts_sorted = sorted([t.timestamp for t in txs if t.timestamp] or [])
    pace = 0
    if len(ts_sorted) >= 2:
        span = max(ts_sorted) - min(ts_sorted)
        pace = 60000 / max(1, span)  # arbitrário
    usd = sum(t.usd_value or 0 for t in txs)
    score = 0
    score += min(50, swaps * 5)
    score += min(30, int(pace))
    score += min(20, int(usd / 500))
    return max(0, min(100, score))

def _explain(wallet: str, score: int, txs: List[TxLite]) -> str:
    c_swaps = sum(1 for t in txs if t.direction in {"buy", "sell", "swap"})
    latest = max((t.timestamp or 0 for t in txs), default=0)
    mins = int((time.time() - latest) / 60) if latest else None
    parts = [f"Atividade em {wallet[:4]}…{wallet[-4:]}: {c_swaps} swaps."]
    if mins is not None:
        parts.append(f"Última há ~{mins} min.")
    parts.append("Ritmo elevado." if score >= 70 else ("Ritmo moderado." if score >= 40 else "Baixa intensidade."))
    return " ".join(parts)

# =========================
# Routes
# =========================
@router.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@router.post("/ask", response_model=AskOut)
def ask(payload: AskIn):
    if not payload.wallets:
        raise HTTPException(status_code=400, detail="Fornece pelo menos uma wallet.")
    alerts: List[AlertOut] = []
    used_mock = False
    for w in payload.wallets:
        try:
            raw = _fetch_wallet_txs_helius(w, payload.limit)
            txs = [_simplify_tx(w, tx) for tx in raw] if raw else _mock_txs(w, payload.limit)
            if not raw:
                used_mock = True
        except Exception:
            used_mock = True
            txs = _mock_txs(w, payload.limit)
        if payload.min_usd > 0:
            txs = [t for t in txs if (t.usd_value or 0) >= payload.min_usd]
        score = _score_wallet_txs(txs)
        alerts.append(AlertOut(
            wallet=w,
            txs=txs,
            score=score,
            explanation=_explain(w, score, txs),
        ))
    meta = {
        "wallets": payload.wallets,
        "limit": payload.limit,
        "min_usd": payload.min_usd,
        "helius": bool(HELIUS_API_KEY),
        "mock_data": used_mock,
    }
    return AskOut(alerts=alerts, meta=meta)

# =========================
# Supabase: holdings & predictions
# =========================
def _sb_get(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return []
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = HTTP.get(url, headers=SUPABASE_HEADERS, params=params, timeout=15)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []

@router.get("/holdings")
def get_holdings(limit: int = Query(50, ge=1, le=200)):
    """
    Lê holdings relevantes de transacted_tokens (sem 'type'),
    ordenados por ts desc. Filtra value_usd>0.
    """
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return []
    params = {
        "select": "id,token,exchange,value_usd,liquidity,volume_24h,score,price,price_change_24h,pair_url,token_address,analysis_text,ts,chain",
        "order": "ts.desc",
        "limit": str(limit),
        "value_usd": "gt.0",
    }
    rows = _sb_get("transacted_tokens", params)
    out = []
    for r in rows:
        out.append({
            "id": r.get("id"),
            "token": r.get("token"),
            "exchange": r.get("exchange"),
            "value_usd": float(r.get("value_usd") or 0),
            "liquidity": float(r.get("liquidity") or 0),
            "volume_24h": float(r.get("volume_24h") or 0),
            "score": float(r.get("score") or 0),
            "pair_url": r.get("pair_url"),
            "token_address": r.get("token_address"),
            "analysis": r.get("analysis_text"),
            "chain": r.get("chain"),
            "price": float(r.get("price") or 0),
            "price_change_24h": float(r.get("price_change_24h") or 0),
            "ts": r.get("ts"),
        })
    return out

@router.get("/predictions")
def get_predictions(limit: int = Query(50, ge=1, le=200), min_score: float = Query(50, ge=0, le=100)):
    """
    Lê potenciais listings (usa score/listing_probability/confidence),
    ordena por ts desc, sem depender de campo 'type'.
    """
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return []
    # Filtrar por score >= min_score
    # PostgREST: score=gte.X
    params = {
        "select": "id,token,exchange,value_usd,liquidity,volume_24h,score,listing_probability,confidence,pair_url,token_address,ai_analysis,ts,chain",
        "order": "ts.desc",
        "limit": str(limit),
        "score": f"gte.{min_score}",
    }
    rows = _sb_get("transacted_tokens", params)
    out = []
    for r in rows:
        out.append({
            "id": r.get("id"),
            "token": r.get("token"),
            "exchange": r.get("exchange"),
            "value_usd": float(r.get("value_usd") or 0),
            "liquidity": float(r.get("liquidity") or 0),
            "volume_24h": float(r.get("volume_24h") or 0),
            "score": float(r.get("score") or 0),
            "listing_probability": float(r.get("listing_probability") or 0),
            "confidence": float(r.get("confidence") or 0),
            "pair_url": r.get("pair_url"),
            "token_address": r.get("token_address"),
            "analysis": r.get("ai_analysis"),
            "chain": r.get("chain"),
            "ts": r.get("ts"),
        })
    return out
