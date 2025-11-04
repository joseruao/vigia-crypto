# backend/utils/supa.py
import os, requests

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
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.get(url, headers=headers(), params=params or {}, timeout=timeout)
    return r

def rest_upsert(table: str, data: dict, on_conflict: str, timeout=20):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    h = headers().copy()
    h["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(url, headers=h, json=data, timeout=timeout)
    return r
