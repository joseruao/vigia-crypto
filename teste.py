# holdings_checker_final.py
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
TELEGRAM_BOT_TOKEN = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID = "5239378332"

# APIs
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Ficheiro de tokens listados
LISTED_TOKENS_FILE = "listed_tokens.json"

# WALLETS DE EXCHANGES
WALLETS = {
    "Ethereum": {
        "Binance 8": "0xf977814e90da44bfa03b6295a0616a897441acec",
        "Binance 14": "0x564286362092d8e7936f0549571a803b203aaced", 
        "Binance 7": "0x28c6c06298d514db089934071355e5743bf21d60",
        "Kraken": "0xe9f7ecae3a53d2a67105292894676b00d1fab785",
        "OKX 73": "0x2c4b9d9a57d7b6f91e3d6b1a3b4c1d81b37c0c2c",
        "OKX 93": "0x5a52e96bacdabb82fd05763e25335261b270efcb",
    },
    "Solana": {
        "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "Binance 2": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
        "Binance 3": "8kPLJg9eKSwCoDJjK3CixgB3Mf7i5p2hWQqRgt7F5XkR",
        "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE",
    }
}

# THRESHOLD MÍNIMO EM USD
MIN_VALUE_USD = 300000  # $300K

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
        # Fallback básico
        return {
            "Binance": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP", 
                       "ENJ", "BAT", "ZRX", "SNX", "CRV", "1INCH", "YFI", "SUSHI", "REN", "BAL"],
            "Kraken": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR", "COMP"],
            "OKX": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE", "MKR"],
            "Coinbase": ["ETH", "USDT", "USDC", "WBTC", "DAI", "LINK", "UNI", "AAVE"],
        }

def get_listed_exchanges_for_token(token_symbol):
    """Retorna as exchanges onde o token já está listado"""
    listed_exchanges = []
    for exchange, tokens in LISTED_TOKENS.items():
        if token_symbol.upper() in [t.upper() for t in tokens]:
            listed_exchanges.append(exchange)
    return listed_exchanges

def is_token_listed_on_exchange(token_symbol, exchange_name):
    """Verifica se um token está listado em uma exchange específica"""
    # Normalizar nomes das exchanges
    exchange_map = {
        "Binance 8": "Binance", "Binance 14": "Binance", "Binance 7": "Binance",
        "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
        "Kraken": "Kraken",
        "OKX 73": "OKX", "OKX 93": "OKX",
        "Coinbase 1": "Coinbase",
    }
    
    target_exchange = exchange_map.get(exchange_name, exchange_name)
    
    if target_exchange in LISTED_TOKENS:
        listed_tokens = [t.upper() for t in LISTED_TOKENS[target_exchange]]
        return token_symbol.upper() in listed_tokens
    
    return False

def get_token_data_dexcheck(token_address, chain="solana"):
    """Obtém dados de tokens via DexCheck (mais preciso que DexScreener)"""
    try:
        # API do DexCheck para Solana
        if chain.lower() == "solana":
            url = f"https://api.dexcheck.ai/solana/tokens/{token_address}"
            headers = {
                "X-DexCheck-Api-Secret": "lU6WhkxhGnYKSSr86AVVsoE0vYL092Z2"  # Obter em dexcheck.ai
            }
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
                        "url": f"https://dexcheck.ai/app/solana/token/{token_address}",
                        "name": token_data.get('name', ''),
                        "symbol": token_data.get('symbol', '')
                    }
        
        # Fallback para DexScreener se DexCheck falhar
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(dex_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pairs = data['pairs']
                main_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
                
                return {
                    "price": float(main_pair['priceUsd']),
                    "liquidity": float(main_pair.get('liquidity', {}).get('usd', 0)),
                    "volume_24h": float(main_pair.get('volume', {}).get('h24', 0)),
                    "market_cap": 0,
                    "url": main_pair.get('url', f"https://dexscreener.com/solana/{token_address}"),
                    "name": main_pair.get('baseToken', {}).get('name', ''),
                    "symbol": main_pair.get('baseToken', {}).get('symbol', '')
                }
        
        return {"price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0, "url": "", "name": "", "symbol": ""}
    except:
        return {"price": 0, "liquidity": 0, "volume_24h": 0, "market_cap": 0, "url": "", "name": "", "symbol": ""}

# ============================
# FUNÇÕES ESPECÍFICAS POR BLOCKCHAIN
# ============================
async def get_sol_holdings_with_balance(wallet_address):
    """Obtém holdings de Solana com balanços reais"""
    try:
        holdings = []
        
        # Obter tokens via Helius
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {
                    "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                },
                {
                    "encoding": "jsonParsed"
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(HELIUS_URL, json=payload, timeout=20) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'result' in data and 'value' in data['result']:
                        for token_account in data['result']['value']:
                            try:
                                token_info = token_account['account']['data']['parsed']['info']
                                mint = token_info['mint']
                                balance = float(token_info['tokenAmount']['uiAmount'])
                                
                                if balance <= 0:
                                    continue
                                    
                                # Ignorar stablecoins e SOL
                                if mint in ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 
                                          "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                                          "So11111111111111111111111111111111111111112"]:
                                    continue
                                    
                                # Obter dados completos do token
                                token_data = get_token_data_dexcheck(mint, "solana")
                                value_usd = balance * token_data["price"]
                                
                                if value_usd >= MIN_VALUE_USD:
                                    holdings.append({
                                        "symbol": token_data["symbol"] or mint[:8] + "...",
                                        "name": token_data["name"],
                                        "balance": balance,
                                        "value_usd": value_usd,
                                        "address": mint,
                                        "url": token_data["url"],
                                        "liquidity": token_data["liquidity"],
                                        "volume_24h": token_data["volume_24h"],
                                        "market_cap": token_data["market_cap"]
                                    })
                                    
                            except Exception as e:
                                print(f"❌ Erro ao processar token: {e}")
                                continue
        
        return holdings
        
    except Exception as e:
        print(f"❌ Erro ao obter holdings Solana: {e}")
        return []

# ============================
# PROGRAMA PRINCIPAL
# ============================
async def main():
    print("🤖 VERIFICADOR DE HOLDINGS NÃO LISTADOS (>$300K)")
    print("=" * 55)
    
    global LISTED_TOKENS
    LISTED_TOKENS = load_listed_tokens()
    
    print(f"🔍 Procurando tokens não listados com valor > ${MIN_VALUE_USD:,}...")
    
    # Verificar wallets Solana uma por uma e enviar alertas separados
    for wallet_name, wallet_address in WALLETS["Solana"].items():
        print(f"\n📊 Analisando {wallet_name}...")
        holdings = await get_sol_holdings_with_balance(wallet_address)
        
        unlisted_tokens = []
        for token in holdings:
            if not is_token_listed_on_exchange(token["symbol"], wallet_name):
                unlisted_tokens.append(token)
                print(f"   🚫 NÃO LISTADO: {token['symbol']} (${token['value_usd']:,.2f})")
        
        # Enviar alerta para esta wallet se encontrar tokens não listados
        if unlisted_tokens:
            # Agrupar tokens por símbolo
            token_groups = defaultdict(list)
            for token in unlisted_tokens:
                token_groups[token["symbol"]].append(token)
            
            message = f"🚨 <b>HOLDINGS NÃO LISTADOS - {wallet_name}</b>\n\n"
            message += f"💰 <b>Tokens > ${MIN_VALUE_USD:,} não listados na {wallet_name}:</b>\n\n"
            
            total_wallet_value = 0
            
            for symbol, tokens in token_groups.items():
                # Calcular total por token
                total_token_value = sum(token["value_usd"] for token in tokens)
                total_wallet_value += total_token_value
                
                # Obter exchanges onde está listado
                listed_exchanges = get_listed_exchanges_for_token(symbol)
                
                message += f"💎 <b>{symbol}</b>\n"
                message += f"📊 <b>Valor Total:</b> ${total_token_value:,.2f}\n"
                
                if listed_exchanges:
                    message += f"🏪 <b>Listado em:</b> {', '.join(listed_exchanges)}\n"
                else:
                    message += f"🏪 <b>Listado em:</b> Nenhuma exchange major\n"
                
                # Adicionar link do DexCheck
                if tokens[0]["url"]:
                    message += f"🔗 <a href='{tokens[0]['url']}'>Ver no DexCheck</a>\n"
                
                message += f"💧 <b>Liquidez:</b> ${tokens[0]['liquidity']:,.0f}\n"
                message += f"📈 <b>Volume 24h:</b> ${tokens[0]['volume_24h']:,.0f}\n\n"
            
            message += f"💰 <b>VALOR TOTAL NA WALLET:</b> ${total_wallet_value:,.2f}\n\n"
            message += f"<i>⏰ Verificado às {datetime.now().strftime('%H:%M:%S')}</i>"
            
            if send_telegram_alert(message):
                print(f"✅ Alerta enviado para {wallet_name} - {len(token_groups)} tokens")
                print(f"💰 Valor total: ${total_wallet_value:,.2f}")
            else:
                print(f"❌ Falha ao enviar alerta para {wallet_name}")
            
            # Esperar entre alertas para não sobrecarregar o Telegram
            time.sleep(2)
        else:
            print(f"✅ {wallet_name}: Nenhum token não listado encontrado")

if __name__ == "__main__":
    asyncio.run(main())