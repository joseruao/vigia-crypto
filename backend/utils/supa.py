# backend/utils/supa.py
import os
import requests

# Função para carregar .env
def _load_env():
    """Carrega o .env de forma robusta"""
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent
        env_paths = [
            backend_dir / ".env",
            backend_dir.parent / ".env",
        ]
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                return True
        return False
    except ImportError:
        return False
    except Exception:
        return False

# Carrega .env imediatamente
_load_env()

# Função para obter variáveis (sempre atualizadas)
def _get_url():
    """Obtém SUPABASE_URL, recarregando .env se necessário"""
    url = os.getenv("SUPABASE_URL", "")
    if not url:
        _load_env()
        url = os.getenv("SUPABASE_URL", "")
    return url

def _get_key():
    """Obtém SUPABASE_SERVICE_ROLE_KEY, recarregando .env se necessário"""
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        _load_env()
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return key

# Variáveis globais (para compatibilidade)
SUPABASE_URL = _get_url()
SUPABASE_SERVICE_ROLE_KEY = _get_key()

def headers():
    """Retorna headers HTTP com autenticação Supabase"""
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
