# backend/Api/routes/alerts.py
from __future__ import annotations
import os, time, math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Garante que o diretório backend está no path para imports absolutos
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Carrega .env antes de importar utils.supa
try:
    from dotenv import load_dotenv
    env_paths = [
        BACKEND_DIR / ".env",
        BACKEND_DIR.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)  # override=True para garantir que carrega
            break
except ImportError:
    pass

# Importa supa
from utils import supa
import os

router = APIRouter(tags=["alerts"])

# Normalização de exchanges (p/ “listado noutra”)
EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
    "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
    "Bybit": "Bybit", "Gate.io": "Gate.io", "Bitget": "Bitget",
    "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
    "OKX": "OKX", "MEXC": "MEXC"
}

TEST_TOKENS = {"TEST", "FOO", "PNUT"}
TOP100_EXCLUDED_SYMBOLS = {
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD",
    "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "RETH", "BETH",
}
DEFAULT_PREDICTIONS_MAX_AGE_HOURS = 36
PREDICTIONS_LIMIT = 10

def _prediction_max_age_hours() -> int:
    try:
        value = int(os.getenv("PREDICTIONS_MAX_AGE_HOURS", DEFAULT_PREDICTIONS_MAX_AGE_HOURS))
        return max(value, 1)
    except (TypeError, ValueError):
        return DEFAULT_PREDICTIONS_MAX_AGE_HOURS

def _prediction_since_iso() -> str:
    since = datetime.now(timezone.utc) - timedelta(hours=_prediction_max_age_hours())
    return since.isoformat()

def _is_buy_watchlist_question(q: str) -> bool:
    q = (q or "").lower()
    buy_terms = (
        "comprar", "compra", "buy", "entrada", "entrar", "aconselhas",
        "recomendas", "oportunidade", "oportunidades", "analisar",
        "melhor", "melhores", "risco", "suporte", "pullback", "rsi",
    )
    universe_terms = ("moeda", "moedas", "crypto", "cripto", "token", "tokens", "top100", "top 100", "hoje", "mercado")
    return any(term in q for term in buy_terms) and any(term in q for term in universe_terms)

def _is_top100_buy_question(q: str) -> bool:
    q = (q or "").lower()
    if "top100" not in q and "top 100" not in q:
        return False
    top100_terms = (
        "comprar", "compra", "buy", "entrada", "entrar", "aconselhas",
        "recomendas", "oportunidade", "oportunidades", "analisar",
        "analisa", "melhor", "melhores", "risco", "suporte", "rsi",
        "oversold", "sobrevend", "pullback", "hoje",
    )
    return _is_buy_watchlist_question(q) or any(term in q for term in top100_terms)

def _fmt_money(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "N/A"
    if number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if number >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:.0f}"

def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"

def _top100_mode(prompt: str) -> str:
    q = (prompt or "").lower()
    if "risco" in q or "segura" in q or "seguro" in q:
        return "low_risk"
    if "suporte" in q or "pullback" in q or "perto" in q:
        return "near_support"
    if "rsi" in q or "oversold" in q or "sobrevend" in q:
        return "low_rsi"
    return "score"

def _risk_rank(value: Any) -> int:
    text = str(value or "").upper()
    if "BAIXO" in text:
        return 0
    if "MODERADO/ELEVADO" in text:
        return 2
    if "ELEVADO" in text:
        return 3
    return 1

def _sort_top100_rows(rows: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    if mode == "low_risk":
        return sorted(rows, key=lambda row: (_risk_rank(row.get("risk")), -float(row.get("score") or 0)))
    if mode == "near_support":
        return sorted(rows, key=lambda row: (
            abs(float(row.get("current_position") if row.get("current_position") is not None else 50) - 25),
            -float(row.get("score") or 0),
        ))
    if mode == "low_rsi":
        return sorted(rows, key=lambda row: (
            float(row.get("rsi") if row.get("rsi") is not None else 50),
            -float(row.get("score") or 0),
        ))
    return sorted(rows, key=lambda row: float(row.get("score") or 0), reverse=True)

def _top100_title(mode: str, count: int) -> str:
    if mode == "low_risk":
        return f"**Top100 com menor risco para analisar ({count} moedas):**"
    if mode == "near_support":
        return f"**Top100 mais perto de zona de suporte/pullback ({count} moedas):**"
    if mode == "low_rsi":
        return f"**Top100 com RSI mais baixo para analisar ({count} moedas):**"
    return f"**Shortlist top100 para analisar hoje ({count} moedas):**"

def _fetch_top100_rows(date_filter: str | None, log=None) -> tuple[list, bool]:
    """Fetch top100 rows from Supabase. Returns (rows, has_technical_cols)."""
    base_select = "date,rank,coin_id,symbol,name,price,market_cap,volume_24h,change_24h,change_7d,change_30d,volume_ratio,score,risk,signal,rationale,ts"
    tech_select = f"{base_select},rsi,trend,support,resistance,current_position,entry_zone,technical_action,technical_confidence"
    params = {"select": tech_select, "order": "score.desc", "limit": "50"}
    if date_filter:
        params["date"] = f"eq.{date_filter}"
    r = supa.rest_get("top100_technical_rankings", params=params, timeout=8)
    if r.status_code != 200:
        # Fallback: try without technical columns (older schema)
        params2 = {"select": base_select, "order": "score.desc", "limit": "50"}
        if date_filter:
            params2["date"] = f"eq.{date_filter}"
        r2 = supa.rest_get("top100_technical_rankings", params=params2, timeout=8)
        if r2.status_code != 200:
            if log:
                log.warning("Top100 ranking indisponivel: HTTP %s / %s", r.status_code, r2.status_code)
            return [], False
        if log:
            log.warning("Top100 ranking sem colunas tecnicas; usando select legacy")
        return r2.json() or [], False
    return r.json() or [], True


def _answer_top100_buy_watchlist(log=None, prompt: str = "") -> Dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    raw, has_tech = _fetch_top100_rows(today, log)
    if not raw:
        raw, has_tech = _fetch_top100_rows(yesterday, log)
    if not raw:
        # Last resort: no date filter (any historical data)
        raw, has_tech = _fetch_top100_rows(None, log)

    if raw is None or (isinstance(raw, list) and len(raw) == 0 and not has_tech):
        answer = (
            "Ainda nao tenho o ranking tecnico diario do top100 disponivel.\n\n"
            "Confirma nos logs do cron dos holders a linha "
            "`Confirmacao Supabase: X linhas visiveis em top100_technical_rankings`.\n\n"
            "Enquanto isso podes usar `analisa BTC`, `analisa SOL`, `analisa NEAR`, etc."
        )
        return {"ok": True, "answer": answer, "count": 0, "items": []}

    mode = _top100_mode(prompt)
    rows = [
        row for row in raw
        if str(row.get("symbol") or "").upper() not in TOP100_EXCLUDED_SYMBOLS
        and float(row.get("score") or 0) > 0
    ]
    rows = _sort_top100_rows(rows, mode)[:10]
    if not rows:
        answer = (
            "A tabela top100 existe mas nao tem dados validos para hoje.\n\n"
            "O cron dos holders atualiza o top100 na FASE 1.5 — verifica nos logs se correu sem erros.\n\n"
            "Enquanto isso podes usar `analisa BTC`, `analisa SOL`, `analisa NEAR`, etc."
        )
        return {"ok": True, "answer": answer, "count": 0, "items": []}

    lines = [
        f"{_top100_title(mode, len(rows))}\n",
        "Base: score tecnico diario com momentum 24h/7d/30d, volume relativo e risco. Isto nao e recomendacao de compra; e uma fila de analise.\n",
    ]
    for i, item in enumerate(rows, 1):
        symbol = item.get("symbol") or "N/A"
        name = item.get("name") or symbol
        score = item.get("score") or 0
        price = _fmt_money(item.get("price"))
        change_24h = _fmt_pct(item.get("change_24h"))
        line = (
            f"{i}. **{symbol}** ({name}) - score **{float(score):.1f}/100** · "
            f"sinal **{item.get('signal', 'N/A')}** · risco **{item.get('risk', 'N/A')}** · "
            f"7d {_fmt_pct(item.get('change_7d'))} · 30d {_fmt_pct(item.get('change_30d'))} · "
            f"vol {_fmt_money(item.get('volume_24h'))}"
        )
        line += f"\n   Preco: **{price}** | 24h {change_24h}"
        if item.get("rsi") is not None:
            line += (
                f"\n   RSI: **{_fmt_pct(item.get('rsi')).replace('%', '')}** | "
                f"tendencia **{item.get('trend', 'N/A')}** | "
                f"range **{_fmt_pct(item.get('current_position'))}**"
            )
        if item.get("support") is not None and item.get("resistance") is not None:
            line += f"\n   Suporte: **{_fmt_money(item.get('support'))}** | Resistencia: **{_fmt_money(item.get('resistance'))}**"
        rationale = item.get("rationale")
        if rationale:
            line += f"\n  Motivo: {rationale}"
        lines.append(line)

    examples = ", ".join(str(row.get("symbol") or "").upper() for row in rows[:3] if row.get("symbol"))
    if examples:
        first_symbol = examples.split(", ")[0]
        lines.append(f"\nProximo passo: escolhe uma e pede `analisa {first_symbol}`. Exemplos desta lista: {examples}.")
    return {"ok": True, "answer": "\n".join(lines), "count": len(rows), "items": rows}

def _is_test_token(row: Dict[str, Any]) -> bool:
    token = str(row.get("token") or "").strip().upper()
    token_address = str(row.get("token_address") or "").strip().lower()
    pair_url = str(row.get("pair_url") or "").strip().lower()
    analysis = " ".join(
        str(row.get(field) or "").lower()
        for field in ("analysis", "analysis_text", "ai_analysis")
    )
    return (
        token in TEST_TOKENS
        or token_address.startswith("test")
        or "/test" in pair_url
        or "registo de teste" in analysis
        or "registro de teste" in analysis
    )

def _score(row: Dict[str, Any]) -> float:
    try:
        return float(row.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0

def _num(row: Dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0

def _freshness_bonus(row: Dict[str, Any]) -> float:
    try:
        ts_raw = str(row.get("ts") or "")
        if not ts_raw:
            return 0.0
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours <= 24:
            return 6.0
        if age_hours <= 72:
            return 3.0
        return 0.0
    except Exception:
        return 0.0

def _listing_score(row: Dict[str, Any]) -> float:
    """Score continuo para UI/chat; evita dezenas de candidatos empatados em 70."""
    value_usd = _num(row, "value_usd")
    liquidity = _num(row, "liquidity")
    volume_24h = _num(row, "volume_24h")
    raw_score = _score(row)

    score = 22.0
    if value_usd > 0:
        score += min(24.0, math.log10(value_usd + 1) * 3.6)
    else:
        score -= 8.0

    if liquidity > 0:
        score += min(24.0, math.log10(liquidity + 1) * 3.2)
    if liquidity < 100_000:
        score -= 8.0

    if volume_24h > 0:
        score += min(14.0, math.log10(volume_24h + 1) * 2.1)

    if row.get("pair_url"):
        score += 2.0
    score += _freshness_bonus(row)

    # Mantem algum sinal do score original, mas sem deixar o 70 dominar tudo.
    score = score * 0.82 + raw_score * 0.18
    lower_bound = 50.0 if raw_score >= 50 else 0.0
    return round(min(max(score, lower_bound), 99.0), 1)

def _apply_listing_score(row: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(row)
    updated["raw_score"] = _score(row)
    updated["score"] = _listing_score(row)
    return updated

def _normalize_exchange(exchange: str) -> str:
    exchange = str(exchange or "").strip()
    return EXCHANGE_NORMALIZE.get(exchange, exchange)

def _token_candidates(token: str) -> set:
    base = str(token or "").strip().upper().lstrip("$")
    if not base:
        return set()
    candidates = {base}
    candidates.update({f"1000{base}", f"10000{base}", f"1000000{base}", f"1M{base}"})
    for prefix in ("1000000", "10000", "1000", "1M"):
        if base.startswith(prefix) and len(base) > len(prefix):
            candidates.add(base[len(prefix):])
    if base == "BABYDOGE":
        candidates.update({"1MBABYDOGE", "1000000BABYDOGE"})
    return candidates

def _dedupe_latest_predictions(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = "|".join([
            str(row.get("exchange") or ""),
            str(row.get("token_address") or row.get("token") or ""),
            str(row.get("chain") or ""),
        ]).lower()
        if key not in latest or str(row.get("ts") or "") > str(latest[key].get("ts") or ""):
            latest[key] = row

    items = list(latest.values())
    items.sort(key=lambda x: (_score(x), str(x.get("ts") or "")), reverse=True)
    return items

def _load_listed_tokens_map(log=None) -> Dict[str, set]:
    try:
        rows = []
        page_size = 1000
        offset = 0
        while True:
            params = {
                "select": "exchange,token",
                "limit": str(page_size),
                "offset": str(offset),
            }
            r = supa.rest_get("exchange_tokens", params=params, timeout=8)
            if r.status_code != 200:
                if log:
                    log.warning("Nao foi possivel carregar exchange_tokens: HTTP %s", r.status_code)
                return {}
            page = r.json() or []
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        listed: Dict[str, set] = {}
        for row in rows:
            exchange = _normalize_exchange(str(row.get("exchange") or "").strip())
            token = str(row.get("token") or "").strip().upper()
            if exchange and token:
                listed.setdefault(exchange, set()).update(_token_candidates(token))
        return listed
    except Exception as e:
        if log:
            log.warning("Erro ao carregar exchange_tokens: %s", e)
        return {}

def _is_listed_on_own_exchange(row: Dict[str, Any], listed_tokens: Dict[str, set]) -> bool:
    exchange = _normalize_exchange(str(row.get("exchange") or ""))
    candidates = _token_candidates(str(row.get("token") or ""))
    if not exchange or not candidates:
        return False
    listed = listed_tokens.get(exchange, set())
    return any(token in listed for token in candidates)

def _filter_prediction_rows(
    rows: List[Dict[str, Any]],
    listed_tokens: Dict[str, set],
    min_score: float = 50,
    log=None,
) -> List[Dict[str, Any]]:
    filtered = []
    excluded_listed = []
    for row in rows:
        if _score(row) < min_score or _is_test_token(row):
            continue
        if _is_listed_on_own_exchange(row, listed_tokens):
            excluded_listed.append(f"{row.get('token')}@{_normalize_exchange(row.get('exchange'))}")
            continue
        filtered.append(_apply_listing_score(row))
    if log and excluded_listed:
        log.info("Predictions excluidas por ja estarem listadas na propria exchange: %s", ", ".join(excluded_listed[:20]))
    return _dedupe_latest_predictions(filtered)

def _merge_prediction_backfill(recent: List[Dict[str, Any]], fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    combined = list(recent)
    seen = {
        "|".join([
            str(row.get("exchange") or ""),
            str(row.get("token_address") or row.get("token") or ""),
            str(row.get("chain") or ""),
        ]).lower()
        for row in combined
    }
    for row in fallback:
        key = "|".join([
            str(row.get("exchange") or ""),
            str(row.get("token_address") or row.get("token") or ""),
            str(row.get("chain") or ""),
        ]).lower()
        if key in seen:
            continue
        combined.append(row)
        seen.add(key)
        if len(combined) >= PREDICTIONS_LIMIT:
            break
    return combined

class AskIn(BaseModel):
    prompt: str

@router.get("/alerts/health")
def alerts_health():
    import logging
    log = logging.getLogger("vigia")
    
    # Usa supa.ok() que recarrega automaticamente
    is_ok = supa.ok()
    
    # Obtém valores usando as funções do supa se disponíveis
    if hasattr(supa, '_get_url') and hasattr(supa, '_get_key'):
        supabase_url = supa._get_url()
        supabase_key = supa._get_key()
    else:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
    
    log.info(f"🔍 Health check: URL={'✅' if supabase_url else '❌'}, KEY={'✅' if supabase_key else '❌'}, supa.ok()={is_ok}")
    
    return {
        "ok": True,
        "ts": int(time.time()),
        "supabase_url": bool(supabase_url),
        "has_key": bool(supabase_key),
        "supabase_url_length": len(supabase_url) if supabase_url else 0,
        "supabase_key_length": len(supabase_key) if supabase_key else 0,
        "supa_ok": is_ok
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
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
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
        listed_tokens = _load_listed_tokens_map(log)
        base_select = "id,exchange,token,chain,score,ts,listed_exchanges,analysis_text,ai_analysis,pair_url,value_usd,liquidity,volume_24h,token_address"
        # Busca holdings (que são as predictions de potencial listing)
        # Timeout reduzido para 8 segundos para evitar travamentos
        # Limite de 500 registos para evitar queries muito lentas
        params = {
            "type": "eq.holding",
            "select": base_select,
            "limit": "500",
            "order": "ts.desc",
            "ts": f"gte.{_prediction_since_iso()}"
        }
        
        log.info(f"Buscando predictions do Supabase...")
        r = supa.rest_get("transacted_tokens", params=params, timeout=8)
        
        if r.status_code != 200:
            log.error(f"Erro ao buscar predictions: HTTP {r.status_code} - {r.text[:200]}")
            return []

        data = r.json() or []
        log.info(f"Recebidos {len(data)} registos do Supabase")
        
        # Filtra por score mínimo de 50 e ordena por score desc
        filtered = _filter_prediction_rows(data, listed_tokens, log=log)
        
        log.info(
            "Predictions filtradas (score >= 50, ultimas %sh): %s",
            _prediction_max_age_hours(),
            len(filtered),
        )
        
        # Se não houver nenhuma com score >= 50, retorna todas ordenadas por score (para debug)
        if len(filtered) < PREDICTIONS_LIMIT:
            log.warning("Predictions recentes insuficientes (%s/%s). A procurar fallback historico nao listado.", len(filtered), PREDICTIONS_LIMIT)
            fallback_params = {
                "type": "eq.holding",
                "select": base_select,
                "limit": "500",
                "order": "score.desc",
            }
            fallback_r = supa.rest_get("transacted_tokens", params=fallback_params, timeout=8)
            if fallback_r.status_code != 200:
                log.error(f"Erro ao buscar fallback predictions: HTTP {fallback_r.status_code} - {fallback_r.text[:200]}")
                return filtered[:PREDICTIONS_LIMIT]
            fallback_filtered = _filter_prediction_rows(fallback_r.json() or [], listed_tokens, log=log)
            filtered = _merge_prediction_backfill(filtered, fallback_filtered)
            log.info("Predictions apos backfill historico: %s", len(filtered))
        
        # Retorna lista direta (formato esperado pelo frontend)
        return filtered[:PREDICTIONS_LIMIT]
        
    except Exception as e:
        log.error(f"Erro ao processar predictions: {e}", exc_info=True)
        return []

@router.post("/alerts/ask")
def ask_alerts(payload: AskIn):
    """
    Perguntas tipo:
    - "que tokens a binance tem em holding que ainda nao foram listados?"
    - "mostra holdings da gate.io com score > 70"
    - "que tokens achas que vão ser listados?"
    """
    import sys
    import logging
    from pathlib import Path
    
    # Configura logging para ficheiro também
    log_file = Path(__file__).parent.parent.parent / "alerts_debug.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    log = logging.getLogger("vigia")
    # Garante que o nível está configurado
    log.setLevel(logging.INFO)
    # Adiciona handler de ficheiro se ainda não existir
    if not any(isinstance(h, logging.FileHandler) for h in log.handlers):
        log.addHandler(file_handler)
    
    # FORÇA OUTPUT IMEDIATO
    msg_start = f"\n{'='*80}\n🚀 ENDPOINT /alerts/ask CHAMADO!\n📝 Pergunta: {payload.prompt if hasattr(payload, 'prompt') else 'N/A'}\n{'='*80}\n"
    print(msg_start, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    log.info(msg_start)
    log.info(f"Payload completo: {payload}")
    
    # Debug: verifica configuração do Supabase
    # Força recarregamento antes de verificar
    print("="*60, flush=True)  # flush=True para garantir que aparece imediatamente
    print("🔍 VERIFICANDO CONFIGURAÇÃO SUPABASE NO /alerts/ask", flush=True)
    print("="*60, flush=True)
    sys.stdout.flush()  # Força flush do stdout
    sys.stderr.flush()  # Força flush do stderr
    log.info("="*60)
    log.info("🔍 VERIFICANDO CONFIGURAÇÃO SUPABASE NO /alerts/ask")
    log.info("="*60)
    
    # Primeiro, recarrega manualmente para garantir
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent.parent
        env_paths = [
            backend_dir / ".env",
            backend_dir.parent / ".env",
        ]
        
        print("📁 Tentando carregar .env manualmente...", flush=True)  # flush=True
        sys.stdout.flush()
        log.info("📁 Tentando carregar .env manualmente...")
        
        # Guarda valores ANTES de carregar
        url_before = os.getenv("SUPABASE_URL", "")
        key_before = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        print(f"   ANTES de carregar: URL={len(url_before)} chars, KEY={len(key_before)} chars", flush=True)
        sys.stdout.flush()
        
        # Inicializa variáveis (serão atualizadas durante o carregamento)
        supabase_url = ""
        supabase_key = ""
        
        for env_path in env_paths:
            if env_path.exists():
                result = load_dotenv(env_path, override=True)
                print(f"   ✅ Carregado de: {env_path}")  # print também
                print(f"   load_dotenv retornou: {result}")
                log.info(f"   ✅ Carregado de: {env_path}")
                log.info(f"   load_dotenv retornou: {result}")
                
                # Verifica imediatamente após carregar
                test_url = os.getenv("SUPABASE_URL", "")
                test_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
                msg = f"   Após carregar: URL={'✅' if test_url else '❌'} ({len(test_url)} chars), KEY={'✅' if test_key else '❌'} ({len(test_key)} chars)"
                print(msg, flush=True)  # print também
                sys.stdout.flush()
                log.info(msg)
                
                # Verifica se foi sobrescrito
                if key_before and not test_key:
                    print(f"   ⚠️ PROBLEMA: KEY foi sobrescrito de {len(key_before)} para {len(test_key)} chars!", flush=True)
                    print(f"   Algo está a sobrescrever o valor após carregar {env_path}", flush=True)
                    sys.stdout.flush()
                    # Restaura o valor anterior
                    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = key_before
                    test_key = key_before
                    print(f"   ✅ Valor restaurado: {len(test_key)} chars", flush=True)
                    sys.stdout.flush()
                
                # Verifica conteúdo do ficheiro
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'SUPABASE_SERVICE_ROLE_KEY' in content:
                            for line in content.split('\n'):
                                if 'SUPABASE_SERVICE_ROLE_KEY' in line and '=' in line:
                                    parts = line.split('=', 1)
                                    value = parts[1].strip().strip('"').strip("'")
                                    msg = f"   No ficheiro: KEY={'✅' if value else '❌'} ({len(value)} chars)"
                                    print(msg, flush=True)  # print também
                                    sys.stdout.flush()
                                    log.info(msg)
                                    
                                    # Se o ficheiro tem valor mas não foi carregado
                                    if value and not test_key:
                                        print(f"   ❌ PROBLEMA CRÍTICO: Ficheiro tem {len(value)} chars mas não foi carregado!", flush=True)
                                        print(f"   Tentando definir manualmente...", flush=True)
                                        sys.stdout.flush()
                                        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = value
                                        test_key = value
                                        print(f"   ✅ Definido manualmente: {len(test_key)} chars", flush=True)
                                        sys.stdout.flush()
                                    break
                except Exception as e:
                    log.warning(f"   Erro ao ler ficheiro: {e}")
                
                # Atualiza variáveis para usar o valor correto
                supabase_url = test_url
                supabase_key = test_key
                break
        
        # Verifica se há .env.local que pode estar a sobrescrever
        env_local_paths = [
            backend_dir / ".env.local",
            backend_dir.parent / ".env.local",
        ]
        for env_local_path in env_local_paths:
            if env_local_path.exists():
                print(f"   ⚠️ ATENÇÃO: .env.local encontrado em {env_local_path}", flush=True)
                print(f"   Isto pode estar a sobrescrever o .env!", flush=True)
                sys.stdout.flush()
                try:
                    with open(env_local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'SUPABASE_SERVICE_ROLE_KEY' in content:
                            for line in content.split('\n'):
                                if 'SUPABASE_SERVICE_ROLE_KEY' in line and '=' in line:
                                    parts = line.split('=', 1)
                                    value = parts[1].strip().strip('"').strip("'")
                                    if not value:
                                        print(f"   ❌ PROBLEMA: .env.local tem KEY VAZIO! Isto está a sobrescrever!", flush=True)
                                        sys.stdout.flush()
                                    break
                except Exception as e:
                    print(f"   Erro ao ler .env.local: {e}", flush=True)
                    sys.stdout.flush()
    except Exception as e:
        log.error(f"❌ Erro ao recarregar .env: {e}")
        import traceback
        log.error(traceback.format_exc())
    
    # Se já temos valores corretos do carregamento manual, usa-os
    # Caso contrário, tenta usar as funções do supa
    if not supabase_key:
        # Verifica valores atuais antes de chamar supa
        current_url = os.getenv("SUPABASE_URL", "")
        current_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
        print(f"   Valores atuais antes de chamar supa: URL={len(current_url)} chars, KEY={len(current_key)} chars", flush=True)
        sys.stdout.flush()
        
        # Agora usa as funções do supa
        print("📡 Chamando supa._get_url() e supa._get_key()...", flush=True)  # print também
        sys.stdout.flush()
        log.info("📡 Chamando supa._get_url() e supa._get_key()...")
        if hasattr(supa, '_get_url') and hasattr(supa, '_get_key'):
            supabase_url = supa._get_url()
            supabase_key = supa._get_key()
            msg = f"   Resultado: URL={len(supabase_url)} chars, KEY={len(supabase_key)} chars"
            print(msg, flush=True)  # print também
            sys.stdout.flush()
            log.info(msg)
            
            # Se ainda estiver vazio, tenta usar os valores atuais do ambiente
            if not supabase_key and current_key:
                print(f"   ⚠️ supa._get_key() retornou vazio, usando valor do ambiente: {len(current_key)} chars", flush=True)
                sys.stdout.flush()
                supabase_key = current_key
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = current_key
        else:
            log.warning("   ⚠️ Funções _get_url/_get_key não disponíveis, usando os.getenv")
            supabase_url = os.getenv("SUPABASE_URL", "")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
    else:
        print(f"   ✅ Usando valores do carregamento manual: URL={len(supabase_url)} chars, KEY={len(supabase_key)} chars", flush=True)
        sys.stdout.flush()
    
    # Verifica se está configurado usando supa.ok()
    log.info("🔍 Chamando supa.ok()...")
    is_ok = supa.ok()
    log.info(f"   supa.ok() retornou: {is_ok}")
    
    log.info(f"🔍 Debug Supabase no /alerts/ask:")
    log.info(f"   URL: {'✅' if supabase_url else '❌'} ({len(supabase_url)} chars)")
    log.info(f"   KEY: {'✅' if supabase_key else '❌'} ({len(supabase_key)} chars)")
    log.info(f"   supa.ok(): {is_ok}")
    log.info(f"   has _get_url: {hasattr(supa, '_get_url')}")
    log.info(f"   has _get_key: {hasattr(supa, '_get_key')}")
    if supabase_url:
        log.info(f"   URL preview: {supabase_url[:30]}...")
    if supabase_key:
        log.info(f"   KEY preview: {supabase_key[:20]}...")
    
    # FORÇA OUTPUT ANTES DE VERIFICAR
    print(f"\n🔍 ANTES DE VERIFICAR: URL={len(supabase_url)} chars, KEY={len(supabase_key)} chars, is_ok={is_ok}", flush=True)
    sys.stdout.flush()
    
    if not is_ok or not supabase_url or not supabase_key:
        # Mensagem detalhada para debug
        url_status = "✅" if supabase_url else "❌"
        key_status = "✅" if supabase_key else "❌"
        url_len = len(supabase_url) if supabase_url else 0
        key_len = len(supabase_key) if supabase_key else 0
        
        error_msg = (
            f"⚠️ Supabase não configurado.\n\n"
            f"📊 Detalhes:\n"
            f"- URL: {url_status} ({url_len} chars)\n"
            f"- KEY: {key_status} ({key_len} chars)\n"
            f"- supa.ok(): {is_ok}\n"
            f"- URL value: {supabase_url[:30] + '...' if supabase_url else 'VAZIO'}\n"
            f"- KEY value: {supabase_key[:20] + '...' if supabase_key else 'VAZIO'}\n\n"
            f"💡 Verifica:\n"
            f"1. Ficheiro .env em backend/.env ou raiz\n"
            f"2. Variável SUPABASE_SERVICE_ROLE_KEY=... (sem espaços)\n"
            f"3. API foi reiniciada após alterar .env\n"
            f"4. Logs da API quando inicia"
        )
        
        log.error(f"❌ Supabase não configurado! URL: {bool(supabase_url)} ({url_len} chars), KEY: {bool(supabase_key)} ({key_len} chars), supa.ok()={is_ok}")
        return {
            "ok": False, 
            "error": "Supabase não configurado", 
            "answer": error_msg,
            "count": 0, 
            "items": [],
            "debug": {
                "url_exists": bool(supabase_url),
                "url_length": url_len,
                "key_exists": bool(supabase_key),
                "key_length": key_len,
                "supa_ok": is_ok,
                "has_get_url": hasattr(supa, '_get_url'),
                "has_get_key": hasattr(supa, '_get_key'),
            }
        }
    
    log.info(f"✅ Supabase configurado corretamente")

    q = (payload.prompt or "").lower()
    log.info(f"Pergunta recebida: {payload.prompt}")

    if _is_top100_buy_question(q):
        return _answer_top100_buy_watchlist(log, payload.prompt)

    # Defaults
    ex_norm = None
    min_score = 0
    chain = None
    is_buy_watchlist_question = _is_buy_watchlist_question(q)
    
    # Se perguntar sobre "tokens que vão ser listados" sem exchange específica, usa score mínimo
    is_listing_question = "listados" in q or "listing" in q or "vão ser" in q or "vao ser" in q or "vai ser" in q or "achas" in q
    if is_listing_question and not any(ex in q for ex in ["binance", "gate", "bybit", "bitget", "kraken", "okx", "mexc", "coinbase"]):
        min_score = 50  # Score mínimo para predictions
        log.info(f"Detectada pergunta sobre listings - aplicando score mínimo: {min_score}")

    # Inferência simples
    if is_buy_watchlist_question and not any(ex in q for ex in ["binance", "gate", "bybit", "bitget", "kraken", "okx", "mexc", "coinbase"]):
        min_score = max(min_score, 50)
        log.info("Detectada pergunta de watchlist de compra - usando candidatos filtrados")

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

    filter_unlisted = is_listing_question or "nao foram listados" in q or "nÃ£o foram listados" in q or "unlisted" in q
    listed_tokens = _load_listed_tokens_map(log) if filter_unlisted else {}
    if is_buy_watchlist_question and not filter_unlisted:
        filter_unlisted = True
        listed_tokens = _load_listed_tokens_map(log)

    # Base query
    params = {
        "type": "eq.holding",
        "select": "exchange,token,token_address,chain,score,ts,listed_exchanges,pair_url,value_usd,liquidity,volume_24h,analysis_text,ai_analysis",
        "limit": "500",
        "order": "score.desc"
    }
    if chain:
        params["chain"] = f"eq.{chain}"
    if is_listing_question or is_buy_watchlist_question:
        params["ts"] = f"gte.{_prediction_since_iso()}"

    log.info(f"Buscando holdings com params: {params}")
    r = supa.rest_get("transacted_tokens", params=params, timeout=8)
    if r.status_code != 200:
        error_msg = r.text[:200] if hasattr(r, 'text') else str(r.status_code)
        log.error(f"Erro ao buscar holdings: HTTP {r.status_code} - {error_msg}")
        return {"ok": False, "error": error_msg, "answer": f"Erro ao buscar dados: {error_msg}", "count": 0, "items": []}

    data: List[Dict[str, Any]] = r.json() or []
    log.info(f"Recebidos {len(data)} holdings do Supabase")

    # Normalizar exchange → ex_norm
    def norm(ex: str) -> str:
        return EXCHANGE_NORMALIZE.get(ex, ex)

    # Filtrar
    out: List[Dict[str, Any]] = []
    for row in data:
        if _is_test_token(row):
            continue
        if filter_unlisted and _is_listed_on_own_exchange(row, listed_tokens):
            continue
        if ex_norm and norm(row.get("exchange", "")) != ex_norm:
            continue
        if _score(row) < min_score:
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
    
    log.info(f"Holdings filtrados: {len(out)}")

    out = [_apply_listing_score(row) for row in out]

    # Ordena por score desc
    out = _dedupe_latest_predictions(out)

    if len(out) < PREDICTIONS_LIMIT and (is_listing_question or is_buy_watchlist_question):
        fallback_params = params.copy()
        fallback_params.pop("ts", None)
        log.info(f"Resultados recentes insuficientes ({len(out)}/{PREDICTIONS_LIMIT}); buscando fallback historico com params: {fallback_params}")
        fallback_r = supa.rest_get("transacted_tokens", params=fallback_params, timeout=8)
        if fallback_r.status_code == 200:
            fallback_out: List[Dict[str, Any]] = []
            for row in fallback_r.json() or []:
                if _is_test_token(row):
                    continue
                if _is_listed_on_own_exchange(row, listed_tokens):
                    continue
                if ex_norm and norm(row.get("exchange", "")) != ex_norm:
                    continue
                if _score(row) < min_score:
                    continue
                fallback_out.append(row)
            fallback_out = [_apply_listing_score(row) for row in fallback_out]
            fallback_out = _dedupe_latest_predictions(fallback_out)
            out = _merge_prediction_backfill(out, fallback_out)
            log.info(f"Ask apos backfill historico: {len(out)}")

    # Formata resposta em texto para o frontend
    try:
        if len(out) == 0:
            # Mensagem mais informativa quando não há resultados
            answer = "Não encontrei tokens que correspondam à tua pesquisa."
            if ex_norm:
                answer = f"Não encontrei holdings da {ex_norm} que correspondam aos critérios."
            elif is_listing_question:
                answer = f"Não encontrei tokens com potencial de listing (score >= {min_score})."
                if len(data) > 0:
                    # Mostra quantos há no total mas não passam o filtro
                    max_score = max([float(x.get("score") or 0) for x in data] or [0])
                    answer += f"\n\n📊 Há {len(data)} holdings no total, mas nenhum com score >= {min_score}."
                    answer += f"\n💡 Score máximo encontrado: {max_score:.1f}%"
            if min_score > 0:
                answer += f"\n\n💡 Score mínimo aplicado: {min_score}%"
            answer += "\n\n💡 Tenta reduzir os filtros ou verifica se há dados no Supabase."
        else:
            lines = []
            shown = out[:10]
            if is_buy_watchlist_question:
                lines.append(f"🔎 **Watchlist para analisar hoje ({len(shown)} candidato(s)):**\n")
                lines.append("Base: sinais internos de wallets/listing ainda nao listados na propria exchange. Isto e triagem, nao recomendacao de compra.\n")
            elif is_listing_question or "listados" in q or "listing" in q:
                lines.append(f"🎯 **Top {len(shown)} token(s) com potencial de listing:**\n")
            else:
                lines.append(f"📊 **Top {len(shown)} holding(s):**\n")
            
            for i, item in enumerate(shown, 1):  # Limita a 10
                token = item.get("token", "N/A")
                exchange = _normalize_exchange(item.get("exchange", "N/A"))
                score = item.get("score", 0)
                value_usd = item.get("value_usd", 0)
                liquidity = item.get("liquidity", 0)
                pair_url = item.get("pair_url", "")
                analysis = item.get("ai_analysis") or item.get("analysis_text", "")
                
                line = f"{i}. **{token}** ({exchange})"
                if score:
                    line += f" - Score: **{score:.1f}%**"
                if value_usd:
                    line += f" - Valor: ${value_usd:,.0f}"
                if liquidity:
                    line += f" - Liquidez: ${liquidity:,.0f}"
                
                # Links formatados
                links = []
                if pair_url:
                    links.append(f"**[DexScreener]({pair_url})**")
                
                # Adiciona link CoinGecko se tiver token_address ou token name
                token_address = item.get("token_address", "")
                token_lower = token.lower()
                if token_address or token_lower:
                    # CoinGecko usa o nome do token em minúsculas na URL
                    coingecko_url = f"https://www.coingecko.com/en/coins/{token_lower}"
                    links.append(f"[CoinGecko]({coingecko_url})")
                
                if links:
                    line += f" - {' | '.join(links)}"
                
                lines.append(line)
                
                # Adiciona análise se existir (apenas para os primeiros 3)
                if analysis and i <= 3:
                    analysis_short = analysis[:150] + "..." if len(analysis) > 150 else analysis
                    lines.append(f"   💡 {analysis_short}\n")
            
            if len(out) > 10:
                lines.append(f"\n... e mais {len(out) - len(shown)} candidato(s) filtrados")
            
            answer = "\n".join(lines)
        
        log.info(f"Resposta formatada: {len(answer)} caracteres")
        return {"ok": True, "answer": answer, "count": len(out), "items": out}
        
    except Exception as e:
        log.error(f"Erro ao formatar resposta: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "answer": f"Erro ao processar: {str(e)}", "count": 0, "items": []}
