# holdings_ethereum.py
import requests
import time
import json
from datetime import datetime
from collections import defaultdict

# ============================
# CONFIGURAÇÃO
# ============================
TELEGRAM_BOT_TOKEN = "7999197151:AAELAI64aNx2nVk-Uhp-20YAxrXlXbVFzjw"
TELEGRAM_CHAT_ID = "5239378332"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"
LISTED_TOKENS_FILE = "listed_tokens.json"
MIN_VALUE_USD = 300000
MIN_LIQUIDITY_USD = 100000  # Mínimo $100K de liquidez para ser considerado real

# Wallets Ethereum
ETHEREUM_WALLETS = {
    "Binance 8": "0xf977814e90da44bfa03b6295a0616a897441acec",
    "Binance 14": "0x564286362092d8e7936f0549571a803b203aaced",
    "Binance 7": "0x28c6c06298d514db089934071355e5743bf21d60",
    "Binance 16": "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
    "Kraken": "0xe9f7ecae3a53d2a67105292894676b00d1fab785",
    "Bitfinex 2": "0x6b76f8d2aeb91d1e14f6b195f83eae0c0e7f7525",
    "Bitfinex 19": "0xdaa5dfc4490b9d22b58ed7a6cf6c648995cbf43d",
    "Gemini 3": "0x8d12a197cb00d4747a1fe03395095ce2a5cc6819",
    "OKX 73": "0x2c4b9d9a57d7b6f91e3d6b1a3b4c1d81b37c0c2c",
    "OKX 93": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
    "Robinhood": "0x7e4a8391c728fEd9069B2962699AB416628B19Fa",
    "Coinbase 10": "0x503828976d22510aad0201ac7ec88293211d23da",
    "Upbit": "0x55fe002aeff02f77364de339a1292923a15844b8",
    "Gate.io": "0xc882b111a75c0c657fc507c04fbfcd2cc984f071",
    "Bitget Hot Wallet 1": "0xe6a421f24d330967a3af2f4cdb5c34067e7e4d75"
}

# ============================
# FUNÇÕES AUXILIARES
# ============================
def send_telegram_alert(message):
    """Envia alerta para Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para Telegram: {e}")
        return False

def load_listed_tokens():
    """Carrega tokens listados por exchange"""
    try:
        with open(LISTED_TOKENS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erro ao carregar listed_tokens.json: {e}")
        return {
            "Binance": ["USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP", 
                       "ENJ", "BAT", "ZRX", "SNX", "CRV", "1INCH", "YFI", "SUSHI", "REN", "BAL"],
            "Kraken": ["USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP"],
            "OKX": ["USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR"],
            "Coinbase": ["USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE"],
            "Bitfinex": ["USDT", "USDC", "WBTC", "DAI"],
            "Gemini": ["USDT", "USDC", "WBTC", "DAI"],
            "Robinhood": ["USDT", "USDC", "WBTC"],
            "Upbit": ["USDT", "USDC", "WBTC"],
            "Gate.io": ["USDT", "USDC", "WBTC", "DAI"],
            "Bitget": ["USDT", "USDC", "WBTC", "DAI"]
        }

def is_token_listed_on_exchange(token_symbol, wallet_name):
    """Verifica se um token está listado em uma exchange específica"""
    if token_symbol.upper() == "ETH":
        return True
    
    exchange_map = {
        "Binance 8": "Binance", "Binance 14": "Binance", "Binance 7": "Binance", "Binance 16": "Binance",
        "Kraken": "Kraken",
        "Bitfinex 2": "Bitfinex", "Bitfinex 19": "Bitfinex",
        "Gemini 3": "Gemini",
        "OKX 73": "OKX", "OKX 93": "OKX",
        "Robinhood": "Robinhood",
        "Coinbase 10": "Coinbase",
        "Upbit": "Upbit",
        "Gate.io": "Gate.io",
        "Bitget Hot Wallet 1": "Bitget"
    }
    
    target_exchange = exchange_map.get(wallet_name, wallet_name)
    
    if target_exchange in LISTED_TOKENS:
        listed_tokens = [t.upper() for t in LISTED_TOKENS[target_exchange]]
        return token_symbol.upper() in listed_tokens
    
    return False

def get_listed_exchanges_for_token(token_symbol):
    """Retorna todas as exchanges onde o token está listado"""
    listed_exchanges = []
    for exchange, tokens in LISTED_TOKENS.items():
        if token_symbol.upper() in [t.upper() for t in tokens]:
            listed_exchanges.append(exchange)
    return listed_exchanges

def get_eth_token_data(token_address):
    """Obtém dados completos do token via DexScreener e CoinGecko"""
    try:
        # Dados do DexScreener
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        dex_response = requests.get(dex_url, timeout=10)
        
        dex_data = {
            "price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0,
            "dex_url": f"https://dexscreener.com/ethereum/{token_address}",
            "name": "", "symbol": "", "coingecko_url": ""
        }
        
        if dex_response.status_code == 200:
            data = dex_response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pairs = data['pairs']
                main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                
                dex_data.update({
                    "price": float(main_pair.get('priceUsd', 0)),
                    "liquidity": float(main_pair.get('liquidity', {}).get('usd', 0)),
                    "volume_24h": float(main_pair.get('volume', {}).get('h24', 0)),
                    "name": main_pair.get('baseToken', {}).get('name', ''),
                    "symbol": main_pair.get('baseToken', {}).get('symbol', ''),
                    "dex_url": main_pair.get('url', dex_data["dex_url"])
                })
        
        # Tentar encontrar CoinGecko ID
        coingecko_id = find_coingecko_id(dex_data["name"], dex_data["symbol"], token_address)
        if coingecko_id:
            dex_data["coingecko_url"] = f"https://www.coingecko.com/pt/moedas/{coingecko_id}"
        
        return dex_data
        
    except Exception as e:
        print(f"❌ Erro ao obter dados do token {token_address}: {e}")
        return {"price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0,
                "dex_url": f"https://dexscreener.com/ethereum/{token_address}",
                "name": "", "symbol": "", "coingecko_url": ""}

def find_coingecko_id(token_name, token_symbol, token_address):
    """Tenta encontrar o ID do CoinGecko para o token"""
    try:
        # Pesquisar por símbolo/nome
        search_query = token_symbol or token_name or token_address[:6]
        search_url = f"https://api.coingecko.com/api/v3/search?query={search_query}"
        response = requests.get(search_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('coins'):
                for coin in data['coins'][:5]:
                    if (coin.get('symbol', '').upper() == (token_symbol or '').upper() or
                        coin.get('name', '').upper() == (token_name or '').upper()):
                        return coin.get('id', '')
        
        return None
    except:
        return None

def is_scam_token(token_data, value_usd):
    """Verifica se é um token scam/lixo"""
    # 1. Liquidez muito baixa
    if token_data["liquidity"] < MIN_LIQUIDITY_USD:
        return True
    
    # 2. Nomes suspeitos (contém URLs, "reward", "claim", etc.)
    suspicious_keywords = ["http", "www", ".com", ".org", ".fi", ".website", "reward", "claim", "visit", "bounty", "invitation"]
    name_lower = (token_data["name"] or "").lower()
    symbol_lower = (token_data["symbol"] or "").lower()
    
    for keyword in suspicious_keywords:
        if keyword in name_lower or keyword in symbol_lower:
            return True
    
    # 3. Valores exatos suspeitos (ex: $500,000.00 exato)
    if value_usd % 100000 == 0 and value_usd >= 100000:
        return True
    
    # 4. Volume zero com valor alto
    if token_data["volume_24h"] == 0 and value_usd > 100000:
        return True
    
    return False

def get_eth_price():
    """Obtém o preço atual do ETH"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['ethereum']['usd']
    except:
        pass
    return 3000

# ============================
# FUNÇÕES ETHEREUM
# ============================
def get_eth_holdings(wallet_address):
    """Obtém holdings Ethereum - APENAS TOKENS ERC-20"""
    try:
        holdings = []
        processed_tokens = set()
        
        # Obter tokens ERC-20
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet_address,
            "page": 1,
            "offset": 100,
            "sort": "desc",
            "apikey": ETHERSCAN_API_KEY
        }
        
        response = requests.get("https://api.etherscan.io/api", params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1' and data.get('result'):
                for tx in data['result']:
                    try:
                        token_address = tx.get('contractAddress', '')
                        symbol = tx.get('tokenSymbol', '')
                        
                        # Ignorar tokens já processados, ETH e stablecoins
                        if (not token_address or token_address in processed_tokens or
                            symbol.upper() in ["ETH", "USDT", "USDC", "DAI", "BUSD", "TUSD"]):
                            continue
                        
                        # Obter balanço atual
                        balance_params = {
                            "module": "account",
                            "action": "tokenbalance",
                            "contractaddress": token_address,
                            "address": wallet_address,
                            "tag": "latest",
                            "apikey": ETHERSCAN_API_KEY
                        }
                        
                        balance_response = requests.get("https://api.etherscan.io/api", params=balance_params, timeout=15)
                        if balance_response.status_code == 200:
                            balance_data = balance_response.json()
                            if balance_data.get('status') == '1':
                                decimals = int(tx.get('tokenDecimal', 18))
                                balance = int(balance_data['result']) / 10**decimals
                                
                                if balance > 0:
                                    token_data = get_eth_token_data(token_address)
                                    if token_data["price"] > 0:
                                        value_usd = balance * token_data["price"]
                                        
                                        # VERIFICAR SE NÃO É SCAM ANTES DE ADICIONAR
                                        if (value_usd >= MIN_VALUE_USD and 
                                            not is_scam_token(token_data, value_usd)):
                                            
                                            holdings.append({
                                                "symbol": token_data["symbol"] or symbol or token_address[:8] + "...",
                                                "name": token_data["name"] or tx.get('tokenName', ''),
                                                "balance": balance,
                                                "value_usd": value_usd,
                                                "address": token_address,
                                                "dex_url": token_data["dex_url"],
                                                "coingecko_url": token_data["coingecko_url"],
                                                "liquidity": token_data["liquidity"],
                                                "volume_24h": token_data["volume_24h"]
                                            })
                                            
                                            processed_tokens.add(token_address)
                                            print(f"   ✅ {token_data['symbol'] or symbol}: {balance:,.2f} tokens (${value_usd:,.2f})")
                    
                    except Exception as e:
                        print(f"❌ Erro ao processar token: {e}")
                        continue
        
        return holdings
        
    except Exception as e:
        print(f"❌ Erro ao obter holdings: {e}")
        return []

# ============================
# PROGRAMA PRINCIPAL
# ============================
def main():
    print("🤖 VERIFICADOR DE TOKENS ETHEREUM NÃO LISTADOS (>$300K)")
    print("=" * 65)
    print(f"🔍 Filtro: Liquidez mínima ${MIN_LIQUIDITY_USD:,} | Ignorando tokens scam")
    print("=" * 65)
    
    global LISTED_TOKENS
    LISTED_TOKENS = load_listed_tokens()
    
    for wallet_name, wallet_address in ETHEREUM_WALLETS.items():
        print(f"\n📊 Analisando {wallet_name}...")
        holdings = get_eth_holdings(wallet_address)
        
        unlisted_tokens = []
        for token in holdings:
            if not is_token_listed_on_exchange(token["symbol"], wallet_name):
                unlisted_tokens.append(token)
                print(f"   🚫 NÃO LISTADO: {token['symbol']} (${token['value_usd']:,.2f})")
        
        if unlisted_tokens:
            message = f"🚨 <b>ETHEREUM - TOKENS NÃO LISTADOS - {wallet_name}</b>\n\n"
            message += f"💰 <b>Tokens ERC-20 > ${MIN_VALUE_USD:,} não listados:</b>\n\n"
            
            total_value = 0
            
            for token in unlisted_tokens:
                total_value += token["value_usd"]
                
                # Obter exchanges onde está listado
                listed_exchanges = get_listed_exchanges_for_token(token["symbol"])
                
                message += f"💎 <b>{token['name']} ({token['symbol']})</b>\n"
                message += f"📊 <b>Valor:</b> ${token['value_usd']:,.2f}\n"
                message += f"🔢 <b>Balance:</b> {token['balance']:,.2f}\n"
                
                if listed_exchanges:
                    message += f"🏪 <b>Listado em:</b> {', '.join(listed_exchanges)}\n"
                else:
                    message += f"🏪 <b>Listado em:</b> Nenhuma exchange major\n"
                
                if token["liquidity"] > 0:
                    message += f"💧 <b>Liquidez:</b> ${token['liquidity']:,.0f}\n"
                if token["volume_24h"] > 0:
                    message += f"📈 <b>Volume 24h:</b> ${token['volume_24h']:,.0f}\n"
                
                # Links de análise
                message += f"🔗 <a href='{token['dex_url']}'>DexScreener</a>\n"
                if token["coingecko_url"]:
                    message += f"🔗 <a href='{token['coingecko_url']}'>CoinGecko</a>\n"
                
                message += f"📍 <a href='https://etherscan.io/token/{token['address']}'>Etherscan</a>\n"
                message += "\n"
            
            message += f"💰 <b>VALOR TOTAL:</b> ${total_value:,.2f}\n\n"
            message += f"<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
            
            if send_telegram_alert(message):
                print(f"✅ Alerta enviado - {len(unlisted_tokens)} tokens")
            else:
                print(f"❌ Falha ao enviar alerta")
            
            time.sleep(3)
        else:
            print(f"✅ Nenhum token não listado encontrado")

if __name__ == "__main__":
    main()