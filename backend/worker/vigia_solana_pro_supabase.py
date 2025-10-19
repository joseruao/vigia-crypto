# vigia_solana_pro_supabase.py
# -*- coding: utf-8 -*-

import os
import time
import math
import json
import logging
import requests
from requests.adapters import HTTPAdapter, Retry
import numpy as np
from supabase import create_client, Client
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

# ===========================
# LOGGING
# ===========================
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VigiaSolanaPro")

# ===========================
# CONFIG / ENV
# ===========================
def req_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

HELIUS_API_KEY = req_env("HELIUS_API_KEY")
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

SUPABASE_URL = req_env("SUPABASE_URL")
SUPABASE_KEY = req_env("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
ML_SCORE_THRESHOLD = float(os.environ.get("ML_SCORE_THRESHOLD", "50"))
CACHE_TTL = 60 * 60        # 1h cache de tokens listados / supported
REQUEST_TIMEOUT = 12       # seg

# HTTP session com retries (idempotentes GET/POST ao Helius/DexScreener)
def build_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET","POST"])
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=32, pool_maxsize=32)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    sess.headers.update({"User-Agent": "VigiaSolanaPro/1.1"})
    return sess

HTTP = build_session()

# ===========================
# WALLETS
# ===========================
EXCHANGE_WALLETS: Dict[str, str] = {
    "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "Binance 2": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
    "Binance 3": "8kPLJg9eKSwCoDJjK3CixgB3Mf7i5p2hWQqRgt7F5XkR",
    "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE",
    "Coinbase Hot": "FpwQQhQQoEaVu3WU2qZMfF1hx48YyfwsLoRgXG83E99Q",
    "Bybit": "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
    "Gate.io": "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w",
    "Bitget": "A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR",
    "Kraken Cold 1": "9cNE6KBg2Xmf34FPMMvzDF8yUHMrgLRzBV3vD7b1JnUS",
    "Kraken Cold 2": "F7RkX6Y1qTfBqoX5oHoZEgrG1Dpy55UZ3GfWwPbM58nQ",
    "OKX": "HWpGJNxbQRW5HiwHfL2QwF45vweKD2tSfRo8FwY3SgKp",
    "MEXC": "H7gyjxzXm7fQ6pfx9WkQqJk4DfjRk7Vc1nG5VcJqJ5qj",
}

SPECIAL_WALLETS: Dict[str, str] = {
    "Alameda Research": "MJKqp326RZCHnAAbew9MDdui3iCKWco7fsK9sVuZTX2",
    "Suspicious Early Mover": "GkPtg9Lt38syNpdBGsNJu4YMkLi5wFXq3PM8PQhxT8ry"
}

EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
    "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
    "Bybit": "Bybit", "Gate.io": "Gate.io", "Bitget": "Bitget",
    "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
    "OKX": "OKX", "MEXC": "MEXC"
}

# ===========================
# CACHE: exchange_tokens
# ===========================
LISTED_TOKENS: Dict[str, List[str]] = {}
_LISTED_CACHE_TS = 0.0

def load_listed_tokens_from_supabase(force: bool = False) -> Dict[str, List[str]]:
    global LISTED_TOKENS, _LISTED_CACHE_TS
    now = time.time()
    if not force and (now - _LISTED_CACHE_TS) < CACHE_TTL and LISTED_TOKENS:
        return LISTED_TOKENS
    try:
        resp = supabase.table("exchange_tokens").select("exchange,token").execute()
        data = getattr(resp, "data", None) or []
        temp: Dict[str, List[str]] = {}
        for row in data:
            ex = (row.get("exchange") or "").strip()
            tok = (row.get("token") or "").strip()
            if not ex or not tok:
                continue
            temp.setdefault(ex, []).append(tok)
        LISTED_TOKENS = temp
        _LISTED_CACHE_TS = now
        logger.info(f"✅ Tokens carregados do Supabase: {sum(len(v) for v in temp.values())} tokens em {len(temp)} exchanges")
        return LISTED_TOKENS
    except Exception as e:
        logger.warning(f"❌ Erro ao carregar tokens do Supabase: {e} — fallback vazio")
        LISTED_TOKENS = {}
        _LISTED_CACHE_TS = now
        return LISTED_TOKENS

def is_token_listed_on_exchange(token_symbol: str, exchange_name: str) -> bool:
    ex = EXCHANGE_NORMALIZE.get(exchange_name, exchange_name)
    tokens = LISTED_TOKENS.get(ex, [])
    return token_symbol.upper() in {t.upper() for t in tokens}

def get_listed_exchanges(token_symbol: str, exclude_exchange: Optional[str] = None) -> List[str]:
    token_upper = token_symbol.upper()
    exchanges: List[str] = []
    for ex, tokens in LISTED_TOKENS.items():
        if exclude_exchange and ex.lower() == exclude_exchange.lower():
            continue
        for t in tokens:
            if t and t.upper() == token_upper:
                exchanges.append(ex)
                break
    return exchanges

# ===========================
# HELIUS HELPERS (com paginação)
# ===========================
def get_recent_signatures(wallet_address: str, hours: int = 24, limit_per_page: int = 100) -> List[Dict[str, Any]]:
    """Página por página até sair da janela temporal ou acabar."""
    signatures: List[Dict[str, Any]] = []
    after_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    before_sig: Optional[str] = None

    while True:
        params = {"limit": limit_per_page}
        if before_sig:
            params["before"] = before_sig
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-signatures",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, params]
        }
        try:
            r = HTTP.post(HELIUS_URL, json=payload, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                logger.warning(f"Helius {r.status_code} para {wallet_address}")
                break
            result = r.json().get("result") or []
            if not result:
                break

            # filtra por tempo e acumula
            for tx in result:
                bt = tx.get("blockTime")
                if not bt:
                    continue
                if bt >= after_ts:
                    signatures.append(tx)
            # preparar próxima página
            last = result[-1].get("signature")
            if not last:
                break
            # se o último já está antes da janela temporal, parar
            last_bt = result[-1].get("blockTime") or 0
            if last_bt < after_ts:
                break
            before_sig = last
            # safety: não correr infinito
            if len(signatures) > 2000:
                break
        except Exception as e:
            logger.error(f"Erro get_recent_signatures: {e}")
            break

    return signatures

def get_transaction_details(signature: str) -> Optional[Dict[str, Any]]:
    payload = {
        "jsonrpc": "2.0",
        "id": "vigia-details",
        "method": "getTransaction",
        "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
    }
    try:
        r = HTTP.post(HELIUS_URL, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        logger.error(f"Erro get_transaction_details {signature}: {e}")
        return None

# ===========================
# DEXSCREENER HELPERS (robustos + cache)
# ===========================
_DEX_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # mint -> (ts, data)
_DEX_CACHE_TTL = 5 * 60

def _from_path(o: Any, path: List[str], default=None):
    cur = o
    try:
        for p in path:
            if cur is None:
                return default
            cur = cur.get(p) if isinstance(cur, dict) else default
        return cur if cur is not None else default
    except Exception:
        return default

def get_dexscreener_data(token_address: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    cached = _DEX_CACHE.get(token_address)
    if cached and (now - cached[0]) < _DEX_CACHE_TTL:
        return cached[1]
    try:
        r = HTTP.get(f"{DEXSCREENER_API}{token_address}", timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        j = r.json() or {}
        pairs = j.get("pairs") or []
        # escolher par com maior liquidez USD
        def liq_usd(p):
            return float(_from_path(p, ["liquidity","usd"], 0.0) or 0.0)
        best = max(pairs, key=liq_usd) if pairs else None
        if not best:
            return None
        _DEX_CACHE[token_address] = (now, best)
        return best
    except Exception as e:
        logger.debug(f"Dexscreener error for {token_address}: {e}")
        return None

def parse_pair(dex: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos críticos, tolerante a esquemas diferentes."""
    base = dex.get("baseToken") or {}
    token_symbol = (base.get("symbol") or "UNKNOWN").strip()[:20]
    price_usd = float(dex.get("priceUsd") or dex.get("price") or 0) or 0.0
    price_change_24h = (
        _from_path(dex, ["priceChange","h24"], None)
        if isinstance(dex.get("priceChange"), dict)
        else dex.get("priceChange")
    )
    try:
        price_change_24h = float(price_change_24h) if price_change_24h is not None else None
    except Exception:
        price_change_24h = None

    liquidity = float(_from_path(dex, ["liquidity","usd"], 0.0) or 0.0)
    volume_24h = float(_from_path(dex, ["volume","h24"], 0.0) or 0.0)
    tx_buys = int(_from_path(dex, ["txns","h24","buys"], 0) or 0)
    tx_sells = int(_from_path(dex, ["txns","h24","sells"], 0) or 0)
    pair_url = dex.get("url") or ""
    pair_created_ms = dex.get("pairCreatedAt")  # nem sempre existe

    # holders concentration (pouco comum, mas se existir...)
    holders_concentration = 0.0
    try:
        holders_concentration = float(_from_path(dex, ["topHolders","concentration"], 0.0) or 0.0)
    except Exception:
        holders_concentration = 0.0

    return {
        "token_symbol": token_symbol,
        "price_usd": price_usd,
        "price_change_24h": price_change_24h,
        "liquidity": liquidity,
        "volume_24h": volume_24h,
        "txns_buys": tx_buys,
        "txns_sells": tx_sells,
        "pair_url": pair_url,
        "pair_created_ms": pair_created_ms,
        "holders_concentration": holders_concentration,
    }

# ===========================
# ML (8 features) com autocheck
# ===========================
MODEL_PATH = "vigia_ml_model.pkl"
SCALER_PATH = "vigia_ml_scaler.pkl"

class CryptoAIAnalyzer:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.n_features = 8
        self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                m = joblib.load(MODEL_PATH)
                s = joblib.load(SCALER_PATH)
                # sanity-check: dimensões
                test = np.zeros((1, self.n_features))
                _ = s.transform(test)
                self.model, self.scaler = m, s
                logger.info("✅ Modelo ML carregado (8 features).")
                return
            except Exception as e:
                logger.warning(f"⚠️ Falha a carregar modelo cacheado: {e} — será re-treinado")
        self.model, self.scaler = self._create_and_train_model()
        try:
            joblib.dump(self.model, MODEL_PATH)
            joblib.dump(self.scaler, SCALER_PATH)
        except Exception as e:
            logger.debug(f"Não consegui gravar cache do modelo: {e}")

    def _create_and_train_model(self):
        """Treino sintético, mesmo racional que já tinhas, mas isolado."""
        try:
            X_train = np.array([
                [50000, 1_000_000, 500_000,  25, 100, 1, 2.0, 0.10],
                [30000,   800_000, 400_000,  15, 150, 1, 1.5, 0.15],
                [10000,   200_000,  80_000,   5, 200, 1, 1.2, 0.25],
                [ 5000,    50_000,  20_000,  -5, 300, 1, 0.5, 0.40],
                [20000, 2_000_000,1_000_000, -2,  50, 0, 1.0, 0.05],
                [15000, 1_500_000, 600_000,   8,  80, 0, 1.3, 0.08],
                [70000, 5_000_000,2_500_000,  30,  20, 0, 1.4, 0.07],
                [ 2000,    30_000,  10_000, -15, 400, 1, 0.3, 0.60],
                [12000,   100_000,  50_000,  12, 250, 1, 2.5, 0.10],
                [25000,   700_000, 300_000,  20, 120, 1, 2.0, 0.12],
            ], dtype=float)
            y_train = np.array([1,1,0,0,0,0,1,0,1,1], dtype=int)

            Xs = np.column_stack([
                X_train[:,0] / 100_000.0,
                X_train[:,1] / 1_000_000.0,
                X_train[:,2] / 500_000.0,
                X_train[:,3] / 100.0,
                X_train[:,4] / 1000.0,
                X_train[:,5],
                X_train[:,6],
                X_train[:,7],
            ])

            scaler = StandardScaler().fit(Xs)
            model = RandomForestClassifier(
                n_estimators=200, max_depth=10,
                random_state=42, class_weight="balanced"
            ).fit(Xs, y_train)

            logger.info("✅ Modelo ML treinado (8 features).")
            return model, scaler

        except Exception as e:
            logger.error(f"Erro treino ML: {e}")
            class Dummy:
                def predict_proba(self, X): return np.array([[0.45, 0.55]])
            class DS:
                def transform(self, X): return X
            return Dummy(), DS()

    def _extract_features(self, token_data: Dict[str, Any], is_new_token: bool = True):
        liquidity    = float(token_data.get('liquidity', 0) or 0)
        volume_24h   = float(token_data.get('volume_24h', 0) or 0)
        price_change = float(token_data.get('price_change_24h', 0) or 0)
        value_usd    = float(token_data.get('value_usd', 0) or 0)

        if   liquidity > 5_000_000: market_cap_rank = 50
        elif liquidity > 1_000_000: market_cap_rank = 100
        elif liquidity >   500_000: market_cap_rank = 200
        else:                       market_cap_rank = 500

        buys  = float(token_data.get('txns_buys', 1)  or 1)
        sells = float(token_data.get('txns_sells', 1) or 1)
        buys_sells_ratio = buys / max(sells, 1)
        holders_concentration = float(token_data.get('holders_concentration', 0.1) or 0.1)

        feats = np.array([[
            value_usd / 100_000.0,
            liquidity / 1_000_000.0,
            volume_24h / 500_000.0,
            price_change / 100.0,
            market_cap_rank / 1000.0,
            1.0 if is_new_token else 0.0,
            buys_sells_ratio,
            holders_concentration
        ]], dtype=float)
        return feats

    def predict_listing_potential(self, token_data: Dict[str, Any], exchange_name: str, token_symbol: str):
        try:
            is_new = not is_token_listed_on_exchange(token_symbol, exchange_name)
            X = self._extract_features(token_data, is_new_token=is_new)
            Xs = self.scaler.transform(X)
            proba = self.model.predict_proba(Xs)[0]
            p1 = float(proba[1])*100.0
            return {
                'listing_probability': p1,
                'score': p1,
                'confidence': float(max(proba))*100.0,
                'is_new_token': is_new
            }
        except Exception as e:
            logger.error(f"Erro ML predict: {e}")
            return {'listing_probability': 55.0, 'score': 55.0, 'confidence': 50.0, 'is_new_token': True}

# ===========================
# ANÁLISE IA EXPLICATIVA (NOVO!)
# ===========================
def generate_ai_analysis(alert_data: Dict[str, Any]) -> str:
    """
    Gera uma análise IA explicativa do potencial listing
    """
    token = alert_data.get('token', 'Unknown')
    exchange = alert_data.get('exchange', 'Unknown')
    score = alert_data.get('score', 0)
    liquidity = alert_data.get('liquidity', 0)
    volume_24h = alert_data.get('volume_24h', 0)
    value_usd = alert_data.get('value_usd', 0)
    listed_exchanges = alert_data.get('listed_exchanges', [])
    txns_buys = alert_data.get('txns_buys', 0)
    txns_sells = alert_data.get('txns_sells', 0)
    holders_concentration = alert_data.get('holders_concentration', 0.0)
    
    # Análise de fatores
    factors = []
    confidence_level = ""
    
    # Análise do Score ML
    if score >= 80:
        factors.append(f"📊 **Score ML muito alto ({score}%)** - padrão muito similar a tokens que foram listados anteriormente")
        confidence_level = "muito alto"
    elif score >= 60:
        factors.append(f"📊 **Score ML alto ({score}%)** - características positivas comparando com históricos de listing")
        confidence_level = "alto"
    else:
        factors.append(f"📊 **Score ML moderado ({score}%)** - alguns indicadores positivos mas não conclusivos")
        confidence_level = "moderado"
    
    # Análise de Liquidez
    if liquidity > 1000000:
        factors.append(f"💰 **Liquidez excelente (${liquidity:,.0f})** - suficiente para suportar trading institucional")
    elif liquidity > 500000:
        factors.append(f"💰 **Boa liquidez (${liquidity:,.0f})** - adequada para uma exchange major")
    elif liquidity > 100000:
        factors.append(f"💰 **Liquidez moderada (${liquidity:,.0f})** - mínima recomendada para listing")
    else:
        factors.append(f"💰 **Liquidez baixa (${liquidity:,.0f})** - pode ser limitante")
    
    # Análise de Volume
    if volume_24h > 500000:
        factors.append(f"📈 **Volume muito forte (${volume_24h:,.0f}/24h)** - demonstra interesse orgânico significativo")
    elif volume_24h > 100000:
        factors.append(f"📈 **Volume sólido (${volume_24h:,.0f}/24h)** - trading consistente")
    elif volume_24h > 50000:
        factors.append(f"📈 **Volume moderado (${volume_24h:,.0f}/24h)** - aceitável para consideração")
    
    # Análise de Compra da Exchange
    if value_usd > 50000:
        factors.append(f"🏦 **Grande aquisição pela exchange (${value_usd:,.0f})** - posicionamento significativo")
    elif value_usd > 10000:
        factors.append(f"🏦 **Aquisição relevante (${value_usd:,.0f})** - interesse demonstrado")
    elif value_usd > 1000:
        factors.append(f"🏦 **Aquisição detectada (${value_usd:,.0f})** - presença na wallet")
    
    # Análise de Listagem em Outras Exchanges
    if listed_exchanges:
        other_exchanges = [ex for ex in listed_exchanges if ex != exchange]
        if other_exchanges:
            factors.append(f"🔗 **Já listado em {', '.join(other_exchanges)}** - precedente estabelecido para listing em {exchange}")
        else:
            factors.append(f"🆕 **Primeira deteção em exchange major** - potencial listing inaugural")
    else:
        factors.append(f"🆕 **Não listado em outras exchanges major** - oportunidade de listing exclusivo")
    
    # Análise de Pressão Compradora
    if txns_buys > 0 or txns_sells > 0:
        ratio = txns_buys / max(txns_sells, 1)
        if ratio > 2.0:
            factors.append(f"🎯 **Forte pressão compradora (rácio {ratio:.1f}:1)** - sentimento positivo do mercado")
        elif ratio > 1.2:
            factors.append(f"🎯 **Pressão compradora moderada (rácio {ratio:.1f}:1)** - mais compradores que vendedores")
        elif ratio < 0.8:
            factors.append(f"⚠️ **Pressão vendedora (rácio {ratio:.1f}:1)** - pode ser preocupante")
    
    # Análise de Concentração de Holders
    if holders_concentration > 0.20:
        factors.append(f"🚨 **Alta concentração de holders ({holders_concentration*100:.1f}%)** - risco de manipulação")
    elif holders_concentration > 0.10:
        factors.append(f"⚠️ **Concentração moderada de holders ({holders_concentration*100:.1f}%)** - merece atenção")
    else:
        factors.append(f"✅ **Baixa concentração de holders ({holders_concentration*100:.1f}%)** - distribuição saudável")
    
    # Conclusão IA
    if confidence_level == "muito alto":
        conclusion = f"🚨 **ALTA PROBABILIDADE** de listing iminente na {exchange}"
    elif confidence_level == "alto":
        conclusion = f"📈 **PROVÁVEL** listing na {exchange} nos próximos dias/semanas"
    else:
        conclusion = f"👀 **POTENCIAL** listing na {exchange} - merece monitorização"
    
    # Montar análise final
    analysis = f"""🎯 **{token} - Análise de Potencial Listing na {exchange}**

{' | '.join(factors)}

💡 **Conclusão IA:** {conclusion}

🔍 **Recomendação:** {'Monitorizar ativamente' if score > 50 else 'Manter em watchlist'}"""
    
    return analysis

# ===========================
# ANÁLISE DE TRANSACÇÃO
# ===========================
BLUECHIPS = {"USDC","USDT","SOL","BTC","ETH","WIF","BONK"}  # podes ajustar

def analyze_transaction(tx_data: Dict[str, Any], wallet_address: str, exchange_name: str) -> Optional[Dict[str, Any]]:
    try:
        if not tx_data or 'result' not in tx_data:
            return None
        result = tx_data['result']
        meta = result.get('meta', {}) or {}
        if meta.get('err'):
            return None

        # varrer balances pós-transação pertencentes à wallet monitorizada
        for balance in meta.get('postTokenBalances', []):
            if balance.get('owner') != wallet_address:
                continue

            amount = float(((balance.get('uiTokenAmount') or {}).get('uiAmount')) or 0.0)
            if amount <= 0:
                continue

            mint_address = balance.get('mint')
            if not mint_address:
                continue

            dex = get_dexscreener_data(mint_address)
            if not dex:
                continue

            p = parse_pair(dex)
            price = float(p["price_usd"] or 0.0)
            if price <= 0:
                continue

            value_usd = amount * price
            if value_usd <= 0:
                continue

            token_symbol = p["token_symbol"] or "UNKNOWN"
            if token_symbol.upper() in BLUECHIPS:
                continue

            # filtros mínimos
            liquidity = float(p["liquidity"] or 0.0)
            volume_24h = float(p["volume_24h"] or 0.0)
            if liquidity < 50_000:
                continue
            if volume_24h < 10_000:
                continue

            holders_concentration = float(p["holders_concentration"] or 0.0)
            if holders_concentration and holders_concentration > 0.20:
                continue

            # já listado na própria exchange?
            if is_token_listed_on_exchange(token_symbol, exchange_name):
                logger.info(f"⚠️ {token_symbol} já listado em {exchange_name} - ignorando")
                continue

            listed_elsewhere = get_listed_exchanges(
                token_symbol,
                exclude_exchange=EXCHANGE_NORMALIZE.get(exchange_name, exchange_name)
            )
            sig = (result.get('transaction') or {}).get('signatures', [None])[0]
            ts = result.get("blockTime", int(time.time()))
            special = wallet_address in SPECIAL_WALLETS.values()

            return {
                "exchange": exchange_name,
                "token": token_symbol,
                "token_address": mint_address,
                "amount": amount,
                "value_usd": value_usd,
                "price": price,
                "price_change_24h": p["price_change_24h"],
                "liquidity": liquidity,
                "volume_24h": volume_24h,
                "pair_url": p["pair_url"],
                "signature": sig,
                "timestamp": ts,
                "listed_exchanges": listed_elsewhere,
                "special": special,
                "txns_buys": p["txns_buys"],
                "txns_sells": p["txns_sells"],
                "holders_concentration": holders_concentration,
                "pair_created_ms": p["pair_created_ms"],
            }
        return None
    except Exception as e:
        logger.error(f"Erro na análise de transação: {e}")
        return None

# ===========================
# SUPABASE UPSERT
# ===========================
def save_transaction_supabase(alert_info: Dict[str, Any]) -> bool:
    payload = {
        "exchange": alert_info.get("exchange"),
        "token": alert_info.get("token"),
        "token_address": alert_info.get("token_address"),
        "signature": alert_info.get("signature"),
        "amount": float(alert_info.get("amount") or 0.0),
        "value_usd": float(alert_info.get("value_usd") or 0.0),
        "price": float(alert_info.get("price") or 0.0),
        "liquidity": float(alert_info.get("liquidity") or 0.0),
        "volume_24h": float(alert_info.get("volume_24h") or 0.0),
        "pair_url": alert_info.get("pair_url"),
        "listed_exchanges": alert_info.get("listed_exchanges", []),
        "special": bool(alert_info.get("special", False)),
        "ts": datetime.fromtimestamp(alert_info.get("timestamp", int(time.time())), tz=timezone.utc).isoformat(),
        # ML
        "score": float(alert_info.get("score") or 0.0),
        "listing_probability": float(alert_info.get("listing_probability") or 0.0),
        "confidence": float(alert_info.get("confidence") or 0.0),
        # métricas extra
        "txns_buys": int(alert_info.get("txns_buys") or 0),
        "txns_sells": int(alert_info.get("txns_sells") or 0),
        "holders_concentration": float(alert_info.get("holders_concentration") or 0.0),
        # NOVO: análise IA explicativa
        "ai_analysis": alert_info.get("ai_analysis"),
    }
    try:
        res = supabase.table("transacted_tokens").upsert(
            payload, on_conflict="token_address,signature"
        ).execute()
        return bool(getattr(res, "data", None))
    except Exception as e:
        logger.error(f"Exceção ao salvar transação no Supabase: {e}")
        return False

# ===========================
# MAIN
# ===========================
def main():
    logger.info("🚀 VIGIA SOLANA PRO 1.2 — INICIANDO (COM ANÁLISE IA)")
    load_listed_tokens_from_supabase(force=True)
    ai = CryptoAIAnalyzer()
    total_alerts = 0

    for exchange_name, wallet in EXCHANGE_WALLETS.items():
        logger.info(f"🔍 Analisando {exchange_name} ({wallet})...")
        txs = get_recent_signatures(wallet, hours=24, limit_per_page=100)
        logger.info(f"   ✅ {len(txs)} transações dentro da janela")

        for tx in txs:
            sig = tx.get("signature")
            if not sig:
                continue

            details = get_transaction_details(sig)
            if not details:
                continue

            alert = analyze_transaction(details, wallet, exchange_name)
            if not alert:
                continue

            # 🤖 Predição ML
            ml = ai.predict_listing_potential(alert, exchange_name, alert["token"])

            # Anexar campos ML
            alert["score"] = float(ml.get("score") or 0.0)
            alert["listing_probability"] = float(ml.get("listing_probability") or 0.0)
            alert["confidence"] = float(ml.get("confidence") or 0.0)
            
            # 🧠 GERAR ANÁLISE IA EXPLICATIVA (NOVO!)
            alert["ai_analysis"] = generate_ai_analysis(alert)

            # ✅ filtro principal
            if ml.get("is_new_token", True) and alert["score"] >= ML_SCORE_THRESHOLD:
                saved = save_transaction_supabase(alert)
                if saved:
                    logger.info(f"   🚨 POTENCIAL LISTING: {alert['token']} — Score {alert['score']:.1f}")
                    logger.info(f"   📝 Análise IA: {alert['ai_analysis'][:100]}...")
                    total_alerts += 1
                else:
                    logger.debug(f"   ℹ️ Não inserido (duplicado/erro) {alert['token']} — {alert.get('signature')}")
            else:
                logger.debug(
                    f"   ℹ️ Não passa ML/novo: {alert['token']} "
                    f"score={alert['score']:.1f} new={ml.get('is_new_token')}"
                )

            time.sleep(0.35)  # rate-limit por transação (ligeiro)

        # refresh do catálogo de listados ~a cada ~30min
        if time.time() - _LISTED_CACHE_TS > (CACHE_TTL / 2):
            load_listed_tokens_from_supabase(force=True)

        time.sleep(0.8)  # rate-limit entre wallets

    logger.info(f"🎯 Total de alertas gravados: {total_alerts}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Falha inesperada: {e}")
        raise