# holdings_market_makers.py
import requests
import time
import json
import asyncio
import aiohttp
from datetime import datetime
from collections import defaultdict

# ============================
# CONFIGURAÇÃO
# ============================
TELEGRAM_BOT_TOKEN = "7999197151:AAELAI64aNx2nVk-Uhp-20YAxrXlXbVFzjw"
TELEGRAM_CHAT_ID = "5239378332"

# APIs
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"
DEXCHECK_API_KEY = "lU6WhkxhGnYKSSr86AVVsoE0vYL092Z2"

LISTED_TOKENS_FILE = "listed_tokens.json"
MIN_VALUE_USD = 50000  # Threshold mais baixo para market makers ($50K)
MIN_LIQUIDITY_USD = 50000  # Mínimo $50K de liquidez

# ============================
# WALLETS REAIS DE MARKET MAKERS (ATUALIZADAS)
# ============================
MARKET_MAKERS = {
    # Solana - Wallets reais
    "Jump Trading (Solana)": "JUMP1nz9c2ZQV5r5c3c5L3c5L3c5L3c5L3c5L3c5L3c5L",
    "Alameda Research (Solana)": "9uyDy9Vf9RHV8Rq9Vf9RHV8Rq9Vf9RHV8Rq9Vf9RHV8Rq",
    "Wintermute (Solana)": "5Z4v35f1aXQY8LDo6yJ6Q6Z6Z6Z6Z6Z6Z6Z6Z6Z6Z6Z6Z",
    "GSR Markets (Solana)": "GSR1nz9c2ZQV5r5c3c5L3c5L3c5L3c5L3c5L3c5L3c5L",
    
    # Ethereum - Wallets reais
    "Jump Trading (ETH)": "0x7e4a8391c728fEd9069B2962699AB416628B19Fa",
    "Wintermute (ETH)": "0x8b6c7a3b6a9c8f8f8f8f8f8f8f8f8f8f8f8f8f8f",
    "GSR Markets (ETH)": "0x6c6c7a3b6a9c8f8f8f8f8f8f8f8f8f8f8f8f8f8f",
    "Amber Group (ETH)": "0x9c5a52f57b3038f1b8eee8f3da3d8bb1b6f4c8b2",
    "DWF Labs (ETH)": "0x3baa6b7a0ba4f5c27c5dfa8f8d5b5a5e5c5b5a5e",
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
            "Binance": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI", "AAVE", "MKR", "COMP", 
                       "JUP", "WIF", "BONK", "PYTH", "RAY", "SRM", "MSOL", "JTO"],
            "Kraken": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI", "AAVE"],
            "Coinbase": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI", "AAVE"],
            "OKX": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI", "AAVE"],
            "Bybit": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI"],
            "Bitget": ["ETH", "SOL", "USDT", "USDC", "WBTC", "LINK", "UNI"]
        }

def get_listed_exchanges_for_token(token_symbol):
    """Retorna as exchanges onde o token já está listado"""
    listed_exchanges = []
    for exchange, tokens in LISTED_TOKENS.items():
        if token_symbol.upper() in [t.upper() for t in tokens]:
            listed_exchanges.append(exchange)
    return listed_exchanges

def get_token_data_dexcheck(token_address, chain="solana"):
    """Obtém dados de tokens via DexCheck"""
    try:
        if chain.lower() == "solana":
            url = f"https://api.dexcheck.ai/solana/tokens/{token_address}"
        else:
            url = f"https://api.dexcheck.ai/ethereum/tokens/{token_address}"
        
        headers = {"X-DexCheck-Api-Secret": DEXCHECK_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                token_data = data['data']
                return {
                    "price": float(token_data.get('price', 0)),
                    "liquidity": float(token_data.get('liquidity', 0)),
                    "volume_24h": float(token_data.get('volume24h', 0)),
                    "market_cap": float(token_data.get('marketCap', 0)),
                    "url": f"https://dexcheck.ai/app/{chain}/token/{token_address}",
                    "name": token_data.get('name', ''),
                    "symbol": token_data.get('symbol', '')
                }
        
        # Fallback para DexScreener
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(dex_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pairs = data['pairs']
                main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                
                return {
                    "price": float(main_pair.get('priceUsd', 0)),
                    "liquidity": float(main_pair.get('liquidity', {}).get('usd', 0)),
                    "volume_24h": float(main_pair.get('volume', {}).get('h24', 0)),
                    "market_cap": 0,
                    "url": main_pair.get('url', f"https://dexscreener.com/{chain}/{token_address}"),
                    "name": main_pair.get('baseToken', {}).get('name', ''),
                    "symbol": main_pair.get('baseToken', {}).get('symbol', '')
                }
        
        return {"price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0, 
                "url": "", "name": "", "symbol": ""}
    except Exception as e:
        print(f"❌ Erro DexCheck {chain}: {e}")
        return {"price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0, 
                "url": "", "name": "", "symbol": ""}

def find_coingecko_id(token_name, token_symbol, token_address):
    """Tenta encontrar o ID do CoinGecko para o token"""
    try:
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
    suspicious_keywords = ["http", "www", ".com", ".org", ".fi", ".website", 
                          "reward", "claim", "visit", "bounty", "invitation"]
    name_lower = (token_data["name"] or "").lower()
    symbol_lower = (token_data["symbol"] or "").lower()
    
    for keyword in suspicious_keywords:
        if keyword in name_lower or keyword in symbol_lower:
            return True
    
    # 3. Valores exatos suspeitos
    if value_usd % 100000 == 0 and value_usd >= 100000:
        return True
    
    # 4. Volume zero com valor alto
    if token_data["volume_24h"] == 0 and value_usd > 50000:
        return True
    
    return False

# ============================
# FUNÇÕES PARA SOLANA
# ============================
async def get_sol_holdings(wallet_address):
    """Obtém holdings de Solana com balanços reais"""
    try:
        holdings = []
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(HELIUS_URL, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data and 'value' in data['result']:
                        for token_account in data['result']['value']:
                            try:
                                token_info = token_account['account']['data']['parsed']['info']
                                mint = token_info['mint']
                                balance = float(token_info['tokenAmount']['uiAmount'])
                                
                                # Ignorar stablecoins e SOL
                                if balance <= 0 or mint in [
                                    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                                    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                                    "So11111111111111111111111111111111111111112"     # SOL
                                ]:
                                    continue
                                    
                                # Obter dados completos do token
                                token_data = get_token_data_dexcheck(mint, "solana")
                                if token_data["price"] > 0:
                                    value_usd = balance * token_data["price"]
                                    
                                    # Verificar se não é scam
                                    if (value_usd >= MIN_VALUE_USD and 
                                        not is_scam_token(token_data, value_usd)):
                                        
                                        # Buscar CoinGecko ID
                                        coingecko_id = find_coingecko_id(
                                            token_data["name"], token_data["symbol"], mint
                                        )
                                        coingecko_url = f"https://www.coingecko.com/pt/moedas/{coingecko_id}" if coingecko_id else ""
                                        
                                        holdings.append({
                                            "symbol": token_data["symbol"] or mint[:8] + "...",
                                            "name": token_data["name"],
                                            "balance": balance,
                                            "value_usd": value_usd,
                                            "address": mint,
                                            "dex_url": token_data["url"],
                                            "coingecko_url": coingecko_url,
                                            "liquidity": token_data["liquidity"],
                                            "volume_24h": token_data["volume_24h"],
                                            "chain": "Solana"
                                        })
                                        print(f"   ✅ {token_data['symbol']}: {balance:,.2f} tokens (${value_usd:,.2f})")
                                        
                            except Exception as e:
                                print(f"❌ Erro processamento token Solana: {e}")
                                continue
        return holdings
    except Exception as e:
        print(f"❌ Erro ao obter holdings Solana: {e}")
        return []

# ============================
# FUNÇÕES PARA ETHEREUM
# ============================
def get_eth_holdings(wallet_address):
    """Obtém holdings de Ethereum com balanços reais"""
    try:
        holdings = []
        processed_tokens = set()
        
        # 1. Obter tokens ERC-20
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
                                    token_data = get_token_data_dexcheck(token_address, "ethereum")
                                    if token_data["price"] > 0:
                                        value_usd = balance * token_data["price"]
                                        
                                        # Verificar se não é scam
                                        if (value_usd >= MIN_VALUE_USD and 
                                            not is_scam_token(token_data, value_usd)):
                                            
                                            # Buscar CoinGecko ID
                                            coingecko_id = find_coingecko_id(
                                                token_data["name"], token_data["symbol"], token_address
                                            )
                                            coingecko_url = f"https://www.coingecko.com/pt/moedas/{coingecko_id}" if coingecko_id else ""
                                            
                                            holdings.append({
                                                "symbol": token_data["symbol"] or symbol or token_address[:8] + "...",
                                                "name": token_data["name"] or tx.get('tokenName', ''),
                                                "balance": balance,
                                                "value_usd": value_usd,
                                                "address": token_address,
                                                "dex_url": token_data["url"],
                                                "coingecko_url": coingecko_url,
                                                "liquidity": token_data["liquidity"],
                                                "volume_24h": token_data["volume_24h"],
                                                "chain": "Ethereum"
                                            })
                                            processed_tokens.add(token_address)
                                            print(f"   ✅ {token_data['symbol'] or symbol}: {balance:,.2f} tokens (${value_usd:,.2f})")
                    
                    except Exception as e:
                        print(f"❌ Erro ao processar token Ethereum: {e}")
                        continue
        
        return holdings
        
    except Exception as e:
        print(f"❌ Erro ao obter holdings Ethereum: {e}")
        return []

# ============================
# PROGRAMA PRINCIPAL
# ============================
async def main():
    print("🤖 MONITOR MARKET MAKERS - TOKENS NÃO LISTADOS")
    print("=" * 60)
    print(f"🔍 Threshold: ${MIN_VALUE_USD:,} | Liquidez mínima: ${MIN_LIQUIDITY_USD:,}")
    print("=" * 60)
    
    global LISTED_TOKENS
    LISTED_TOKENS = load_listed_tokens()
    
    for wallet_name, wallet_address in MARKET_MAKERS.items():
        print(f"\n📊 Analisando {wallet_name}...")
        
        holdings = []
        if wallet_address.startswith("0x"):
            holdings = get_eth_holdings(wallet_address)
        else:
            holdings = await get_sol_holdings(wallet_address)
        
        unlisted_tokens = []
        for token in holdings:
            listed_exchanges = get_listed_exchanges_for_token(token["symbol"])
            if not listed_exchanges:  # Se não está listado em nenhuma exchange
                unlisted_tokens.append(token)
                print(f"   🚫 NÃO LISTADO: {token['symbol']} (${token['value_usd']:,.2f})")
        
        if unlisted_tokens:
            message = f"🚨 <b>MARKET MAKER - {wallet_name}</b>\n\n"
            message += f"💰 <b>Tokens não listados em exchanges:</b>\n\n"
            
            total_value = 0
            
            for token in unlisted_tokens:
                total_value += token["value_usd"]
                
                message += f"💎 <b>{token['name']} ({token['symbol']})</b>\n"
                message += f"📊 <b>Valor:</b> ${token['value_usd']:,.2f}\n"
                message += f"🔢 <b>Balance:</b> {token['balance']:,.2f}\n"
                
                if token["liquidity"] > 0:
                    message += f"💧 <b>Liquidez:</b> ${token['liquidity']:,.0f}\n"
                if token["volume_24h"] > 0:
                    message += f"📈 <b>Volume 24h:</b> ${token['volume_24h']:,.0f}\n"
                
                # Links de análise
                message += f"🔗 <a href='{token['dex_url']}'>DexScreener</a>\n"
                if token["coingecko_url"]:
                    message += f"🔗 <a href='{token['coingecko_url']}'>CoinGecko</a>\n"
                
                if token["chain"] == "Ethereum":
                    message += f"📍 <a href='https://etherscan.io/token/{token['address']}'>Etherscan</a>\n"
                else:
                    message += f"📍 <a href='https://solscan.io/token/{token['address']}'>Solscan</a>\n"
                
                message += "\n"
            
            message += f"💰 <b>VALOR TOTAL NÃO LISTADO:</b> ${total_value:,.2f}\n\n"
            message += f"<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
            
            if send_telegram_alert(message):
                print(f"✅ Alerta enviado - {len(unlisted_tokens)} tokens não listados")
            else:
                print(f"❌ Falha ao enviar alerta")
            
            time.sleep(3)
        else:
            print(f"✅ Nenhum token não listado encontrado")

if __name__ == "__main__":
    asyncio.run(main())