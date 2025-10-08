# vigia_solana_pro_supabase.py
import os
import time
import requests
import logging
import numpy as np
from supabase import create_client, Client
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta, timezone

# ---------------------------
# CONFIGURAÇÃO (edita conforme necessário)
# ---------------------------
TELEGRAM_BOT_TOKEN_SOL = os.environ.get("TELEGRAM_BOT_TOKEN_SOL", "7999197151:AAELAI64aNx2nVk-Uhp-20YAxrXlXbVFzjw")
TELEGRAM_CHAT_ID = "5239378332"
TELEGRAM_CHAT_ID_SOL = os.environ.get("TELEGRAM_CHAT_ID_SOL", "5239378332")

HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "0fd1b496-c250-459e-ba21-fa5a33caf055")
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Supabase: usa service_role para escrita (coloca a tua)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qynnajpvxnqcmkzrhpde.supabase.co")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Parâmetros
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
ALERT_MIN_VALUE = 10000  # valor mínimo em USD para considerar (não usado diretamente; podes ativar se quiseres)
ML_SCORE_THRESHOLD = 50  # só envia alertas ML com score >= este
CACHE_TTL = 60 * 60      # 1h para cache dos tokens listados / supported
REQUEST_TIMEOUT = 12

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VigiaSolanaPro")

# ---------------------------
# WALLETS / SPECIAL WALLETS
# ---------------------------
EXCHANGE_WALLETS = {
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

SPECIAL_WALLETS = {
    "Alameda Research": "MJKqp326RZCHnAAbew9MDdui3iCKWco7fsK9sVuZTX2",
    "Suspicious Early Mover": "GkPtg9Lt38syNpdBGsNJu4YMkLi5wFXq3PM8PQhxT8ry"
}

# ---------------------------
# Cache local para listed tokens carregados do Supabase
# ---------------------------
LISTED_TOKENS = {}  # {'Binance': ['SOL','USDC'], ...}
_LISTED_CACHE_TS = 0

def load_listed_tokens_from_supabase(force: bool = False):
    """Carrega exchange_tokens do Supabase (com cache)."""
    global LISTED_TOKENS, _LISTED_CACHE_TS
    now = time.time()
    if not force and (now - _LISTED_CACHE_TS) < CACHE_TTL and LISTED_TOKENS:
        return LISTED_TOKENS
    try:
        resp = supabase.table("exchange_tokens").select("exchange,token").execute()
        data = getattr(resp, "data", None)
        if not data:
            logger.info("✅ Tokens carregados do Supabase: 0 tokens (fallback ou vazio)")
            LISTED_TOKENS = {}
            _LISTED_CACHE_TS = now
            return LISTED_TOKENS
        temp = {}
        count = 0
        for row in data:
            ex = (row.get("exchange") or "").strip()
            tok = (row.get("token") or "").strip()
            if not ex or not tok:
                continue
            temp.setdefault(ex, []).append(tok)
            count += 1
        LISTED_TOKENS = temp
        _LISTED_CACHE_TS = now
        logger.info(f"✅ Tokens carregados do Supabase: {count} tokens em {len(temp)} exchanges")
        return LISTED_TOKENS
    except Exception as e:
        logger.warning(f"❌ Erro ao carregar tokens do Supabase: {e} — fallback para vazio")
        LISTED_TOKENS = {}
        _LISTED_CACHE_TS = now
        return LISTED_TOKENS

# mapa de normalização de nomes de exchanges (ex.: "Binance 1" -> "Binance")
EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
    "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
    "Bybit": "Bybit", "Gate.io": "Gate.io", "Bitget": "Bitget",
    "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
    "OKX": "OKX", "MEXC": "MEXC"
}

def is_token_listed_on_exchange(token_symbol: str, exchange_name: str) -> bool:
    """Verifica se token já existe na exchange específica (usando cache LISTED_TOKENS)."""
    ex = EXCHANGE_NORMALIZE.get(exchange_name, exchange_name)
    tokens = LISTED_TOKENS.get(ex, [])
    return token_symbol.upper() in [t.upper() for t in tokens]

def get_listed_exchanges(token_symbol: str, exclude_exchange: str | None = None):
    """Devolve lista de exchanges onde o token aparece (exceto exclude)."""
    token_upper = token_symbol.upper()
    exchanges = []
    for ex, tokens in LISTED_TOKENS.items():
        if exclude_exchange and ex.lower() == exclude_exchange.lower():
            continue
        for t in tokens:
            if t and t.upper() == token_upper:
                exchanges.append(ex)
                break
    return exchanges

# ---------------------------
# Funções utilitárias (Helius, Dexscreener, Telegram)
# ---------------------------
def get_recent_transactions(wallet_address: str, hours: int = 24):
    try:
        # timezone-aware UTC
        start_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-signatures",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 50}]
        }
        r = requests.post(HELIUS_URL, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            logger.warning(f"Helius returned {r.status_code} for {wallet_address}")
            return []
        j = r.json()
        if not j.get("result"):
            return []
        txs = []
        for tx in j["result"]:
            bt = tx.get("blockTime")
            if bt and bt >= start_ts:
                txs.append(tx)
        return txs
    except Exception as e:
        logger.error(f"Erro get_recent_transactions: {e}")
        return []

def get_transaction_details(signature: str):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-details",
            "method": "getTransaction",
            "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        }
        r = requests.post(HELIUS_URL, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        logger.error(f"Erro get_transaction_details {signature}: {e}")
        return None

def get_dexscreener_data(token_address: str):
    try:
        r = requests.get(f"{DEXSCREENER_API}{token_address}", timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        j = r.json()
        if j.get("pairs") and len(j["pairs"]) > 0:
            return j["pairs"][0]
        return None
    except Exception as e:
        logger.debug(f"Dexscreener error for {token_address}: {e}")
        return None

def send_telegram_alert(message: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_SOL}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_SOL,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            logger.error(f"Erro Telegram {r.status_code}: {r.text}")
            return False
        j = r.json()
        if not j.get("ok"):
            logger.error(f"Telegram não ok: {j}")
            return False
        return True
    except Exception as e:
        logger.error(f"Exceção Telegram: {e}")
        return False

# ---------------------------
# ML Analyzer (features expandidas)
# ---------------------------
MODEL_PATH = "vigia_ml_model.pkl"
SCALER_PATH = "vigia_ml_scaler.pkl"

class CryptoAIAnalyzer:
    def __init__(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                logger.info("✅ Modelo carregado do disco.")
                return
            except Exception as e:
                logger.warning(f"Falha a carregar modelo do disco: {e} — retrain")
        self.model, self.scaler = self._create_and_train_model()
        try:
            joblib.dump(self.model, MODEL_PATH)
            joblib.dump(self.scaler, SCALER_PATH)
        except Exception:
            pass

    def _create_and_train_model(self):
        """
        Cria e treina o modelo com features expandidas.
        Features: [valor, liquidez, volume, variação, market_cap_rank,
                   is_new_token, buys/sells_ratio, holders_concentration]
        """
        try:
            X_train = np.array([
                [50000, 1_000_000, 500_000, 25, 100, 1, 2.0, 0.10],  # Novo bom
                [30000,   800_000, 400_000, 15, 150, 1, 1.5, 0.15],  # Novo médio
                [10000,   200_000,  80_000,  5, 200, 1, 1.2, 0.25],  # Novo arriscado
                [ 5000,    50_000,  20_000, -5, 300, 1, 0.5, 0.40],  # Honeypot provável
                [20000, 2_000_000, 1_000_000, -2, 50, 0, 1.0, 0.05], # Estabelecido em queda
                [15000, 1_500_000,   600_000,  8, 80, 0, 1.3, 0.08], # Estável
                [70000, 5_000_000, 2_500_000, 30, 20, 0, 1.4, 0.07], # Blue chip
                [ 2000,    30_000,   10_000,-15,400, 1, 0.3, 0.60],  # Scam (1 holder)
                [12000,   100_000,   50_000, 12,250, 1, 2.5, 0.10],  # Novo hype
                [25000,   700_000,  300_000, 20,120, 1, 2.0, 0.12],  # Novo promissor
            ])
            y_train = np.array([1, 1, 0, 0, 0, 0, 1, 0, 1, 1])

            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                class_weight="balanced"
            )
            model.fit(X_train, y_train)

            scaler = StandardScaler()
            scaler.fit(X_train)

            logger.info("✅ Modelo ML treinado com features expandidas.")
            return model, scaler

        except Exception as e:
            logger.error(f"Erro treino ML: {e}")

            class Dummy:
                def predict_proba(self, X):  # fallback
                    return np.array([[0.3, 0.7]])

            class DS:
                def transform(self, X):
                    return X

            return Dummy(), DS()

    def _extract_features(self, token_data: dict, is_new_token: bool = True):
        """Extrai features expandidas para o modelo."""
        liquidity = token_data.get('liquidity', 0) or 0
        volume_24h = token_data.get('volume_24h', 0) or 0
        price_change = token_data.get('price_change_24h', 0) or 0
        value_usd = token_data.get('value_usd', 0) or 0

        # rank aproximado pela liquidez
        if liquidity > 5_000_000:
            market_cap_rank = 50
        elif liquidity > 1_000_000:
            market_cap_rank = 100
        elif liquidity > 500_000:
            market_cap_rank = 200
        else:
            market_cap_rank = 500

        # buys/sells ratio (fallback 1.0)
        buys = token_data.get('txns_buys', 1)
        sells = token_data.get('txns_sells', 1)
        buys_sells_ratio = (buys / max(sells, 1))

        # concentração de holders (se existir)
        holders_concentration = token_data.get('holders_concentration', 0.1)

        features = np.array([
            value_usd / 100000.0,
            liquidity / 1_000_000.0,
            volume_24h / 500_000.0,
            price_change / 100.0,
            market_cap_rank / 1000.0,
            1 if is_new_token else 0,
            buys_sells_ratio,
            holders_concentration
        ]).reshape(1, -1)

        return features

    def predict_listing_potential(self, token_data: dict, exchange_name: str, token_symbol: str):
        """Devolve dict com score, probabilidade, confiança e se é novo token."""
        try:
            is_new = not is_token_listed_on_exchange(token_symbol, exchange_name)
            X = self._extract_features(token_data, is_new)
            Xs = self.scaler.transform(X)
            proba = self.model.predict_proba(Xs)[0]  # [p0, p1]
            p1 = float(proba[1]) * 100.0
            conf = float(max(proba)) * 100.0
            return {
                'listing_probability': p1,
                'score': p1,
                'confidence': conf,
                'is_new_token': is_new
            }
        except Exception as e:
            logger.error(f"Erro ML predict: {e}")
            return {
                'listing_probability': 70.0,
                'score': 70.0,
                'confidence': 50.0,
                'is_new_token': True
            }

# ---------------------------
# Análise de transações
# ---------------------------
def analyze_transaction(tx_data: dict, wallet_address: str, exchange_name: str):
    """Analisa uma transação e aplica filtros anti-scam antes de gerar alerta."""
    try:
        if not tx_data or 'result' not in tx_data:
            return None

        result = tx_data['result']
        meta = result.get('meta', {})
        if meta.get('err'):
            return None

        for balance in meta.get('postTokenBalances', []):
            if balance.get('owner') != wallet_address:
                continue

            amount = balance.get('uiTokenAmount', {}).get('uiAmount', 0)
            if not amount or amount <= 0:
                continue

            mint_address = balance.get('mint')
            dex = get_dexscreener_data(mint_address)
            if not dex or not isinstance(dex, dict):
                continue

            # Preço
            try:
                price = float(dex.get('priceUsd', 0) or 0)
            except Exception:
                price = 0
            if price <= 0:
                continue

            value_usd = amount * price
            if value_usd <= 0:
                continue

            token_symbol = (dex.get('baseToken') or {}).get('symbol', 'UNKNOWN')
            if token_symbol in ["USDC", "USDT", "SOL", "BTC", "ETH"]:
                continue

            # Dados extra
            liquidity = (dex.get('liquidity') or {}).get('usd', 0) or 0
            volume_24h = (dex.get('volume') or {}).get('h24', 0) or 0

            # --- Filtros anti-scam ---
            if liquidity < 50_000:   # liquidez mínima $50k
                continue
            if volume_24h < 10_000:  # volume mínimo $10k
                continue

            # holders concentration (se vier)
            holders_concentration = 0.0
            try:
                holders_concentration = (dex.get("topHolders", {}) or {}).get("concentration", 0.0) or 0.0
            except Exception:
                holders_concentration = 0.0

            if holders_concentration and holders_concentration > 0.20:  # máx 20%
                continue

            # verificar se já listado na própria exchange
            if is_token_listed_on_exchange(token_symbol, exchange_name):
                logger.info(f"⚠️ {token_symbol} já listado em {exchange_name} - ignorando")
                continue

            listed = get_listed_exchanges(
                token_symbol,
                exclude_exchange=EXCHANGE_NORMALIZE.get(exchange_name, exchange_name)
            )
            sig = result.get('transaction', {}).get('signatures', [None])[0]

            return {
                "exchange": exchange_name,
                "token": token_symbol,
                "token_address": mint_address,
                "amount": amount,
                "value_usd": value_usd,
                "price": price,
                "price_change_24h": (dex.get("priceChange", {}) or {}).get("h24") if isinstance(dex.get("priceChange"), dict)
                                    else dex.get("priceChange"),
                "liquidity": liquidity,
                "volume_24h": volume_24h,
                "pair_url": dex.get("url", ""),
                "signature": sig,
                "timestamp": result.get("blockTime", int(time.time())),
                "listed_exchanges": listed,
                "special": wallet_address in SPECIAL_WALLETS.values(),
                "txns_buys": (dex.get("txns", {}) or {}).get("h24", {}).get("buys", 0),
                "txns_sells": (dex.get("txns", {}) or {}).get("h24", {}).get("sells", 0),
                "holders_concentration": holders_concentration,
            }

        return None

    except Exception as e:
        logger.error(f"Erro na análise de transação: {e}")
        return None

def format_listing_alert(alert_info: dict, ml_prediction: dict) -> str:
    score = ml_prediction.get('score', 0)
    if score >= 80:
        emoji = "🚀💎"; urgency = "ALTA PRIORIDADE"
    elif score >= 65:
        emoji = "🔥✨"; urgency = "POTENCIAL"
    elif score >= 50:
        emoji = "⚠️📈"; urgency = "MONITORAR"
    else:
        emoji = "🔻👀"; urgency = "BAIXO POTENCIAL"

    message = f"{emoji} <b>POTENCIAL NOVO LISTING DETETADO!</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    message += f"💰 <b>Valor Recebido:</b> ${alert_info['value_usd']:,.2f}\n"
    message += f"📊 <b>Preço Atual:</b> ${alert_info['price']:.8f}\n"
    if alert_info.get('price_change_24h') is not None:
        try:
            pc = float(alert_info['price_change_24h'])
            change_emoji = "📈" if pc >= 0 else "📉"
            message += f"{change_emoji} <b>24h Change:</b> {pc:.2f}%\n"
        except Exception:
            pass
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.2f}\n"
    message += f"📈 <b>Volume 24h:</b> ${alert_info['volume_24h']:,.2f}\n\n"
    message += "🤖 <b>ANÁLISE DE IA</b>\n"
    message += f"⭐ Score: {ml_prediction['score']:.1f}/100\n"
    message += f"🎯 Probabilidade: {ml_prediction['listing_probability']:.1f}%\n"
    message += f"📈 Confiança: {ml_prediction['confidence']:.1f}%\n"
    message += f"🚨 Urgência: {urgency}\n\n"
    message += f"🔗 <a href='{alert_info['pair_url']}'>DexScreener</a>\n"
    message += f"🔍 <a href='https://solscan.io/token/{alert_info['token_address']}'>Solscan</a>\n\n"
    message += "<i>🤖 Sistema de deteção de novos listings</i>"
    return message

# ---------------------------
# Salvar transação no Supabase (upsert + índice único recomendado)
# ---------------------------
def save_transaction_supabase(alert_info: dict) -> bool:
    payload = {
        "exchange": alert_info.get("exchange"),
        "token": alert_info.get("token"),
        "token_address": alert_info.get("token_address"),
        "signature": alert_info.get("signature"),
        "amount": alert_info.get("amount"),
        "value_usd": alert_info.get("value_usd"),
        "price": alert_info.get("price"),
        "liquidity": alert_info.get("liquidity"),
        "pair_url": alert_info.get("pair_url"),
        "listed_exchanges": alert_info.get("listed_exchanges", []),
        "special": alert_info.get("special", False),
        "ts": datetime.fromtimestamp(alert_info.get("timestamp", int(time.time()))).isoformat(),
        # 👇 novos
        "score": float(alert_info.get("score") or 0.0),
        "txns_buys": int(alert_info.get("txns_buys") or 0),
        "txns_sells": int(alert_info.get("txns_sells") or 0),
        "holders_concentration": float(alert_info.get("holders_concentration") or 0.0),
    }

    try:
        # Requer UNIQUE(token_address, signature) para funcionar como esperado:
        #   ALTER TABLE public.transacted_tokens
        #   ADD CONSTRAINT transacted_tokens_token_sig_uniq UNIQUE (token_address, signature);
        res = supabase.table("transacted_tokens").upsert(
            payload, on_conflict="token_address,signature"
        ).execute()
        return bool(getattr(res, "data", None))
    except Exception as e:
        logger.error(f"Exceção ao salvar transação no Supabase: {e}")
        return False

# ---------------------------
# MAIN
# ---------------------------
def main():
    logger.info("🚀 VIGIA SOLANA PRO - INICIANDO")
    load_listed_tokens_from_supabase(force=True)  # catálogo de tokens já listados
    ai = CryptoAIAnalyzer()
    total_alerts = 0

    for exchange_name, wallet in EXCHANGE_WALLETS.items():
        logger.info(f"🔍 Analisando {exchange_name} ({wallet})...")
        txs = get_recent_transactions(wallet, hours=24)
        logger.info(f"   ✅ {len(txs)} transações encontradas")

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

            # 👉 anexar campos de ML ao registo ANTES de gravar
            alert["score"] = float(ml.get("score") or 0.0)
            alert["listing_probability"] = float(ml.get("listing_probability") or 0.0)
            alert["confidence"] = float(ml.get("confidence") or 0.0)

            # ✅ filtro principal: só novos (segundo ML) e com score mínimo
            if ml.get("is_new_token", True) and ml.get("score", 0) >= ML_SCORE_THRESHOLD:
                saved = save_transaction_supabase(alert)

                if saved:
                    # envia alerta (opcional)
                    msg = format_listing_alert(alert, ml)
                    if send_telegram_alert(msg):
                        logger.info(f"   🚨 POTENCIAL LISTING: {alert['token']} - Score {alert['score']:.1f}")
                        total_alerts += 1
                else:
                    # duplicado/erro ao inserir — não reenviar
                    logger.debug(f"   ℹ️  Não inserido (duplicado/erro) {alert['token']} — {alert.get('signature')}")

            else:
                logger.debug(
                    f"   ℹ️  Não passa ML/novo: {alert['token']} "
                    f"score={ml.get('score'):.1f} new={ml.get('is_new_token')}"
                )

            time.sleep(0.5)  # rate-limit entre transações

        # refresh do catálogo (meia-vida do cache)
        if time.time() - _LISTED_CACHE_TS > (CACHE_TTL / 2):
            load_listed_tokens_from_supabase(force=True)

        time.sleep(1)  # rate-limit entre exchanges

    logger.info(f"🎯 Total de alertas enviados: {total_alerts}")

# Guardião de arranque
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Falha inesperada: {e}")
        raise
