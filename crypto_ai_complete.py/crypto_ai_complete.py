# eth_holdings_analyzer.py - ANALISA HOLDINGS DE EXCHANGES ETHEREUM
import requests
import time
from datetime import datetime

# ============================
# CONFIGURAÇÃO ETHEREUM
# ============================
TELEGRAM_BOT_TOKEN_ETH = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID_ETH = "5239378332"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"

# Wallets de Exchanges Ethereum (confirmadas)
EXCHANGE_WALLETS_ETH = {
    "Binance ETH": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "Coinbase ETH": "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43",
    "Kraken ETH": "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2",
    "Bitfinex ETH": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "OKX ETH": "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b",
}

THRESHOLD_USD = 10000  # $10,000 mínimo
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# Tokens que devem ser IGNORADOS (incluindo tokens já listados em exchanges)
IGNORE_TOKENS = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "USDG",  # Stablecoins
    "ETH", "WETH", "BTC", "WBTC", "LINK", "UNI", "AAVE",    # Bluechips
    "ETHFI", "ENA", "PENDLE", "ARB", "OP", "MATIC", "SNX",  # Tokens já listados
    "MKR", "COMP", "CRV", "LDO", "RPL", "1INCH", "SUSHI"    # Mais tokens listados
}

# ============================
# SISTEMA ETHEREUM (CORRIGIDO)
# ============================
def send_telegram_alert_eth(message):
    """Envia alerta para Telegram ETH"""
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

def get_dex_data_eth(token_address):
    """Obtém dados do DexScreener para Ethereum"""
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pair = data['pairs'][0]
                # Adicionar URL do DexScreener
                pair['url'] = f"https://dexscreener.com/ethereum/{token_address}"
                return pair
        return None
    except:
        return None

def get_wallet_token_balance_eth(wallet_address):
    """Obtém BALANÇO ATUAL de tokens ERC-20 de uma wallet Ethereum (CORRIGIDO)"""
    try:
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'address': wallet_address,
            'tag': 'latest',
            'apikey': ETHERSCAN_API_KEY
        }
        
        # Primeiro obter lista de tokens
        list_params = {
            'module': 'account',
            'action': 'tokentx',
            'address': wallet_address,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'desc',
            'page': 1,
            'offset': 100,
            'apikey': ETHERSCAN_API_KEY
        }
        
        response = requests.get(ETHERSCAN_API_URL, params=list_params, timeout=20)
        if response.status_code != 200:
            return []
            
        data = response.json()
        if data['status'] != '1' or not data.get('result'):
            return []
        
        # Extrair tokens únicos
        unique_tokens = {}
        
        for tx in data['result']:
            try:
                token_address = tx['contractAddress']
                token_symbol = tx.get('tokenSymbol', 'UNKNOWN').upper()
                
                # Ignorar tokens conhecidos e já listados
                if token_symbol in IGNORE_TOKENS:
                    continue
                
                if token_address in unique_tokens:
                    continue
                
                # Obter BALANÇO ATUAL do token
                balance_params = {
                    'module': 'account',
                    'action': 'tokenbalance',
                    'contractaddress': token_address,
                    'address': wallet_address,
                    'tag': 'latest',
                    'apikey': ETHERSCAN_API_KEY
                }
                
                balance_response = requests.get(ETHERSCAN_API_URL, params=balance_params, timeout=10)
                if balance_response.status_code != 200:
                    continue
                    
                balance_data = balance_response.json()
                if balance_data['status'] != '1':
                    continue
                
                # Converter balanço
                decimals = int(tx.get('tokenDecimal', 18))
                raw_balance = int(balance_data['result'])
                real_balance = raw_balance / (10 ** decimals)
                
                if real_balance <= 0:
                    continue
                
                # Obter dados do DexScreener
                dex_data = get_dex_data_eth(token_address)
                if not dex_data or not dex_data.get('priceUsd'):
                    continue
                
                price = float(dex_data['priceUsd'])
                value_usd = real_balance * price
                
                unique_tokens[token_address] = {
                    'symbol': token_symbol,
                    'amount': real_balance,
                    'value_usd': value_usd,
                    'price': price,
                    'liquidity': dex_data.get('liquidity', {}).get('usd', 0),
                    'volume_24h': dex_data.get('volume', {}).get('h24', 0),
                    'dex': dex_data.get('dexId', 'Unknown'),
                    'dex_url': dex_data.get('url', '')
                }
                
            except Exception as e:
                continue
        
        return list(unique_tokens.values())
        
    except Exception as e:
        print(f"❌ Erro ao obter tokens: {e}")
        return []

def analyze_eth_holdings(holdings, wallet_name):
    """Analisa holdings Ethereum para encontrar gems"""
    gems = []
    
    for token in holdings:
        # Filtros mais rigorosos
        if (token['value_usd'] >= THRESHOLD_USD and
            token['liquidity'] > 50000 and  # Liquidez mínima maior
            token['volume_24h'] > 10000 and  # Volume mínimo maior
            token['symbol'] not in IGNORE_TOKENS):  # Verificação extra
            
            gems.append({
                'wallet': wallet_name,
                'token': token['symbol'],
                'amount': token['amount'],
                'value_usd': token['value_usd'],
                'price': token['price'],
                'liquidity': token['liquidity'],
                'volume_24h': token['volume_24h'],
                'dex': token['dex'],
                'dex_url': token.get('dex_url', '')
            })
    
    return gems

def format_eth_alert(gem):
    """Formata alerta de gem Ethereum (CORRIGIDO)"""
    emoji = "💎" if gem['value_usd'] > 50000 else "🔥"
    
    message = f"{emoji} <b>HOLDING ETHEREUM ENCONTRADO!</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {gem['wallet']}\n"
    message += f"💎 <b>Token:</b> {gem['token']}\n"
    message += f"💰 <b>Valor Aproximado:</b> ${gem['value_usd']:,.2f}\n"
    message += f"📦 <b>Quantidade:</b> {gem['amount']:,.2f}\n"
    message += f"📊 <b>Preço:</b> ${gem['price']:.6f}\n"
    message += f"💧 <b>Liquidez:</b> ${gem['liquidity']:,.0f}\n"
    message += f"📈 <b>Volume 24h:</b> ${gem['volume_24h']:,.0f}\n"
    message += f"🦄 <b>DEX:</b> {gem['dex']}\n\n"
    
    # LINK DO DEXSCREENER ADICIONADO
    if gem.get('dex_url'):
        message += f"🔗 <b>DexScreener:</b> {gem['dex_url']}\n\n"
    
    message += f"<i>🤖 Holding significativo em Ethereum</i>"
    
    return message

# ============================
# PROGRAMA PRINCIPAL
# ============================
def main():
    print("🤖 ANALISADOR DE HOLDINGS ETHEREUM (CORRIGIDO)")
    print("💎 Procurando holdings significativos em ETH")
    print("=" * 55)
    
    total_gems = 0
    
    for wallet_name, wallet_address in EXCHANGE_WALLETS_ETH.items():
        print(f"🔍 Analisando {wallet_name}...")
        
        # Obter tokens da wallet (BALANÇO ATUAL)
        tokens = get_wallet_token_balance_eth(wallet_address)
        
        if not tokens:
            print(f"   ❌ Nenhum token relevante encontrado")
            continue
            
        print(f"   ✅ {len(tokens)} tokens potenciais encontrados")
        
        # Mostrar alguns tokens para debug
        for token in tokens[:3]:
            print(f"   ▪ {token['symbol']}: ${token['value_usd']:,.2f}")
        
        # Encontrar gems
        gems = analyze_eth_holdings(tokens, wallet_name)
        
        if gems:
            print(f"   💎 {len(gems)} holding(s) significativo(s)!")
            
            for gem in gems:
                alert_message = format_eth_alert(gem)
                if send_telegram_alert_eth(alert_message):
                    print(f"   📤 Enviado: {gem['token']} - ${gem['value_usd']:,.0f}")
                total_gems += 1
                time.sleep(2)
        else:
            print(f"   ℹ️  Nenhum holding significativo")
        
        time.sleep(3)  # Aumentado para evitar rate limiting
    
    # Relatório final
    if total_gems > 0:
        print(f"\n🎉 Total de {total_gems} holding(s) significativo(s) encontrado(s)!")
        send_telegram_alert_eth(f"✅ Análise ETH concluída: {total_gems} holdings encontrados!")
    else:
        print(f"\n🤔 Nenhum holding significativo encontrado")
        print("💡 Tente ajustar os filtros se necessário")

if __name__ == "__main__":
    main()