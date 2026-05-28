# backend/utils/supa.py
import os
import requests

SUPABASE_DEBUG = os.getenv("SUPABASE_DEBUG", "").lower() in {"1", "true", "yes"}

def _debug_print(message: str):
    if SUPABASE_DEBUG:
        print(message)

# Função para carregar .env
def _load_env():
    """Carrega o .env de forma robusta"""
    import logging
    log = logging.getLogger("vigia")
    
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        # IMPORTANTE: Ordem de carregamento - .env primeiro, depois .env.local
        # Se .env.local for carregado depois, pode sobrescrever com valores vazios!
        env_paths = [
            backend_dir / ".env",  # .env do backend primeiro
            backend_dir.parent / ".env",  # .env da raiz
            # NÃO carregamos .env.local porque pode sobrescrever com valores vazios
            # Se precisares de .env.local, adiciona-o mas garante que tem valores corretos
        ]
        
        loaded = False
        # Guarda valores antes de carregar para verificar se foram sobrescritos
        url_before = os.getenv("SUPABASE_URL", "")
        key_before = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        
        for env_path in env_paths:
            if env_path.exists():
                # Carrega o .env
                result = load_dotenv(env_path, override=True)
                # Verifica se carregou corretamente (tenta ambos os nomes para compatibilidade)
                url = os.getenv("SUPABASE_URL", "")
                key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
                
                _debug_print(f"Carregado .env de {env_path}")
                _debug_print(f"   load_dotenv retornou: {result}")
                _debug_print(f"   SUPABASE_URL: {'ok' if url else 'missing'} ({len(url)} chars)")
                _debug_print(f"   SUPABASE_SERVICE_ROLE_KEY: {'ok' if key else 'missing'} ({len(key)} chars)")
                log.info(f"📁 Carregado .env de {env_path}")
                log.debug(f"   load_dotenv retornou: {result}")
                log.info(f"   SUPABASE_URL: {'✅' if url else '❌'} ({len(url)} chars)")
                log.info(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if key else '❌'} ({len(key)} chars)")
                
                # Verifica se foi sobrescrito por outro ficheiro
                if key_before and not key:
                    log.warning(f"   ⚠️ ATENÇÃO: KEY foi sobrescrito! Tinha {len(key_before)} chars, agora tem {len(key)} chars")
                    log.warning(f"   Pode haver um .env.local ou outro ficheiro a sobrescrever!")
                
                # Verifica se a linha existe no ficheiro
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'SUPABASE_SERVICE_ROLE_KEY' in content:
                            # Verifica se tem valor
                            for line in content.split('\n'):
                                if 'SUPABASE_SERVICE_ROLE_KEY' in line and '=' in line:
                                    parts = line.split('=', 1)
                                    value = parts[1].strip().strip('"').strip("'")
                                    if value:
                                        log.info(f"   ✅ Linha encontrada no .env com {len(value)} chars")
                                    else:
                                        log.error(f"   ❌ Linha encontrada mas valor VAZIO!")
                                    break
                        else:
                            log.error(f"   ❌ SUPABASE_SERVICE_ROLE_KEY não encontrado no .env!")
                except Exception as e:
                    log.warning(f"   ⚠️ Erro ao ler .env: {e}")
                
                loaded = True
                break
        
        if not loaded:
            # No Render/produção, variáveis vêm do ambiente, não de ficheiros .env
            # Só mostra warning se estiver em desenvolvimento local
            if os.getenv("RENDER") is None:  # Não está no Render
                log.warning("⚠️ Nenhum .env encontrado nos caminhos:")
                for env_path in env_paths:
                    log.warning(f"   - {env_path} (existe: {env_path.exists()})")
            else:
                log.debug("ℹ️ Em produção (Render) - usando variáveis de ambiente diretamente")
        
        return loaded
    except ImportError:
        log.error("❌ python-dotenv não instalado")
        return False
    except Exception as e:
        log.error(f"❌ Erro ao carregar .env: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

# Carrega .env imediatamente (mas não confia apenas nisto)
# As funções _get_url() e _get_key() sempre recarregam
_load_env()

# Função para obter variáveis (sempre atualizadas)
def _get_url():
    """Obtém SUPABASE_URL, recarregando .env se necessário"""
    import logging
    log = logging.getLogger("vigia")
    
    # Sempre recarrega para garantir que está atualizado
    _load_env()
    url = os.getenv("SUPABASE_URL", "")
    
    if not url:
        log.warning("⚠️ SUPABASE_URL vazio após carregar .env, tentando novamente...")
        _load_env()
        url = os.getenv("SUPABASE_URL", "")
    
    if url:
        log.debug(f"✅ _get_url() retornou: {len(url)} chars")
    else:
        log.error("❌ _get_url() retornou VAZIO após múltiplas tentativas")
    
    return url

def _get_key():
    """Obtém SUPABASE_SERVICE_ROLE_KEY, recarregando .env se necessário"""
    import logging
    log = logging.getLogger("vigia")
    
    # Guarda valor atual antes de recarregar
    current_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
    if current_key:
        log.debug(f"   _get_key(): Valor atual antes de recarregar: {len(current_key)} chars")
    
    # Sempre recarrega para garantir que está atualizado
    _load_env()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
    
    # Se foi sobrescrito para vazio, restaura o valor anterior
    if current_key and not key:
        log.warning(f"KEY foi sobrescrito de {len(current_key)} para {len(key)} chars")
        log.warning(f"   Restaurando valor anterior...")
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = current_key
        key = current_key
        log.warning(f"Valor restaurado: {len(key)} chars")
    
    # Se ainda não tiver, tenta variantes do nome
    if not key:
        log.warning("⚠️ SUPABASE_SERVICE_ROLE_KEY vazio, tentando variantes...")
        # Tenta variantes comuns (incluindo SUPABASE_SERVICE_ROLE para compatibilidade com Render)
        for var_name in ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE", "SUPABASE_KEY", "SUPABASE_API_KEY"]:
            test_key = os.getenv(var_name, "")
            if test_key:
                log.info(f"   Tentando {var_name}: {'✅' if test_key else '❌'}")
            if test_key:
                key = test_key
                log.info(f"   ✅ Encontrado em {var_name}!")
                # Normaliza para SUPABASE_SERVICE_ROLE_KEY para consistência
                if var_name != "SUPABASE_SERVICE_ROLE_KEY":
                    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = test_key
                break
        
        # Se ainda não tiver, recarrega novamente mas SEM sobrescrever se já tiver valor
        if not key:
            log.warning("⚠️ Tentando recarregar .env novamente...")
            saved_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            _load_env()
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            # Se ficou vazio mas tinha valor antes, restaura
            if saved_key and not key:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = saved_key
                key = saved_key
    
    if key and not SUPABASE_DEBUG:
        log.debug(f"_get_key() retornou: {len(key)} chars")
        return key

    if key:
        msg = f"✅ _get_key() retornou: {len(key)} chars"
        _debug_print(msg)
        log.debug(msg)
    else:
        msg = "❌ _get_key() retornou VAZIO após múltiplas tentativas"
        print(msg)
        log.error(msg)
        # Debug: verifica todas as variáveis de ambiente que começam com SUPABASE
        all_supabase_vars = {k: (v[:20] + "..." if len(v) > 20 else v) if v else "VAZIO" for k, v in os.environ.items() if k.startswith("SUPABASE")}
        log.error(f"   Variáveis SUPABASE no ambiente: {all_supabase_vars}")
        log.error(f"   Total de variáveis de ambiente: {len(os.environ)}")
    
    return key

# Variáveis globais (para compatibilidade) - serão atualizadas quando necessário
SUPABASE_URL = ""
SUPABASE_SERVICE_ROLE_KEY = ""

# Função para atualizar variáveis globais
def _update_globals():
    """Atualiza as variáveis globais"""
    global SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    SUPABASE_URL = _get_url()
    SUPABASE_SERVICE_ROLE_KEY = _get_key()

# Atualiza na inicialização
_update_globals()

def headers():
    """Retorna headers HTTP com autenticação Supabase"""
    # Atualiza variáveis globais primeiro
    _update_globals()
    # Depois obtém key atualizada
    key = _get_key()
    if not key:
        # Evita meter "Bearer " vazio
        return {"apikey": "missing", "Content-Type": "application/json"}
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

def ok():
    """Verifica se as variáveis estão configuradas, recarregando se necessário"""
    # Atualiza variáveis globais primeiro
    _update_globals()
    # Depois obtém valores atualizados
    url = _get_url()
    key = _get_key()
    return bool(url) and bool(key)

def rest_get(table: str, params=None, timeout=15):
    """
    Faz GET request ao Supabase REST API.
    Retorna objeto Response do requests.
    """
    import logging
    log = logging.getLogger("vigia")
    
    url_base = _get_url()
    if not url_base:
        log.error("SUPABASE_URL não configurado")
        class ErrorResponse:
            status_code = 500
            text = "SUPABASE_URL not configured"
            def json(self):
                return []
        return ErrorResponse()
    
    url = f"{url_base}/rest/v1/{table}"
    
    try:
        log.debug(f"GET {url} com params: {params}")
        r = requests.get(url, headers=headers(), params=params or {}, timeout=timeout)
        log.debug(f"Resposta: {r.status_code}")
        return r
    except requests.exceptions.Timeout:
        log.error(f"Timeout ao buscar {table} (>{timeout}s)")
        # Retorna objeto Response simulado com erro
        class TimeoutResponse:
            status_code = 504
            text = "Request timeout"
            def json(self):
                return []
        return TimeoutResponse()
    except requests.exceptions.RequestException as e:
        log.error(f"Erro de conexão ao Supabase: {e}")
        class ErrorResponse:
            status_code = 500
            text = str(e)
            def json(self):
                return []
        return ErrorResponse()

def rest_upsert(table: str, data: dict, on_conflict: str, timeout=20):
    url_base = _get_url()
    if not url_base:
        raise ValueError("SUPABASE_URL not configured")
    url = f"{url_base}/rest/v1/{table}?on_conflict={on_conflict}"
    h = headers().copy()
    h["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(url, headers=h, json=data, timeout=timeout)
    return r

def rest_delete(table: str, params=None, timeout=15):
    """
    Faz DELETE request ao Supabase REST API.
    Retorna objeto Response do requests.
    """
    import logging
    log = logging.getLogger("vigia")
    
    url_base = _get_url()
    if not url_base:
        log.error("SUPABASE_URL não configurado")
        class ErrorResponse:
            status_code = 500
            text = "SUPABASE_URL not configured"
            def json(self):
                return []
        return ErrorResponse()
    
    url = f"{url_base}/rest/v1/{table}"
    
    try:
        log.debug(f"DELETE {url} com params: {params}")
        r = requests.delete(url, headers=headers(), params=params or {}, timeout=timeout)
        log.debug(f"Resposta: {r.status_code}")
        return r
    except requests.exceptions.Timeout:
        log.error(f"Timeout ao deletar {table} (>{timeout}s)")
        class TimeoutResponse:
            status_code = 504
            text = "Request timeout"
            def json(self):
                return []
        return TimeoutResponse()
    except requests.exceptions.RequestException as e:
        log.error(f"Erro de conexão ao Supabase: {e}")
        class ErrorResponse:
            status_code = 500
            text = str(e)
            def json(self):
                return []
        return ErrorResponse()
