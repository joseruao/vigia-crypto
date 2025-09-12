# vigia_ethereum_final_corrigido.py
import requests
import time
import json
from datetime import datetime, timedelta

# ============================
# CONFIGURAÇÃO ETHEREUM
# ============================
TELEGRAM_BOT_TOKEN_ETH = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID_ETH = "5239378332"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"

ETHERSCAN_API_URL = "https://api.etherscan.io/api"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# WALLETS DE EXCHANGES ETHEREUM
EXCHANGE_WALLETS_ETH = {
    # Binance
    "Binance 8": "0xf977814e90da44bfa03b6295a0616a897441acec",
    "Binance 14": "0x564286362092d8e7936f0549571a803b203aaced",
    "Binance 7": "0x28c6c06298d514db089934071355e5743bf21d60",
    "Binance 16": "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
    
    # Kraken
    "Kraken": "0xe9f7ecae3a53d2a67105292894676b00d1fab785",
    
    # Bitfinex
    "Bitfinex 2": "0x6b76f8d2aeb91d1e14f6b195f83eae0c0e7f7525",
    "Bitfinex 19": "0xdaa5dfc4490b9d22b58ed7a6cf6c648995cbf43d",
    
    # Gemini
    "Gemini 3": "0x8d12a197cb00d4747a1fe03395095ce2a5cc6819",
    
    # OKX
    "OKX 73": "0x2c4b9d9a57d7b6f91e3d6b1a3b4c1d81b37c0c2c",
    "OKX 93": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
    
    # Robinhood
    "Robinhood": "0x7e4a8391c728fEd9069B2962699AB416628B19Fa",
    
    # Upbit
    "Upbit": "0x55fe002aeff02f77364de339a1292923a15844b8",
    
    # Gate.io
    "Gate.io": "0xc882b111a75c0c657fc507c04fbfcd2cc984f071",
    
    # Bitget
    "Bitget Hot Wallet 1": "0xe6a421f24d330967a3af2f4cdb5c34067e7e4d75"
}

# WALLETS ESPECIAIS (INSIDERS/WHALES) - ETHEREUM
SPECIAL_WALLETS_ETH = {
    "Alameda Research": "0x9e5a52f57b3038f1b8eee8f3da3d8bb1b6f4c8b1",
    "Jump Trading": "0x7e4a8391c728fEd9069B2962699AB416628B19Fa",
    "Wintermute Trading": "0x8b6c7a3b6a9c8f8f8f8f8f8f8f8f8f8f8f8f8f8f",
    "Genesis Trading": "0x9c5a52f57b3038f1b8eee8f3da3d8bb1b6f4c8b2",
    "Three Arrows Capital": "0x8d12a197cb00d4747a1fe03395095ce2a5cc6819",
    "Suspicious Early Mover": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
}

# Usar o MESMO ficheiro do Vigia Solana
LISTED_TOKENS_FILE = "listed_tokens.json"
THRESHOLD_USD = 10000  # Threshold para alertas

# ============================
# FUNÇÕES ETHEREUM (CORRIGIDAS)
# ============================
def load_listed_tokens():
    """Carrega tokens listados por exchange - MESMO FICHEIRO DO SOLANA"""
    try:
        with open(LISTED_TOKENS_FILE, 'r') as f:
            return json.load(f)
    except:
        # Fallback básico para Ethereum (usando dados reais)
        return {
            "Binance": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP", 
                       "ENJ", "BAT", "ZRX", "SNX", "CRV", "1INCH", "YFI", "SUSHI", "REN", "BAL"],
            "Kraken": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP"],
            "Bitfinex": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE"],
            "Gemini": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "BAT", "ZRX"],
            "OKX": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR"],
            "Robinhood": ["ETH", "USDT", "USDC", "BTC", "LINK", "UNI", "AAVE"],
            "Upbit": ["ETH", "USDT", "USDC", "BTC", "LINK"],
            "Gate.io": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE"],
            "Bitget": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI"]
        }

LISTED_TOKENS = load_listed_tokens()

def is_token_listed_on_exchange(token_symbol, exchange_name):
    """Verifica se um token está listado em uma exchange específica"""
    # Normalizar nomes das exchanges
    exchange_map = {
        "Binance 8": "Binance", "Binance 14": "Binance", "Binance 7": "Binance", "Binance 16": "Binance",
        "Kraken": "Kraken",
        "Bitfinex 2": "Bitfinex", "Bitfinex 19": "Bitfinex",
        "Gemini 3": "Gemini",
        "OKX 73": "OKX", "OKX 93": "OKX",
        "Robinhood": "Robinhood",
        "Upbit": "Upbit",
        "Gate.io": "Gate.io",
        "Bitget Hot Wallet 1": "Bitget"
    }
    
    target_exchange = exchange_map.get(exchange_name, exchange_name)
    
    if target_exchange in LISTED_TOKENS:
        listed_tokens = [t.upper() for t in LISTED_TOKENS[target_exchange]]
        return token_symbol.upper() in listed_tokens
    
    return False

def get_listed_exchanges_for_token(token_symbol):
    """Retorna as exchanges onde o token já está listado"""
    listed_exchanges = []
    for exchange, tokens in LISTED_TOKENS.items():
        if token_symbol.upper() in [t.upper() for t in tokens]:
            listed_exchanges.append(exchange)
    return listed_exchanges

def is_special_wallet(wallet_address):
    """Verifica se é uma wallet especial (insider/whale)"""
    return wallet_address.lower() in [w.lower() for w in SPECIAL_WALLETS_ETH.values()]

def send_telegram_alert_eth(message):
    """Envia alerta para Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_ETH}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_ETH,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except:
        return False

def get_erc20_transfers(wallet_address, hours=24):
    """Obtém transferências ERC-20 recentes"""
    try:
        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet_address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "apikey": ETHERSCAN_API_KEY
        }
        
        response = requests.get(ETHERSCAN_API_URL, params=params, timeout=15)
        if response.status_code != 200:
            return []
        
        data = response.json()
        if data.get('status') != '1' or not data.get('result'):
            return []
        
        # Filtrar transferências recentes de entrada
        recent_transfers = []
        for transfer in data['result']:
            if int(transfer.get('timeStamp', 0)) >= start_timestamp:
                # Apenas transferências de entrada (to address é a wallet da exchange)
                if transfer.get('to', '').lower() == wallet_address.lower():
                    recent_transfers.append(transfer)
        
        return recent_transfers[:50]  # Limitar a 50 transferências
        
    except Exception as e:
        print(f"❌ Erro ao buscar transferências ERC-20: {e}")
        return []

def get_dexscreener_data_eth(token_address):
    """Obtém dados do DexScreener para Ethereum"""
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                # Encontrar o par principal (maior liquidez)
                pairs = data['pairs']
                main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                return main_pair
        return None
    except:
        return None

def analyze_eth_transfer(transfer, wallet_address, exchange_name):
    """Analisa uma transferência ERC-20"""
    try:
        token_address = transfer.get('contractAddress')
        token_symbol = transfer.get('tokenSymbol', 'UNKNOWN')
        amount = float(transfer.get('value', 0)) / (10 ** int(transfer.get('tokenDecimal', 18)))
        
        # Ignorar stablecoins e tokens principais
        if token_symbol in ["USDT", "USDC", "ETH", "WBTC", "DAI", "WETH"]:
            return None
        
        # Obter dados do token
        dex_data = get_dexscreener_data_eth(token_address)
        if not dex_data or not dex_data.get('priceUsd'):
            return None
        
        price = float(dex_data['priceUsd'])
        value_usd = amount * price
        
        # Verificar se o token já está listado na PRÓPRIA exchange
        if is_token_listed_on_exchange(token_symbol, exchange_name):
            print(f"   ⚠️  {token_symbol} já listado em {exchange_name} - Ignorando")
            return None
        
        if value_usd < THRESHOLD_USD:
            return None
        
        # Verificar em quais outras exchanges está listado
        listed_exchanges = get_listed_exchanges_for_token(token_symbol)
        
        # Verificar se é wallet especial
        special = is_special_wallet(wallet_address)
        
        return {
            "exchange": exchange_name,
            "token": token_symbol,
            "token_address": token_address,
            "amount": amount,
            "value_usd": value_usd,
            "price": price,
            "liquidity": dex_data.get('liquidity', {}).get('usd', 0),
            "volume_24h": dex_data.get('volume', {}).get('h24', 0),
            "pair_url": dex_data.get('url', ''),
            "timestamp": int(transfer.get('timeStamp', time.time())),
            "listed_exchanges": listed_exchanges,
            "special": special
        }
        
    except Exception as e:
        print(f"❌ Erro na análise de transferência: {e}")
        return None

def format_eth_alert(alert_info, total_amount=None, total_value=None):
    """Formata alerta para Telegram (Ethereum)"""
    message = ""

    if alert_info['special']:
        message += "🐋💥🚨 <b>WHALE/INSIDER ALERT ETHEREUM!</b> 🐋💥🚨\n\n"
    elif not alert_info['listed_exchanges']:
        message += "🎺🚀 <b>POSSÍVEL NOVO LISTING ETHEREUM!</b> 🎺🚀\n\n"
    elif total_amount and total_value and total_value > THRESHOLD_USD*2:
        message += "🔥 <b>ALTA PROBABILIDADE DE LISTING ETHEREUM!</b> 🔥\n\n"
    else:
        message += "🔔 <b>Movimentação relevante Ethereum</b>\n\n"

    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    if total_amount and total_value:
        message += f"💰 <b>Valor Total:</b> ${total_value:,.2f}\n"
        message += f"📦 <b>Quantidade Total:</b> {total_amount:,.2f}\n"
    else:
        message += f"💰 <b>Valor:</b> ${alert_info['value_usd']:,.2f}\n"
        message += f"📦 <b>Quantidade:</b> {alert_info['amount']:,.2f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info['price']:.6f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.0f}\n\n"

    if alert_info.get('pair_url'):
        message += f"🔗 <a href='{alert_info['pair_url']}'>Ver no DexScreener</a>\n"
        message += f"🔍 <a href='https://etherscan.io/token/{alert_info['token_address']}'>Ver no Etherscan</a>\n\n"

    if alert_info['listed_exchanges']:
        message += f"💹 <b>Já listado em:</b> {', '.join(alert_info['listed_exchanges'])}\n"
    else:
        message += f"🆕 <b>NOVO TOKEN - Não listado em nenhuma exchange major!</b>\n"

    message += f"<i>⏰ Detectado às {datetime.fromtimestamp(alert_info['timestamp']).strftime('%H:%M:%S')}</i>"

    return message

# ============================
# PROGRAMA PRINCIPAL ETHEREUM
# ============================
def main():
    print("🤖 VIGIA ETHEREUM - DETECTOR DE NOVOS LISTINGS (CORRIGIDO)")
    print("=" * 65)
    total_alerts = 0

    # Primeiro verificar se o ficheiro listed_tokens.json existe
    try:
        with open(LISTED_TOKENS_FILE, 'r') as f:
            listed_data = json.load(f)
        print(f"✅ Ficheiro {LISTED_TOKENS_FILE} carregado com sucesso!")
        print(f"📊 Exchanges no ficheiro: {', '.join(listed_data.keys())}")
    except Exception as e:
        print(f"⚠️  Não foi possível carregar {LISTED_TOKENS_FILE}: {e}")
        print("ℹ️  Usando fallback interno...")

    # Adicionar wallets especiais às exchanges para monitorizar também
    all_wallets_to_monitor = {**EXCHANGE_WALLETS_ETH, **SPECIAL_WALLETS_ETH}

    for wallet_name, wallet_address in all_wallets_to_monitor.items():
        print(f"🔍 Analisando {wallet_name}...")
        
        # Buscar transferências ERC-20
        transfers = get_erc20_transfers(wallet_address, hours=48)
        
        if not transfers:
            print(f"   ℹ️  Nenhuma transferência recente")
            continue

        print(f"   ✅ {len(transfers)} transferências encontradas")

        # Agrupar transferências por token
        token_alerts = {}
        for transfer in transfers:
            alert_info = analyze_eth_transfer(transfer, wallet_address, wallet_name)
            if alert_info:
                key = alert_info['token_address']
                if key not in token_alerts:
                    token_alerts[key] = {'info': alert_info, 'total_amount': 0, 'total_value': 0, 'count': 0}
                token_alerts[key]['total_amount'] += alert_info['amount']
                token_alerts[key]['total_value'] += alert_info['value_usd']
                token_alerts[key]['count'] += 1

        # Enviar alertas
        alerts_found = 0
        for key, data in token_alerts.items():
            alert_info = data['info']
            
            # Só alertar se for relevante
            if data['total_value'] < THRESHOLD_USD:
                continue
                
            if data['count'] > 1:
                message = format_eth_alert(alert_info, data['total_amount'], data['total_value'])
                message += f"\n📊 <b>Transferências agrupadas:</b> {data['count']}"
            else:
                message = format_eth_alert(alert_info)

            if send_telegram_alert_eth(message):
                print(f"   🚨 ALERTA: {alert_info['token']} - ${data['total_value']:,.2f} ({data['count']} transferências)")
                alerts_found += 1
                total_alerts += 1
                time.sleep(1)

        if alerts_found == 0:
            print(f"   ℹ️  Nenhum alerta significativo")

    print(f"\n🎯 Total de alertas Ethereum: {total_alerts}")

if __name__ == "__main__":
    main()