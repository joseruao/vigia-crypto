# backend/utils/supa.py
import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def headers():
    if not SUPABASE_SERVICE_ROLE_KEY:
        # Evita meter "Bearer " vazio
        return {"apikey": "missing", "Content-Type": "application/json"}
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

def ok():
    return bool(SUPABASE_URL) and bool(SUPABASE_SERVICE_ROLE_KEY)

def rest_get(table: str, params=None, timeout=15):
    """
    Faz GET request ao Supabase REST API.
    Retorna objeto Response do requests.
    """
    import logging
    log = logging.getLogger("vigia")
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    
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
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    h = headers().copy()
    h["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(url, headers=h, json=data, timeout=timeout)
    return r
