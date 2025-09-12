# vigia_solana_pro_trained.py - VERSÃO COM APIs DE MÚLTIPLAS CORRETORAS
import requests
import time
import re
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging

# ============================
# CONFIGURAÇÃO
# ============================
# Use variáveis de ambiente ou valores padrão
TELEGRAM_BOT_TOKEN_SOL = os.environ.get("TELEGRAM_BOT_TOKEN_SOL", "8350004696:AAGVXDH0hRr9S4EPsuQdwDBrG0Pa1m3i_-U")
TELEGRAM_CHAT_ID_SOL = os.environ.get("TELEGRAM_CHAT_ID_SOL", "5239378332")
HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "0fd1b496-c250-459e-ba21-fa5a33caf055")

HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VigiaSolana")

# Wallets Ativas (exemplo - adiciona as tuas wallets reais)
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
    "FTX": "2npR8J6kKgrY2T6VioeS5pbgjRtx6eXG3wJ8kYF8tX9L",
    "MEXC": "H7gyjxzXm7fQ6pfx9WkQqJk4DfjRk7Vc1nG5VcJqJ5qj",
}

# Cache para tokens suportados por exchange
SUPPORTED_TOKENS_CACHE = {}
CACHE_DURATION = 3600  # 1 hora em segundos

# ============================
# VERIFICAÇÃO DE TOKENS SUPORTADOS (TODAS AS CORRETORAS)
# ============================
def get_supported_tokens(exchange_name):
    """Obtém lista de tokens suportados por cada exchange"""
    global SUPPORTED_TOKENS_CACHE
    
    current_time = time.time()
    
    # Verificar cache
    if (exchange_name in SUPPORTED_TOKENS_CACHE and 
        current_time - SUPPORTED_TOKENS_CACHE[exchange_name]['timestamp'] < CACHE_DURATION):
        return SUPPORTED_TOKENS_CACHE[exchange_name]['tokens']
    
    tokens = set()
    
    try:
        if "Binance" in exchange_name:
            # API da Binance
            response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
            if response.status_code == 200:
                data = response.json()
                for symbol in data.get('symbols', []):
                    if symbol.get('status') == 'TRADING':
                        base_asset = symbol.get('baseAsset')
                        if base_asset:
                            tokens.add(base_asset.upper())
                logger.info(f"✅ Binance: {len(tokens)} tokens suportados")
        
        elif "Coinbase" in exchange_name:
            # API da Coinbase
            try:
                response = requests.get("https://api.exchange.coinbase.com/products", timeout=10)
                if response.status_code == 200:
                    products = response.json()
                    for product in products:
                        if product.get('status') == 'online':
                            base_currency = product.get('base_currency')
                            if base_currency:
                                tokens.add(base_currency.upper())
                    logger.info(f"✅ Coinbase: {len(tokens)} tokens suportados")
            except Exception as e:
                logger.warning(f"Coinbase API falhou, usando fallback: {e}")
                # Fallback para lista conhecida
                coinbase_tokens = {"BTC", "ETH", "SOL", "USDC", "USDT", "ADA", "MATIC", "DOGE", "DOT", 
                                 "AVAX", "LTC", "LINK", "ATOM", "XLM", "ETC", "FIL", "ALGO", "BCH",
                                 "NEAR", "VET", "ICP", "EOS", "XTZ", "AAVE", "MKR", "COMP", "YFI",
                                 "SNX", "UNI", "SUSHI", "CRV", "1INCH", "REN", "BAT", "ZRX", "OMG"}
                tokens.update(coinbase_tokens)
        
        elif "Kraken" in exchange_name:
            # API da Kraken
            try:
                response = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for pair, info in data.get('result', {}).items():
                        if 'wsname' in info:
                            base_asset = info['wsname'].split('/')[0]
                            tokens.add(base_asset.upper())
                    logger.info(f"✅ Kraken: {len(tokens)} tokens suportados")
            except Exception as e:
                logger.warning(f"Kraken API falhou, usando fallback: {e}")
                kraken_tokens = {"BTC", "ETH", "SOL", "USDC", "USDT", "ADA", "DOT", "AVAX", "LTC", 
                               "LINK", "ATOM", "XLM", "ETC", "FIL", "ALGO", "BCH", "NEAR", "ICP"}
                tokens.update(kraken_tokens)
        
        elif "Bybit" in exchange_name:
            # API da Bybit
            try:
                response = requests.get("https://api.bybit.com/v5/market/instruments-info?category=spot", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for instrument in data.get('result', {}).get('list', []):
                        if instrument.get('status') == 'Trading':
                            base_coin = instrument.get('baseCoin')
                            if base_coin:
                                tokens.add(base_coin.upper())
                    logger.info(f"✅ Bybit: {len(tokens)} tokens suportados")
            except Exception as e:
                logger.warning(f"Bybit API falhou, usando fallback: {e}")
                bybit_tokens = {"BTC", "ETH", "SOL", "USDC", "USDT", "XRP", "ADA", "DOGE", "MATIC", 
                              "DOT", "AVAX", "LTC", "LINK", "ATOM", "XLM", "ETC", "FIL", "ALGO"}
                tokens.update(bybit_tokens)
        
        elif "OKX" in exchange_name:
            # API da OKX
            try:
                response = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SPOT", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for instrument in data.get('data', []):
                        if instrument.get('state') == 'live':
                            base_ccy = instrument.get('baseCcy')
                            if base_ccy:
                                tokens.add(base_ccy.upper())
                    logger.info(f"✅ OKX: {len(tokens)} tokens suportados")
            except Exception as e:
                logger.warning(f"OKX API falhou, usando fallback: {e}")
                okx_tokens = {"BTC", "ETH", "SOL", "USDC", "USDT", "XRP", "ADA", "DOGE", "MATIC", 
                            "DOT", "AVAX", "LTC", "LINK", "ATOM", "XLM", "ETC", "FIL", "ALGO"}
                tokens.update(okx_tokens)
        
        # Adicionar tokens comuns a todas as exchanges
        common_tokens = {"SOL", "BTC", "ETH", "USDC", "USDT"}
        tokens.update(common_tokens)
    
    except Exception as e:
        logger.error(f"❌ Erro ao obter tokens suportados para {exchange_name}: {e}")
        # Fallback para lista básica em caso de erro
        tokens = {"SOL", "BTC", "ETH", "USDC", "USDT"}
    
    # Atualizar cache
    SUPPORTED_TOKENS_CACHE[exchange_name] = {
        'tokens': tokens,
        'timestamp': current_time
    }
    
    return tokens

def is_token_supported(exchange_name, token_symbol):
    """Verifica se um token é suportado por uma exchange"""
    supported_tokens = get_supported_tokens(exchange_name)
    
    # Normalizar símbolo do token
    normalized_symbol = token_symbol.upper()
    
    # Remover possíveis prefixos/sufixos comuns
    if normalized_symbol.startswith('W'):  # Wrapped tokens
        normalized_symbol = normalized_symbol[1:]
    if normalized_symbol.endswith('BULL') or normalized_symbol.endswith('BEAR'):
        normalized_symbol = normalized_symbol[:-4]
    
    return normalized_symbol in supported_tokens

# ============================
# SISTEMA DE IA COM MODELO TREINADO
# ============================
class CryptoAIAnalyzer:
    def __init__(self):
        self.model, self.scaler = self.create_and_train_model()
        
    def create_and_train_model(self):
        """Cria e treina um novo modelo de ML"""
        try:
            # Dados de treino mais realistas - FOCO EM NOVOS LISTINGS
            X_train = np.array([
                # [value, liquidity, volume, price_change_24h, market_cap_rank, is_new_token]
                [50000, 1000000, 500000, 25, 100, 1],    # Novo token promissor
                [30000, 500000, 300000, 20, 150, 1],     # Novo token bom
                [10000, 200000, 100000, 15, 200, 1],     # Novo token médio
                [5000, 100000, 50000, 10, 300, 1],       # Novo token regular
                [20000, 800000, 400000, -5, 50, 0],      # Token estabelecido em queda
                [15000, 600000, 300000, 5, 80, 0],       # Token estabelecido estável
                [8000, 300000, 150000, 12, 120, 0],      # Token estabelecido subindo
                [2000, 50000, 20000, -10, 400, 1],       # Novo token ruim
                [1000, 20000, 10000, -15, 500, 1],       # Novo token muito ruim
                [70000, 2000000, 1000000, 30, 20, 1],    # Novo token excelente
            ])
            
            # Labels (1 = potencial novo listing, 0 = não é novo listing)
            y_train = np.array([1, 1, 1, 1, 0, 0, 0, 1, 1, 1])
            
            # Treinar modelo
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # Treinar scaler com os mesmos dados
            scaler = StandardScaler()
            scaler.fit(X_train)
            
            logger.info("✅ Modelo de ML treinado com sucesso!")
            return model, scaler
            
        except Exception as e:
            logger.error(f"❌ Erro ao treinar modelo: {e}")
            return self.create_dummy_model()
    
    def create_dummy_model(self):
        """Modelo fallback simples"""
        class DummyModel:
            def predict_proba(self, X):
                # Retorna probabilidade alta para novos tokens
                return np.array([[0.2, 0.8]])  # [prob_nao_novo, prob_novo]
                
        class DummyScaler:
            def transform(self, X):
                return X
                
        return DummyModel(), DummyScaler()
    
    def extract_features(self, token_data, is_new_token=True):
        """Extrai features para o modelo ML"""
        # Calcular rank de market cap aproximado
        liquidity = token_data.get('liquidity', 0)
        if liquidity > 5000000:  # > $5M
            market_cap_rank = 50
        elif liquidity > 1000000:  # > $1M
            market_cap_rank = 100
        elif liquidity > 500000:   # > $500K
            market_cap_rank = 200
        else:
            market_cap_rank = 500
        
        features = [
            token_data['value_usd'] / 100000,      # Valor normalizado
            token_data['liquidity'] / 1000000,     # Liquidez normalizada  
            token_data['volume_24h'] / 500000,     # Volume normalizado
            token_data.get('price_change_24h', 0) / 100,  # Variação de preço
            market_cap_rank / 1000,                # Rank de market cap
            1 if is_new_token else 0               # É novo token?
        ]
        return np.array(features).reshape(1, -1)
    
    def predict_listing_potential(self, token_data, exchange_name, token_symbol):
        """Preve potencial de novo listing usando ML"""
        try:
            # Verificar se é um novo token (não suportado pela exchange)
            is_new_token = not is_token_supported(exchange_name, token_symbol)
            
            features = self.extract_features(token_data, is_new_token)
            features_scaled = self.scaler.transform(features)
            
            prediction = self.model.predict_proba(features_scaled)[0]
            
            return {
                'listing_probability': prediction[1] * 100,  # Probabilidade de ser bom novo listing
                'score': prediction[1] * 100,
                'confidence': np.max(prediction) * 100,
                'is_new_token': is_new_token
            }
            
        except Exception as e:
            logger.error(f"❌ Erro predição ML: {e}")
            return {'listing_probability': 70, 'score': 70, 'confidence': 50, 'is_new_token': True}

# ============================
# SISTEMA DE ANÁLISE DE TRANSACÇÕES
# ============================
def get_transaction_details(signature):
    """Obtém detalhes de transação"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-details",
            "method": "getTransaction",
            "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        }
        response = requests.post(HELIUS_URL, json=payload, timeout=15)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"Erro ao obter detalhes da transação {signature}: {e}")
        return None

def get_dexscreener_data(token_address):
    """Obtém dados do DexScreener"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                return data['pairs'][0]
        return None
    except Exception as e:
        logger.error(f"Erro ao obter dados DexScreener para {token_address}: {e}")
        return None

def get_recent_transactions(wallet_address, hours=24):
    """Obtém transações recentes"""
    try:
        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-signatures",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 50}]
        }
        
        response = requests.post(HELIUS_URL, json=payload, timeout=15)
        if response.status_code != 200:
            logger.error(f"Erro HTTP {response.status_code} ao buscar transações")
            return []

        data = response.json()
        if "error" in data or not data.get('result'):
            logger.warning(f"Resposta sem resultados para {wallet_address}")
            return []

        # Corrigir o erro de comparação com None
        valid_transactions = []
        for tx in data['result']:
            block_time = tx.get('blockTime', 0)
            if block_time is not None and block_time >= start_timestamp:
                valid_transactions.append(tx)
                
        return valid_transactions

    except Exception as e:
        logger.error(f"Erro ao buscar transações: {e}")
        return []

def send_telegram_alert(message):
    """Envia alerta para Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_SOL}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_SOL,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            logger.error(f"Erro ao enviar mensagem Telegram: {response.status_code}")
            return False
        return True
    except Exception as e:
        logger.error(f"Exceção ao enviar para Telegram: {e}")
        return False

def format_listing_alert(alert_info, ml_prediction):
    """Formata alerta para potenciais novos listings"""
    score = ml_prediction['score']
    
    if score >= 80:
        emoji = "🚀💎"
        urgency = "ALTA PRIORIDADE"
    elif score >= 65:
        emoji = "🔥✨"
        urgency = "POTENCIAL"
    elif score >= 50:
        emoji = "⚠️📈"
        urgency = "MONITORAR"
    else:
        emoji = "🔻👀"
        urgency = "BAIXO POTENCIAL"
    
    message = f"{emoji} <b>POTENCIAL NOVO LISTING DETETADO!</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    message += f"💰 <b>Valor Recebido:</b> ${alert_info['value_usd']:,.2f}\n"
    message += f"📊 <b>Preço Atual:</b> ${alert_info['price']:.8f}\n"
    
    if 'price_change_24h' in alert_info:
        change_emoji = "📈" if alert_info['price_change_24h'] >= 0 else "📉"
        message += f"{change_emoji} <b>24h Change:</b> {alert_info['price_change_24h']:.2f}%\n"
    
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.2f}\n"
    message += f"📈 <b>Volume 24h:</b> ${alert_info['volume_24h']:,.2f}\n"
    
    message += f"\n🤖 <b>ANÁLISE DE IA:</b>\n"
    message += f"⭐ <b>Score Listing:</b> {score:.1f}/100\n"
    message += f"🎯 <b>Prob. Listing:</b> {ml_prediction['listing_probability']:.1f}%\n"
    message += f"📈 <b>Confiança:</b> {ml_prediction['confidence']:.1f}%\n"
    message += f"🚨 <b>Urgência:</b> {urgency}\n\n"
    
    message += f"🔗 <a href='{alert_info['pair_url']}'>DexScreener</a>\n"
    message += f"🔍 <a href='https://solscan.io/token/{alert_info['token_address']}'>Solscan</a>\n\n"
    
    message += f"<i>🤖 Sistema de deteção de novos listings</i>"
    
    return message

def analyze_transaction(tx_data, wallet_address, exchange_name):
    """Análise básica da transação"""
    try:
        if not tx_data or 'result' not in tx_data:
            return None
            
        result = tx_data['result']
        meta = result.get('meta', {})
        
        if meta.get('err'):
            return None
        
        for balance in meta.get('postTokenBalances', []):
            if (balance.get('owner') == wallet_address and 
                balance.get('uiTokenAmount', {}).get('uiAmount', 0) > 0):
                
                mint_address = balance.get('mint')
                amount = balance['uiTokenAmount']['uiAmount']
                
                dex_data = get_dexscreener_data(mint_address)
                if not dex_data or not dex_data.get('priceUsd'):
                    continue
                
                price = float(dex_data['priceUsd'])
                value_usd = amount * price
                
                token_symbol = dex_data.get('baseToken', {}).get('symbol', 'UNKNOWN')
                
                # Ignorar stablecoins e tokens principais
                if token_symbol in ["USDC", "USDT", "SOL", "BTC", "ETH"]:
                    continue
                
                # Só alertar para transações significativas
                if value_usd >= 10000:  # Reduzido para $10K para apanhar mais potenciais
                    # Calcular variação de preço se disponível
                    price_change = dex_data.get('priceChange', {}).get('h24', 0)
                    if isinstance(price_change, dict):
                        price_change = price_change.get('percentage', 0)
                    
                    return {
                        "exchange": exchange_name,
                        "token": token_symbol,
                        "token_address": mint_address,
                        "amount": amount,
                        "value_usd": value_usd,
                        "price": price,
                        "price_change_24h": price_change,
                        "liquidity": dex_data.get('liquidity', {}).get('usd', 0),
                        "volume_24h": dex_data.get('volume', {}).get('h24', 0),
                        "pair_url": dex_data.get('url', ''),
                        "timestamp": result.get('blockTime', int(time.time()))
                    }
                    
        return None
        
    except Exception as e:
        logger.error(f"Erro na análise de transação: {e}")
        return None

# ============================
# PROGRAMA PRINCIPAL
# ============================
def main():
    logger.info("🚀 VIGIA SOLANA PRO - DETETOR DE NOVOS LISTINGS")
    logger.info("💎 IA especializada em detetar tokens não listados")
    logger.info("=" * 60)
    
    # Pré-carregar tokens suportados
    for exchange_name in EXCHANGE_WALLETS.keys():
        get_supported_tokens(exchange_name)
        time.sleep(1)  # Rate limiting
    
    # Inicializar IA
    ai_analyzer = CryptoAIAnalyzer()
    total_alerts = 0
    
    for exchange_name, wallet_address in EXCHANGE_WALLETS.items():
        logger.info(f"🔍 Analisando {exchange_name}...")
        
        transactions = get_recent_transactions(wallet_address, hours=24)
        
        if not transactions:
            logger.info(f"   ℹ️  Nenhuma transação recente")
            continue
            
        logger.info(f"   ✅ {len(transactions)} transações para analisar")
        
        for tx in transactions:
            signature = tx['signature']
            tx_details = get_transaction_details(signature)
            
            if not tx_details:
                continue
            
            # Análise básica da transação
            alert_info = analyze_transaction(tx_details, wallet_address, exchange_name)
            if not alert_info:
                continue
            
            # 🤖 PREDIÇÃO COM MACHINE LEARNING - FOCO EM NOVOS LISTINGS
            ml_prediction = ai_analyzer.predict_listing_potential(
                alert_info, exchange_name, alert_info['token']
            )
            
            # 📊 FILTRAR POR SCORE MÍNIMO - SÓ ALERTAR PARA POTENCIAIS NOVOS LISTINGS
            if ml_prediction['score'] >= 50 and ml_prediction['is_new_token']:
                message = format_listing_alert(alert_info, ml_prediction)
                
                if send_telegram_alert(message):
                    logger.info(f"   🚨 POTENCIAL LISTING: {alert_info['token']} - Score: {ml_prediction['score']:.1f}")
                    total_alerts += 1
                    time.sleep(2)  # Rate limiting para Telegram
        
        time.sleep(1)  # Rate limiting entre exchanges
    
    logger.info(f"\n🎯 Total de alertas de novos listings: {total_alerts}")

if __name__ == "__main__":
    main()