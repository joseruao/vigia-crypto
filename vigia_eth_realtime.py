# vigia_eth_realtime.py - MONITORIZAÇÃO TEMPO REAL ETHEREUM
import requests
import time
from datetime import datetime

# ============================
# CONFIGURAÇÃO ETHEREUM
# ============================
TELEGRAM_BOT_TOKEN_ETH = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID_ETH = "5239378332"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"

# Endpoints das APIs
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# Wallets de exchanges Ethereum
# WALLETS COMPLETAS DE EXCHANGES ETHEREUM
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
THRESHOLD_USD = 50000 # $50k threshold
CHECK_INTERVAL = 60  # Verificar a cada 60 segundos

# ============================
# FUNÇÕES PRINCIPAIS
# ============================
def send_telegram_alert_eth(message):
    """Envia alerta para o Telegram ETH com formatação HTML"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_ETH}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_ETH,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Alerta enviado para Telegram ETH")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para Telegram ETH: {e}")
        return False

def get_recent_token_transfers(wallet_address, last_check_time):
    """Obtém transferências recentes de tokens"""
    try:
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': wallet_address,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'desc',
            'page': 1,
            'offset': 10,
            'apikey': ETHERSCAN_API_KEY
        }
        
        response = requests.get(ETHERSCAN_API_URL, params=params, timeout=15)
        if response.status_code != 200:
            return []
            
        data = response.json()
        if data['status'] != '1' or not data.get('result'):
            return []
        
        # Filtrar apenas transferências muito recentes (últimos 2 minutos)
        recent_transfers = []
        for transfer in data['result']:
            if int(transfer['timeStamp']) > last_check_time:
                recent_transfers.append(transfer)
            else:
                break
                
        return recent_transfers
        
    except Exception as e:
        print(f"❌ Erro ao buscar transferências: {e}")
        return []

def get_dexscreener_data(token_address):
    """Obtém dados completos do DexScreener"""
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pair = data['pairs'][0]
                return {
                    'price': float(pair.get('priceUsd', 0)),
                    'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                    'fdv': float(pair.get('fdv', 0)),
                    'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                    'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                    'dex': pair.get('dexId', 'Unknown'),
                    'pair_url': pair.get('url', ''),
                    'base_token': pair.get('baseToken', {}).get('name', 'Unknown'),
                    'quote_token': pair.get('quoteToken', {}).get('symbol', '')
                }
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar DexScreener: {e}")
        return None

def analyze_token_transfer(transfer, wallet_address, exchange_name):
    """Analisa transferência com critérios de gems"""
    try:
        # Verificar se é depósito na exchange
        if (transfer['to'].lower() == wallet_address.lower() and 
            transfer['value'] != '0' and
            transfer.get('tokenDecimal')):
            
            token_address = transfer['contractAddress']
            decimals = int(transfer['tokenDecimal'])
            symbol = transfer.get('tokenSymbol', 'UNKNOWN')
            
            # Ignorar stablecoins e bluechips
            stablecoins = {'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'USDG'}
            bluechips = {'WETH', 'WBTC', 'ETH', 'BTC', 'LINK', 'UNI', 'AAVE', 'MATIC', 'MKR', 'COMP'}
            
            if symbol in stablecoins or symbol in bluechips:
                return None
                
            # Calcular quantidade
            amount = int(transfer['value']) / (10 ** decimals)
            
            # Buscar dados DexScreener
            dex_data = get_dexscreener_data(token_address)
            
            if dex_data and dex_data['price'] > 0:
                value_usd = amount * dex_data['price']
                
                # Critérios para gems potenciais
                is_potential_gem = (
                    value_usd >= THRESHOLD_USD and
                    dex_data['liquidity'] > 10000 and  # Mínimo de liquidez
                    dex_data['fdv'] < 50000000 and     # FDV abaixo de 50M
                    dex_data['volume_24h'] > 10000     # Volume mínimo
                )
                
                if is_potential_gem:
                    return {
                        "exchange": exchange_name,
                        "token": symbol,
                        "token_address": token_address,
                        "amount": amount,
                        "value_usd": value_usd,
                        "price": dex_data['price'],
                        "liquidity": dex_data['liquidity'],
                        "fdv": dex_data['fdv'],
                        "volume_24h": dex_data['volume_24h'],
                        "price_change_24h": dex_data['price_change_24h'],
                        "dex": dex_data['dex'],
                        "pair_url": dex_data['pair_url'],
                        "base_token": dex_data['base_token'],
                        "hash": transfer['hash'],
                        "timestamp": int(transfer['timeStamp'])
                    }
            
        return None
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def format_telegram_alert(alert_info):
    """Formata alerta bonito para Telegram"""
    emoji = "💎" if alert_info['fdv'] < 10000000 else "🔥"
    trend_emoji = "📈" if alert_info['price_change_24h'] > 0 else "📉"
    
    message = f"{emoji} <b>ALERTA ETHEREUM GEM</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    message += f"💰 <b>Valor Recebido:</b> ${alert_info['value_usd']:,.0f}\n"
    message += f"📦 <b>Quantidade:</b> {alert_info['amount']:,.0f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info['price']:.8f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.0f}\n"
    message += f"🏢 <b>FDV:</b> ${alert_info['fdv']:,.0f}\n"
    message += f"📈 <b>Volume 24h:</b> ${alert_info['volume_24h']:,.0f}\n"
    message += f"{trend_emoji} <b>Variação 24h:</b> {alert_info['price_change_24h']:+.1f}%\n"
    message += f"🦄 <b>DEX:</b> {alert_info['dex']}\n"
    message += f"⏰ <b>Hora:</b> {datetime.fromtimestamp(alert_info['timestamp']).strftime('%H:%M:%S')}\n\n"
    
    message += f"🔗 <a href='{alert_info['pair_url']}'>Ver no DexScreener</a>\n"
    message += f"🔍 <a href='https://etherscan.io/token/{alert_info['token_address']}'>Etherscan</a>\n"
    message += f"📝 <a href='https://etherscan.io/tx/{alert_info['hash']}'>Ver Transação</a>\n\n"
    
    message += f"<i>⚠️ Não é aconselhamento financeiro</i>"
    
    return message

def monitor_eth_realtime():
    """Monitorização em tempo real das wallets Ethereum"""
    print("🤖 VIGILANTE ETHEREUM - MODO TEMPO REAL")
    print("💎 Procurando gems potenciais em exchanges")
    print("📊 Usando DexScreener para análise")
    print("=" * 60)
    
    last_check_time = int(time.time()) - 120  # Começar verificando últimos 2 minutos
    
    while True:
        try:
            print(f"\n🔍 Verificando transações... {datetime.now().strftime('%H:%M:%S')}")
            
            for exchange_name, wallet_address in EXCHANGE_WALLETS_ETH.items():
                try:
                    # Buscar transferências recentes
                    transfers = get_recent_token_transfers(wallet_address, last_check_time)
                    
                    if transfers:
                        print(f"   ✅ {exchange_name}: {len(transfers)} transferência(s) recente(s)")
                        
                        for transfer in transfers:
                            alert_info = analyze_token_transfer(transfer, wallet_address, exchange_name)
                            if alert_info:
                                # Enviar alerta formatado
                                message = format_telegram_alert(alert_info)
                                send_telegram_alert_eth(message)
                                
                                print(f"   🚨 ALERTA: {alert_info['token']} - ${alert_info['value_usd']:,.0f}")
                                
                                # Pequena pausa entre alertas
                                time.sleep(2)
                    
                    # Pequena pausa entre wallets
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Erro em {exchange_name}: {e}")
                    continue
            
            # Atualizar tempo da última verificação
            last_check_time = int(time.time())
            
            print(f"⏰ Próxima verificação em {CHECK_INTERVAL} segundos...")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"❌ Erro no ciclo principal: {e}")
            time.sleep(30)

# ============================
# EXECUÇÃO PRINCIPAL
# ============================
if __name__ == "__main__":
    # Verificar configuração
    if ETHERSCAN_API_KEY == "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW":
        print("✅ API Key do Etherscan configurada")
    else:
        print("❌ API Key do Etherscan não reconhecida")
    
    print(f"🤖 Bot Token: {'✅' if TELEGRAM_BOT_TOKEN_ETH else '❌'}")
    print(f"💬 Chat ID: {'✅' if TELEGRAM_CHAT_ID_ETH else '❌'}")
    print(f"🔍 Monitorizando {len(EXCHANGE_WALLETS_ETH)} wallets")
    print("=" * 60)
    
    # Iniciar monitorização
    monitor_eth_realtime()