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
        
        # Se não houver nenhuma com score >= 50, retorna todas ordenadas por score (para debug)
        if len(filtered) == 0 and len(data) > 0:
            log.warning(f"Nenhuma prediction com score >= 50. Total de holdings: {len(data)}")
            # Retorna top 10 por score mesmo que < 50, para debug
            all_sorted = sorted(data, key=lambda x: (float(x.get("score") or 0), str(x.get("ts") or "")), reverse=True)
            log.info(f"Retornando top 10 holdings (mesmo com score < 50) para debug")
            return all_sorted[:10]
        
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

    # Defaults
    ex_norm = None
    min_score = 0
    chain = None
    
    # Se perguntar sobre "tokens que vão ser listados" sem exchange específica, usa score mínimo
    is_listing_question = "listados" in q or "listing" in q or "vão ser" in q or "vao ser" in q or "vai ser" in q or "achas" in q
    if is_listing_question and not any(ex in q for ex in ["binance", "gate", "bybit", "bitget", "kraken", "okx", "mexc", "coinbase"]):
        min_score = 50  # Score mínimo para predictions
        log.info(f"Detectada pergunta sobre listings - aplicando score mínimo: {min_score}")

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
        "select": "exchange,token,token_address,chain,score,ts,listed_exchanges,pair_url,value_usd,liquidity,volume_24h,analysis_text,ai_analysis",
        "limit": "500",
        "order": "score.desc"
    }
    if chain:
        params["chain"] = f"eq.{chain}"

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
    
    log.info(f"Holdings filtrados: {len(out)}")

    # Ordena por score desc
    out.sort(key=lambda x: (float(x.get("score") or 0), str(x.get("ts") or "")), reverse=True)

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
            if is_listing_question or "listados" in q or "listing" in q:
                lines.append(f"🎯 **Encontrei {len(out)} token(s) com potencial de listing:**\n")
            else:
                lines.append(f"📊 **Encontrei {len(out)} holding(s):**\n")
            
            for i, item in enumerate(out[:10], 1):  # Limita a 10
                token = item.get("token", "N/A")
                exchange = item.get("exchange", "N/A")
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
                lines.append(f"\n... e mais {len(out) - 10} token(s)")
            
            answer = "\n".join(lines)
        
        log.info(f"Resposta formatada: {len(answer)} caracteres")
        return {"ok": True, "answer": answer, "count": len(out), "items": out}
        
    except Exception as e:
        log.error(f"Erro ao formatar resposta: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "answer": f"Erro ao processar: {str(e)}", "count": 0, "items": []}
