# vigia_eth_24h_completo.py - ANÁLISE 24H COM TODAS AS WALLETS
import requests
import time
from datetime import datetime, timedelta

# ============================
# CONFIGURAÇÃO ETHEREUM
# ============================
TELEGRAM_BOT_TOKEN_ETH = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID_ETH = "5239378332"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"

ETHERSCAN_API_URL = "https://api.etherscan.io/api"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

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

THRESHOLD_USD = 50000  # Threshold de $50k

# ============================
# FUNÇÕES PRINCIPAIS
# ============================
def send_telegram_alert_eth(message):
    """Envia alerta para o Telegram ETH"""
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

def get_all_token_transfers_24h(wallet_address, start_timestamp):
    """Obtém TODAS as transferências das últimas 24h com paginação"""
    all_transfers = []
    page = 1
    
    while True:
        try:
            params = {
                'module': 'account',
                'action': 'tokentx',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'page': page,
                'offset': 1000,
                'apikey': ETHERSCAN_API_KEY
            }
            
            response = requests.get(ETHERSCAN_API_URL, params=params, timeout=20)
            if response.status_code != 200:
                break
                
            data = response.json()
            if data['status'] != '1' or not data.get('result'):
                break
            
            # Filtrar apenas transferências das últimas 24h
            page_transfers = []
            for transfer in data['result']:
                if int(transfer['timeStamp']) >= start_timestamp:
                    page_transfers.append(transfer)
                else:
                    break
            
            all_transfers.extend(page_transfers)
            
            if len(page_transfers) < len(data['result']) or len(data['result']) < 1000:
                break
                
            page += 1
            time.sleep(0.2)
            
        except Exception as e:
            print(f"❌ Erro na página {page}: {e}")
            break
    
    return all_transfers

def get_dexscreener_data(token_address):
    """Obtém dados do DexScreener"""
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
                    'base_token': pair.get('baseToken', {}).get('name', 'Unknown')
                }
        return None
    except:
        return None

def analyze_transfer(transfer, wallet_address, exchange_name):
    """Analisa uma transferência com critérios de gem"""
    try:
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
                
            amount = int(transfer['value']) / (10 ** decimals)
            
            dex_data = get_dexscreener_data(token_address)
            
            if dex_data and dex_data['price'] > 0:
                value_usd = amount * dex_data['price']
                
                if (value_usd >= THRESHOLD_USD and
                    dex_data['liquidity'] > 10000 and
                    dex_data['fdv'] < 100000000 and
                    dex_data['volume_24h'] > 5000):
                    
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
                        "hash": transfer['hash'],
                        "timestamp": int(transfer['timeStamp'])
                    }
            
        return None
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def format_24h_report(alert_info, total_transfers, total_alertas):
    """Formata relatório das 24h"""
    emoji = "💎" if alert_info['fdv'] < 50000000 else "🔥"
    
    message = f"{emoji} <b>RELATÓRIO 24H - GEM ENCONTRADA</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    message += f"💰 <b>Valor Recebido:</b> ${alert_info['value_usd']:,.0f}\n"
    message += f"📦 <b>Quantidade:</b> {alert_info['amount']:,.0f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info['price']:.8f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.0f}\n"
    message += f"🏢 <b>FDV:</b> ${alert_info['fdv']:,.0f}\n"
    message += f"📈 <b>Volume 24h:</b> ${alert_info['volume_24h']:,.0f}\n"
    message += f"🦄 <b>DEX:</b> {alert_info['dex']}\n"
    message += f"⏰ <b>Horário:</b> {datetime.fromtimestamp(alert_info['timestamp']).strftime('%d/%m %H:%M')}\n\n"
    
    message += f"🔗 <a href='{alert_info['pair_url']}'>Ver no DexScreener</a>\n"
    message += f"🔍 <a href='https://etherscan.io/token/{alert_info['token_address']}'>Etherscan</a>\n"
    message += f"📝 <a href='https://etherscan.io/tx/{alert_info['hash']}'>Ver Transação</a>\n\n"
    
    message += f"📊 <i>Total analisado: {total_transfers} transferências</i>\n"
    message += f"🚨 <i>Alertas encontrados: {total_alertas}</i>\n"
    
    return message

def analisar_24h_completo():
    """Análise COMPLETA das últimas 24 horas"""
    print("🤖 VIGILANTE ETHEREUM - ANÁLISE 24H")
    print("💎 Verificando últimas 24 horas...")
    print("============================================================")
    
    start_time = time.time()
    start_timestamp = int((datetime.now() - timedelta(hours=24)).timestamp())
    total_alertas = 0
    
    send_telegram_alert_eth("🔍 <b>INICIANDO ANÁLISE 24H ETHEREUM</b>\n⏰ Hora: " + 
                           datetime.now().strftime("%d/%m/%Y %H:%M"))
    
    for exchange_name, wallet_address in EXCHANGE_WALLETS_ETH.items():
        try:
            print(f"🔍 Analisando {exchange_name}...")
            
            transfers = get_all_token_transfers_24h(wallet_address, start_timestamp)
            
            if transfers:
                print(f"   ✅ {len(transfers)} transferência(s) nas últimas 24h")
                
                alertas_wallet = 0
                for transfer in transfers:
                    alert_info = analyze_transfer(transfer, wallet_address, exchange_name)
                    if alert_info:
                        message = format_24h_report(alert_info, len(transfers), alertas_wallet + 1)
                        send_telegram_alert_eth(message)
                        
                        print(f"   🚨 ALERTA: {alert_info['token']} - ${alert_info['value_usd']:,.0f}")
                        alertas_wallet += 1
                        total_alertas += 1
                        
                        time.sleep(3)
                
                if alertas_wallet > 0:
                    print(f"   🎯 {alertas_wallet} alerta(s) encontrado(s)")
                else:
                    print(f"   ℹ️  Nenhum alerta significativo")
                    
            else:
                print(f"   ℹ️  Nenhuma transferência nas últimas 24h")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Erro em {exchange_name}: {e}")
            continue
    
    tempo_decorrido = time.time() - start_time
    mensagem_final = f"✅ <b>ANÁLISE 24H CONCLUÍDA</b>\n\n"
    mensagem_final += f"⏰ <b>Tempo decorrido:</b> {tempo_decorrido:.1f}s\n"
    mensagem_final += f"🚨 <b>Total de alertas:</b> {total_alertas}\n"
    mensagem_final += f"🏦 <b>Wallets analisadas:</b> {len(EXCHANGE_WALLETS_ETH)}\n"
    mensagem_final += f"📅 <b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    send_telegram_alert_eth(mensagem_final)
    print("============================================================")
    print(f"✅ Análise concluída! {total_alertas} alertas encontrados")
    print(f"⏰ Tempo total: {tempo_decorrido:.1f} segundos")

# ============================
# EXECUÇÃO
# ============================
if __name__ == "__main__":
    analisar_24h_completo()