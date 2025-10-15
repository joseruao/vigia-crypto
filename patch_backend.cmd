@echo off
setlocal

:: Caminho raiz do repo (esta .cmd deve estar na raiz). Se não estiver, ajusta:
set "REPO=%cd%"

if not exist "%REPO%\backend" (
  echo [ERRO] Nao encontrei a pasta 'backend' em %REPO%
  pause & exit /b 1
)

rem ============================
rem 1) requirements.txt
rem ============================
> "%REPO%\backend\requirements.txt" (
  echo fastapi==0.111.0
  echo uvicorn==0.30.6
  echo python-dotenv==1.0.1
  echo.
  echo supabase==2.10.0
  echo gotrue==2.11.4
  echo postgrest==0.18.0
  echo realtime==2.22.0
  echo storage3==0.9.0
  echo.
  echo httpx==0.28.1
  echo httpcore==1.0.9
  echo websockets==15.0.1
  echo requests==2.32.3
  echo.
  echo numpy==2.1.1
  echo scipy==1.16.2
  echo scikit-learn==1.5.1
  echo joblib==1.4.2
  echo.
  echo pydantic==2.12.0
  echo pydantic-core==2.41.1
  echo starlette==0.37.2
  echo anyio==4.11.0
  echo ujson==5.11.0
  echo orjson==3.11.3
  echo python-multipart==0.0.20
  echo.
  echo tqdm==4.67.1
  echo typing-extensions==4.15.0
)
echo [OK] backend\requirements.txt escrito.

rem ============================
rem 2) Api\main.py
rem ============================
> "%REPO%\backend\Api\main.py" (
  echo # -*- coding: utf-8 -*-
  echo from fastapi import FastAPI
  echo from fastapi.middleware.cors import CORSMiddleware
  echo.
  echo from .routes.alerts import router as alerts_router
  echo from .routes.chat import router as chat_router
  echo from .routes.health import router as health_router
  echo.
  echo app = FastAPI(title="Vigia Crypto API", version="1.0.0")
  echo.
  echo app.add_middleware(
  echo ^    CORSMiddleware,
  echo ^    allow_origins=["*"],
  echo ^    allow_credentials=True,
  echo ^    allow_methods=["*"],
  echo ^    allow_headers=["*"],
  echo )
  echo.
  echo app.include_router(alerts_router, prefix="")
  echo app.include_router(chat_router, prefix="")
  echo app.include_router(health_router, prefix="")
  echo.
  echo from .routes import health as health_module
  echo health_module.routes.app = app  # type: ignore
  echo.
  echo @app.get("/ping")
  echo def ping():
  echo ^    return {"status": "ok"}
)
echo [OK] backend\Api\main.py escrito.

rem ============================
rem 3) Api\routes\health.py
rem ============================
> "%REPO%\backend\Api\routes\health.py" (
  echo # -*- coding: utf-8 -*-
  echo from fastapi import APIRouter
  echo import importlib
  echo.
  echo router = APIRouter(tags=["health"])
  echo.
  echo @router.get("/__version")
  echo def version():
  echo ^    return {"api_version": "alerts-v2", "desc": "tem /alerts/ask GET e POST com analysis_text e dedupe"}
  echo.
  echo @router.get("/debug/deps")
  echo def debug_deps():
  echo ^    mods = ["httpx","supabase","gotrue","postgrest","realtime","storage3","fastapi","uvicorn"]
  echo ^    out = {}
  echo ^    for m in mods:
  echo ^        try:
  echo ^            mod = importlib.import_module(m)
  echo ^            out[m] = getattr(mod, "__version__", "unknown")
  echo ^        except Exception as e:
  echo ^            out[m] = f"ERR: {e}"
  echo ^    return out
  echo.
  echo @router.get("/__routes")
  echo def routes():
  echo ^    from fastapi import FastAPI
  echo ^    from fastapi.routing import APIRoute
  echo ^    app: FastAPI = routes.app  # injetado pelo main
  echo ^    items = []
  echo ^    for r in app.routes:
  echo ^        if isinstance(r, APIRoute):
  echo ^            items.append({"path": r.path, "methods": sorted(list(r.methods))})
  echo ^    return items
)
echo [OK] backend\Api\routes\health.py escrito.

rem ============================
rem 4) Api\routes\alerts.py (tolerante + Supabase lazy)
rem ============================
> "%REPO%\backend\Api\routes\alerts.py" (
  echo # -*- coding: utf-8 -*-
  echo from fastapi import APIRouter, Query, Request
  echo from pydantic import BaseModel
  echo from typing import Optional, List, Dict, Any
  echo import os, threading, json
  echo from dotenv import load_dotenv
  echo load_dotenv()
  echo.
  echo router = APIRouter(tags=["alerts"])
  echo.
  echo from supabase import create_client
  echo _SUPA_LOCK = threading.Lock()
  echo _SUPA_CLIENT = None
  echo.
  echo def get_supabase():
  echo ^    global _SUPA_CLIENT
  echo ^    if _SUPA_CLIENT is None:
  echo ^        with _SUPA_LOCK:
  echo ^            if _SUPA_CLIENT is None:
  echo ^                SUPABASE_URL = os.getenv("SUPABASE_URL")
  echo ^                SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
  echo ^                if not SUPABASE_URL or not SUPABASE_KEY:
  echo ^                    raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY em falta no ambiente do servico WEB.")
  echo ^                _SUPA_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
  echo ^    return _SUPA_CLIENT
  echo.
  echo EXCHANGES = ["Binance","Coinbase","Kraken","Bybit","Gate.io","Bitget","OKX","MEXC"]
  echo.
  echo class ChatRequest(BaseModel):
  echo ^    prompt: str
  echo.
  echo def _coingecko_url(token: str) -> str:
  echo ^    token = (token or "").strip()
  echo ^    return f"https://www.coingecko.com/en/search?query={token}"
  echo.
  echo def _dexscreener_url(row: Dict[str, Any]) -> str:
  echo ^    pair_url = row.get("pair_url")
  echo ^    if pair_url:
  echo ^        return pair_url
  echo ^    token_addr = row.get("token_address") or ""
  echo ^    token = row.get("token") or ""
  echo ^    return f"https://dexscreener.com/solana/{token_addr}" if token_addr else f"https://dexscreener.com/search?q={token}"
  echo.
  echo def _fetch_rows(detected_exchange: Optional[str]) -> List[Dict[str, Any]]:
  echo ^    supabase = get_supabase()
  echo ^    base = supabase.table("transacted_tokens").select(
  echo ^        "id, exchange, token, token_address, value_usd, liquidity, volume_24h, score, pair_url, ts, analysis_text"
  echo ^    )
  echo ^    if detected_exchange:
  echo ^        base = base.eq("exchange", detected_exchange)
  echo ^    resp = base.order("score", desc=True).order("ts", desc=True).limit(100).execute()
  echo ^    return getattr(resp, "data", []) or []
  echo.
  echo def _dedupe_rows(rows: List[Dict[str, Any]], key_fields=("token_address","exchange"), limit=10) -> List[Dict[str, Any]]:
  echo ^    seen = set(); out = []
  echo ^    for r in rows:
  echo ^        k = tuple((r.get(f) or "").lower() for f in key_fields)
  echo ^        if k in seen: continue
  echo ^        seen.add(k); out.append(r)
  echo ^        if len(out) >= limit: break
  echo ^    return out
  echo.
  echo def _build_answer(prompt: str, exchange: Optional[str] = None) -> dict:
  echo ^    q = (prompt or "").lower()
  echo ^    detected_exchange = next((ex for ex in EXCHANGES if ex.lower() in q), None)
  echo ^    if exchange: detected_exchange = exchange
  echo ^    rows = _fetch_rows(detected_exchange)
  echo ^    if not rows:
  echo ^        where = f"na {detected_exchange}" if detected_exchange else ""
  echo ^        return {"answer": f"Nenhum token encontrado {where}."}
  echo ^    rows = _dedupe_rows(rows, key_fields=("token_address","exchange"), limit=10)
  echo ^    lines = []
  echo ^    for r in rows:
  echo ^        if r.get("analysis_text"):
  echo ^            lines.append(f"- {r['analysis_text']}")
  echo ^            continue
  echo ^        token = r.get("token") or "—"
  echo ^        ex = r.get("exchange") or "—"
  echo ^        score = r.get("score"); score_txt = f"{score:.1f}" if isinstance(score,(int,float)) else "—"
  echo ^        pair_url = _dexscreener_url(r); coingecko_url = _coingecko_url(token)
  echo ^        lines.append(f"- **{token}** _( {ex} )_ — **Score:** {score_txt}  ^n  ↳ [DexScreener]({pair_url}) · [CoinGecko]({coingecko_url})")
  echo ^    where = f"na **{detected_exchange}**" if detected_exchange else ""
  echo ^    answer = f"**Últimos potenciais listings detetados {where}:**^n^n" + "\n".join(lines)
  echo ^    return {"answer": answer}
  echo.
  echo @router.get("/alerts/predictions")
  echo def predictions():
  echo ^    try:
  echo ^        supabase = get_supabase()
  echo ^        q = supabase.table("transacted_tokens").select(
  echo ^            "id, exchange, token, token_address, value_usd, liquidity, volume_24h, score, pair_url, ts"
  echo ^        ).gte("value_usd",10000).gte("liquidity",100000).order("score",desc=True).order("ts",desc=True).limit(20)
  echo ^        resp = q.execute(); data = getattr(resp,"data",[]) or []
  echo ^        if not data:
  echo ^            resp = supabase.table("transacted_tokens").select(
  echo ^                "id, exchange, token, token_address, value_usd, liquidity, volume_24h, score, pair_url, ts"
  echo ^            ).order("ts",desc=True).limit(20).execute()
  echo ^            data = getattr(resp,"data",[]) or []
  echo ^        for r in data:
  echo ^            r["coingecko_url"] = _coingecko_url(r.get("token") or "")
  echo ^            r["pair_url"] = _dexscreener_url(r)
  echo ^        return _dedupe_rows(data, key_fields=("token_address","exchange"), limit=8)
  echo ^    except Exception as e:
  echo ^        return {"error": f"predictions failed: {e}", "data": []}
  echo.
  echo @router.post("/alerts/ask")
  echo async def ask_alerts_post(request: Request, exchange: Optional[str] = Query(None)):
  echo ^    try:
  echo ^        prompt = None
  echo ^        ctype = request.headers.get("content-type","")
  echo ^        if "application/json" in ctype:
  echo ^            data = await request.json()
  echo ^            if isinstance(data, dict): prompt = data.get("prompt")
  echo ^        elif "text/plain" in ctype:
  echo ^            prompt = (await request.body()).decode("utf-8", errors="ignore")
  echo ^        else:
  echo ^            raw = (await request.body()).decode("utf-8", errors="ignore").strip()
  echo ^            try:
  echo ^                obj = json.loads(raw)
  echo ^                if isinstance(obj, dict): prompt = obj.get("prompt")
  echo ^            except Exception:
  echo ^                prompt = raw
  echo ^        if not prompt or not str(prompt).strip():
  echo ^            return {"answer": "⚠️ prompt vazio."}
  echo ^        return _build_answer(str(prompt), exchange)
  echo ^    except Exception as e:
  echo ^        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}
  echo.
  echo @router.get("/alerts/ask")
  echo def ask_alerts_get(prompt: str = Query(..., description="pergunta do utilizador"), exchange: Optional[str] = Query(None)):
  echo ^    try:
  echo ^        return _build_answer(prompt, exchange)
  echo ^    except Exception as e:
  echo ^        return {"answer": f"⚠️ Erro a consultar tokens: {e}"}
)
echo [OK] backend\Api\routes\alerts.py escrito.

rem ============================
rem 5) Git add/commit/push
rem ============================
cd /d "%REPO%"
git add backend/requirements.txt backend/Api/main.py backend/Api/routes/health.py backend/Api/routes/alerts.py
git commit -m "fix(api): httpx 0.28.1; Supabase lazy; /__version;/debug/deps; /alerts/ask tolerante"
git push

echo.
echo [PRONTO] Agora no Render (WEB service):
echo  - Root Directory: backend
echo  - Build: pip install --upgrade pip ^&^& pip install --no-cache-dir -r requirements.txt
echo  - Start: uvicorn Api.main:app --host 0.0.0.0 --port 8000
echo  - Manual Deploy ^> Clear build cache ^& Deploy
echo.
pause
