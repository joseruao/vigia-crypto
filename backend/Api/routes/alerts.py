# backend/Api/routes/alerts.py
from __future__ import annotations
import os, time
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Garante que o diretório backend está no path para imports absolutos
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils import supa

router = APIRouter(tags=["alerts"])

# Normalização de exchanges (p/ “listado noutra”)
EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
    "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
    "Bybit": "Bybit", "Gate.io": "Gate.io", "Bitget": "Bitget",
    "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
    "OKX": "OKX", "MEXC": "MEXC"
}

class AskIn(BaseModel):
    prompt: str

@router.get("/alerts/health")
def alerts_health():
    return {
        "ok": True,
        "ts": int(time.time()),
        "supabase_url": bool(os.getenv("SUPABASE_URL")),
        "has_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    }

@router.post("/alerts/test-insert")
def test_insert():
    """
    Endpoint de teste para inserir um registo de teste na tabela.
    Útil para verificar se a inserção funciona.
    """
    import logging
    from datetime import datetime, timezone
    
    log = logging.getLogger("vigia")
    
    if not supa.ok():
        return {"ok": False, "error": "Supabase não configurado"}
    
    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        supabase_client = create_client(supabase_url, supabase_key)
        
        test_data = {
            "type": "holding",
            "exchange": "Binance",
            "token": "TEST",
            "token_address": "TestAddress123",
            "chain": "solana",
            "score": 75.5,
            "value_usd": 50000.0,
            "liquidity": 1000000.0,
            "volume_24h": 500000.0,
            "ts": datetime.now(timezone.utc).isoformat(),
            "pair_url": "https://dexscreener.com/test",
            "analysis_text": "Teste de inserção via API",
            "ai_analysis": "Este é um registo de teste inserido via endpoint /alerts/test-insert"
        }
        
        log.info("Inserindo dados de teste...")
        response = supabase_client.table("transacted_tokens").insert(test_data).execute()
        
        if hasattr(response, 'data') and response.data:
            return {
                "ok": True,
                "message": "Dados de teste inseridos com sucesso",
                "id": response.data[0].get('id'),
                "data": test_data
            }
        else:
            return {"ok": False, "error": "Resposta sem dados", "response": str(response)}
            
    except Exception as e:
        log.error(f"Erro ao inserir dados de teste: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

@router.get("/alerts/holdings")
def get_holdings():
    """
    Devolve os holdings atuais (tabela transacted_tokens) — último snapshot por token/exchange.
    """
    import logging
    log = logging.getLogger("vigia")
    
    if not supa.ok():
        log.warning("Supabase não configurado")
        return {"ok": False, "error": "Supabase não configurado", "items": []}

    try:
        # 1) Trazer últimas linhas por (exchange, token, chain, type='holding')
        params = {
            "type": "eq.holding",
            "select": "exchange,token,token_address,chain,score,ts,listed_exchanges,analysis_text,ai_analysis,pair_url,value_usd,liquidity,volume_24h",
            "limit": "500",
            "order": "ts.desc"
        }
        
        log.info("Buscando holdings do Supabase...")
        r = supa.rest_get("transacted_tokens", params=params, timeout=8)
        
        if r.status_code != 200:
            error_msg = r.text[:200] if hasattr(r, 'text') else str(r.status_code)
            log.error(f"Erro ao buscar holdings: HTTP {r.status_code} - {error_msg}")
            return {"ok": False, "error": error_msg, "items": []}

        data: List[Dict[str, Any]] = r.json() or []
        log.info(f"Recebidos {len(data)} holdings do Supabase")

        # 2) Deduplicar por (exchange, token, chain) pegando o mais recente
        latest: Dict[str, Dict[str, Any]] = {}
        for row in data:
            k = f"{row.get('exchange')}|{row.get('token')}|{row.get('chain')}"
            if k not in latest:
                latest[k] = row
            else:
                prev_ts = latest[k].get("ts") or ""
                cur_ts  = row.get("ts") or ""
                if cur_ts > prev_ts:
                    latest[k] = row

        items = list(latest.values())
        # Ordena por score desc depois ts desc
        items.sort(key=lambda x: (float(x.get("score") or 0), str(x.get("ts") or "")), reverse=True)
        
        log.info(f"Holdings deduplicados: {len(items)}")

        return {"ok": True, "count": len(items), "items": items}
        
    except Exception as e:
        log.error(f"Erro ao processar holdings: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "items": []}

@router.get("/alerts/predictions")
def get_predictions():
    """
    Lê potenciais listings (holdings com score alto que ainda não foram listados).
    Busca na tabela transacted_tokens com type='holding' e filtra por score alto.
    Retorna lista direta de items (não objeto com ok/items) para compatibilidade com frontend.
    """
    import logging
    log = logging.getLogger("vigia")
    
    if not supa.ok():
        log.warning("Supabase não configurado")
        return []

    try:
        # Busca holdings (que são as predictions de potencial listing)
        # Timeout reduzido para 8 segundos para evitar travamentos
        # Limite de 500 registos para evitar queries muito lentas
        params = {
            "type": "eq.holding",
            "select": "id,exchange,token,chain,score,ts,listed_exchanges,analysis_text,ai_analysis,pair_url,value_usd,liquidity,volume_24h,token_address",
            "limit": "500",
            "order": "ts.desc"
        }
        
        log.info(f"Buscando predictions do Supabase...")
        r = supa.rest_get("transacted_tokens", params=params, timeout=8)
        
        if r.status_code != 200:
            log.error(f"Erro ao buscar predictions: HTTP {r.status_code} - {r.text[:200]}")
            return []

        data = r.json() or []
        log.info(f"Recebidos {len(data)} registos do Supabase")
        
        # Filtra por score mínimo de 50 e ordena por score desc
        filtered = [x for x in data if float(x.get("score") or 0) >= 50]
        filtered.sort(key=lambda x: (float(x.get("score") or 0), str(x.get("ts") or "")), reverse=True)
        
        log.info(f"Predictions filtradas (score >= 50): {len(filtered)}")
        
        # Retorna lista direta (formato esperado pelo frontend)
        return filtered
        
    except Exception as e:
        log.error(f"Erro ao processar predictions: {e}", exc_info=True)
        return []

@router.post("/alerts/ask")
def ask_alerts(payload: AskIn):
    """
    Perguntas tipo:
    - "que tokens a binance tem em holding que ainda nao foram listados?"
    - "mostra holdings da gate.io com score > 70"
    """
    if not supa.ok():
        return {"ok": False, "error": "Supabase não configurado", "count": 0, "items": []}

    q = (payload.prompt or "").lower()

    # Defaults
    ex_norm = None
    min_score = 0
    chain = None

    # Inferência simples
    if "binance" in q: ex_norm = "Binance"
    if "gate" in q:    ex_norm = "Gate.io"
    if "bybit" in q:   ex_norm = "Bybit"
    if "bitget" in q:  ex_norm = "Bitget"
    if "kraken" in q:  ex_norm = "Kraken"
    if "okx" in q:     ex_norm = "OKX"
    if "mexc" in q:    ex_norm = "MEXC"
    if "coinbase" in q: ex_norm = "Coinbase"

    if "solana" in q:    chain = "solana"
    if "ethereum" in q:  chain = "ethereum"
    if "score >" in q:
        try:
            min_score = int(q.split("score >")[1].split()[0])
        except Exception:
            min_score = 70
    elif "score" in q and ("alto" in q or "elevado" in q):
        min_score = 70

    # Base query
    params = {
        "type": "eq.holding",
        "select": "exchange,token,token_address,chain,score,ts,listed_exchanges,pair_url,value_usd,liquidity,volume_24h"
    }
    if chain:
        params["chain"] = f"eq.{chain}"

    r = supa.rest_get("transacted_tokens", params=params)
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "count": 0, "items": []}

    data: List[Dict[str, Any]] = r.json() or []

    # Normalizar exchange → ex_norm
    def norm(ex: str) -> str:
        return EXCHANGE_NORMALIZE.get(ex, ex)

    # Filtrar
    out: List[Dict[str, Any]] = []
    for row in data:
        if ex_norm and norm(row.get("exchange", "")) != ex_norm:
            continue
        if float(row.get("score") or 0) < min_score:
            continue

        # “ainda não foram listados” → listed_exchanges não contém ex_norm
        if "nao foram listados" in q or "não foram listados" in q or "unlisted" in q:
            lst = row.get("listed_exchanges") or []
            if not isinstance(lst, list):
                lst = []
            if ex_norm and ex_norm in lst:
                # já listado lá → exclui
                continue

        out.append(row)

    # Ordena por score desc
    out.sort(key=lambda x: (float(x.get("score") or 0), str(x.get("ts") or "")), reverse=True)

    return {"ok": True, "count": len(out), "items": out}
