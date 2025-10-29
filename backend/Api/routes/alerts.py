# backend/Api/routes/alerts.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter, Retry
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

router = APIRouter(prefix="/alerts", tags=["alerts"])

# ========= ENV =========
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL em falta")
if not SUPABASE_SERVICE_ROLE:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_KEY) em falta")

# ========= HTTP SESSION =========
def build_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    ad = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=16)
    s.mount("https://", ad)
    s.mount("http://", ad)
    s.headers.update({"User-Agent": "VigiaCrypto/alerts"})
    return s

HTTP = build_session()

# ========= SUPABASE REST HELPERS =========
def sb_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
        "Content-Type": "application/json",
    }

def sb_get(path: str, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{path.lstrip('/')}"
    r = HTTP.get(url, headers=sb_headers(), params=params or {}, timeout=20)
    # Se PostgREST responder erro (ex.: coluna inexistente), devolvemos []
    if r.status_code >= 400:
        # log leve no servidor
        print(f"[alerts] Supabase GET {url} -> {r.status_code} {r.text[:200]}")
        return []
    try:
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []

# ========= MODELS (para /ask com Helius) =========
class AskIn(BaseModel):
    wallets: List[str] = Field(..., description="Wallets Solana (base58).")
    limit: int = Field(10, ge=1, le=100)
    min_usd: float = Field(0, ge=0)

class TxLite(BaseModel):
    signature: str
    slot: Optional[int] = None
    timestamp: Optional[int] = None
    wallet: str
    source: Optional[str] = None
    direction: Optional[str] = None   # buy/sell/swap/in/out/transfer
    usd_value: Optional[float] = None
    tokens_in: List[Dict[str, Any]] = []
    tokens_out: List[Dict[str, Any]] = []
    explorer: Optional[str] = None

class AlertOut(BaseModel):
    wallet: str
    txs: List[TxLite]
    score: int
    explanation: str

class AskOut(BaseModel):
    alerts: List[AlertOut]
    meta: Dict[str, Any]

# ========= HELIUS (requests) =========
_HELIUS_BASE = "https://api.helius.xyz"

def helius_get_txs(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Enhanced transactions: /v0/addresses/:address/transactions"""
    if not HELIUS_API_KEY:
        return []
    params = {"api-key": HELIUS_API_KEY, "limit": str(limit)}
    url = f"{_HELIUS_BASE}/v0/addresses/{address}/transactions"
    r = HTTP.get(url, params=params, timeout=25)
    if r.status_code != 200:
        print(f"[alerts] Helius {r.status_code} {r.text[:160]}")
        return []
    try:
        j = r.json()
        return j if isinstance(j, list) else []
    except Exception:
        return []

def simplify_tx(address: str, tx: Dict[str, Any]) -> TxLite:
    sig = tx.get("signature") or ""
    slot = tx.get("slot")
    ts   = tx.get("timestamp")
    source = tx.get("source")
    direction = None
    tokens_in: List[Dict[str, Any]] = []
    tokens_out: List[Dict[str, Any]] = []
    usd = None

    ev = tx.get("events") or {}
    swap = ev.get("swap")
    if swap:
        source = (swap.get("programInfo") or {}).get("source") or source
        def is_stable(t):
            sym = (t.get("symbol") or "").lower()
            mint = (t.get("mint") or "").lower()
            return ("usdc" in sym) or ("usdt" in sym) or ("usd" in sym) or ("usdc" in mint) or ("usdt" in mint)
        st_in = sum(float(t.get("tokenAmount", 0) or 0) for t in swap.get("tokenInputs", [])  if is_stable(t))
        st_out= sum(float(t.get("tokenAmount", 0) or 0) for t in swap.get("tokenOutputs", []) if is_stable(t))
        if st_in > st_out: direction = "buy"
        elif st_out > st_in: direction = "sell"
        else: direction = "swap"
        tokens_in = swap.get("tokenInputs", []) or []
        tokens_out = swap.get("tokenOutputs", []) or []
    else:
        transfers = ev.get("tokenTransfers") or []
        tokens_in = [t for t in transfers if t.get("toUserAccount") == address]
        tokens_out= [t for t in transfers if t.get("fromUserAccount") == address]
        direction = "in" if tokens_in and not tokens_out else ("out" if tokens_out and not tokens_in else "transfer")

    explorer = f"https://solscan.io/tx/{sig}" if sig else None
    return TxLite(
        signature=sig, slot=slot, timestamp=ts, wallet=address,
        source=source, direction=direction, usd_value=usd,
        tokens_in=tokens_in, tokens_out=tokens_out, explorer=explorer
    )

def score_txs(txs: List[TxLite]) -> int:
    if not txs:
        return 0
    swaps = sum(1 for t in txs if (t.direction in {"buy", "sell", "swap"}))
    timestamps = [t.timestamp for t in txs if t.timestamp]
    pace = 0
    if len(timestamps) >= 2:
        span = max(timestamps) - min(timestamps)
        pace = 60_000 / max(1, span)
    usd = sum(t.usd_value or 0 for t in txs)
    s = 0
    s += min(50, swaps * 5)
    s += min(30, int(pace))
    s += min(20, int(usd / 500))
    return max(0, min(100, int(s)))

def explain(address: str, score: int, txs: List[TxLite]) -> str:
    c_swaps = sum(1 for t in txs if t.direction in {"buy", "sell", "swap"})
    latest = max((t.timestamp or 0 for t in txs), default=0)
    mins = int((time.time() - latest) / 60) if latest else None
    parts = [f"Atividade em {address[:4]}…{address[-4:]}: {c_swaps} swaps."]
    if mins is not None:
        parts.append(f"Última tx há ~{mins} min.")
    if score >= 70: parts.append("Ritmo elevado.")
    elif score >= 40: parts.append("Ritmo moderado.")
    else: parts.append("Baixa intensidade.")
    return " ".join(parts)

# ========= API =========
@router.get("/health")
def alerts_health():
    return {"ok": True, "ts": int(time.time())}

@router.get("/holdings")
def get_holdings():
    """
    Lê holdings guardados em transacted_tokens.
    NÃO usa 'type' (a tua tabela não tem). Usamos apenas colunas existentes.
    """
    # campos que existem no teu schema:
    select_cols = ",".join([
        "id", "token", "exchange", "value_usd", "liquidity", "volume_24h",
        "score", "pair_url", "token_address", "analysis_text", "ts"
    ])
    params = {
        "select": select_cols,
        "order": "ts.desc",
        "limit": "100",
    }
    rows = sb_get("transacted_tokens", params)
    # opcional: filtrar serverside por mínimos > 0
    out = []
    for r in rows:
        try:
            vu = float(r.get("value_usd") or 0.0)
            liq = float(r.get("liquidity") or 0.0)
            if vu <= 0 or liq <= 0:
                continue
            out.append(r)
        except Exception:
            continue
    return out

@router.get("/predictions")
def get_predictions():
    """
    Predictions = entradas com campos de ML (listing_probability/confidence) OU transações (signature) relevantes.
    Não dependemos de coluna 'type'.
    """
    select_cols = ",".join([
        "id","token","exchange","value_usd","liquidity","volume_24h","score",
        "listing_probability","confidence","ai_analysis","pair_url","token_address","signature","ts"
    ])
    params = {
        "select": select_cols,
        "order": "ts.desc",
        "limit": "100",
    }
    rows = sb_get("transacted_tokens", params)
    out = []
    for r in rows:
        lp = r.get("listing_probability")
        sig = r.get("signature")
        try:
            # Se tem probabilidade OU é uma transação com score aceitável, mostramos
            if (lp is not None and float(lp) >= 1) or (sig and float(r.get("score") or 0) >= 50):
                out.append(r)
        except Exception:
            continue
    return out

@router.post("/ask", response_model=AskOut)
def ask(payload: AskIn = Body(...)):
    """
    Perguntas sobre atividade em wallets Solana (via Helius). Sem httpx.
    """
    if not payload.wallets:
        raise HTTPException(status_code=400, detail="Fornece pelo menos uma wallet.")
    alerts: List[AlertOut] = []
    used_mock = False

    for w in payload.wallets:
        raw = []
        try:
            raw = helius_get_txs(w, payload.limit)
        except Exception as e:
            print(f"[alerts] Helius exception: {e}")

        txs: List[TxLite] = []
        if raw:
            txs = [simplify_tx(w, tx) for tx in raw]
        else:
            # mock mínimo para não falhar quando não tens HELIUS_API_KEY
            used_mock = True
            now = int(time.time())
            for i in range(payload.limit):
                txs.append(TxLite(
                    signature=f"FAKE_{i}_{w[:6]}",
                    slot=123456+i,
                    timestamp=now - i*120,
                    wallet=w,
                    source="MOCK",
                    direction=("buy" if i%2==0 else "sell"),
                    usd_value=100 + 5*i,
                    tokens_in=[{"symbol":"SOL","tokenAmount":0.5}],
                    tokens_out=[{"symbol":"USDC","tokenAmount":50}],
                    explorer=None
                ))

        if payload.min_usd > 0:
            txs = [t for t in txs if (t.usd_value or 0) >= payload.min_usd]

        s = score_txs(txs)
        alerts.append(AlertOut(wallet=w, txs=txs, score=s, explanation=explain(w, s, txs)))

    meta = {
        "wallets": payload.wallets,
        "limit": payload.limit,
        "min_usd": payload.min_usd,
        "helius": bool(HELIUS_API_KEY),
        "mock_data": used_mock,
    }
    return AskOut(alerts=alerts, meta=meta)
