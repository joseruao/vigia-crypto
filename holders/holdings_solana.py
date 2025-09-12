# holdings_solana.py
import requests
import time
import json
import asyncio
import aiohttp
from datetime import datetime
from collections import defaultdict

# Configuração
TELEGRAM_BOT_TOKEN = "7999197151:AAELAI64aNx2nVk-Uhp-20YAxrXlXbVFzjw"
TELEGRAM_CHAT_ID = "5239378332"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
LISTED_TOKENS_FILE = "listed_tokens.json"
MIN_VALUE_USD = 300000

# Wallets Solana prioritárias (mais rápidas de analisar)
SOLANA_WALLETS = {
   # "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    #"Binance 2": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
   # "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE",
   # "Kraken Cold 1": "9cNE6KBg2Xmf34FPMMvzDF8yUHMrgLRzBV3vD7b1JnUS",
    "Gate.io": "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w",
  #  "Bybit": "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
}

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except:
        return False

def load_listed_tokens():
    try:
        with open(LISTED_TOKENS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"Binance": ["SOL", "USDC", "USDT", "BONK", "JUP", "WIF", "RAY", "ORCA"]}

def get_token_data_dexcheck(token_address):
    try:
        url = f"https://api.dexcheck.ai/solana/tokens/{token_address}"
        headers = {"X-DexCheck-Api-Secret": "lU6WhkxhGnYKSSr86AVVsoE0vYL092Z2"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {})
        return {}
    except:
        return {}

async def get_sol_holdings(wallet_address, wallet_name):
    try:
        holdings = []
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
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
                                
                                if balance <= 0 or mint in ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "So11111111111111111111111111111111111111112"]:
                                    continue
                                    
                                token_data = get_token_data_dexcheck(mint)
                                price = float(token_data.get('price', 0))
                                value_usd = balance * price
                                
                                if value_usd >= MIN_VALUE_USD:
                                    symbol = token_data.get('symbol', mint[:8] + '...')
                                    holdings.append({
                                        "symbol": symbol, "balance": balance, "value_usd": value_usd,
                                        "address": mint, "liquidity": float(token_data.get('liquidity', 0)),
                                        "volume_24h": float(token_data.get('volume24h', 0))
                                    })
                            except:
                                continue
        return holdings
    except:
        return []

async def analyze_wallet(wallet_name, wallet_address):
    print(f"🔍 Analisando {wallet_name}...")
    holdings = await get_sol_holdings(wallet_address, wallet_name)
    
    if not holdings:
        return
    
    unlisted_tokens = []
    for token in holdings:
        if not any(token['symbol'].upper() in [t.upper() for t in load_listed_tokens().get('Binance', [])]):
            unlisted_tokens.append(token)
    
    if unlisted_tokens:
        message = f"🚨 <b>SOLANA - {wallet_name}</b>\n\n"
        total_value = 0
        
        for token in unlisted_tokens:
            total_value += token['value_usd']
            message += f"💎 {token['symbol']}: {token['balance']:,.0f} tokens (${token['value_usd']:,.2f})\n"
            message += f"   💧 Liquidez: ${token['liquidity']:,.0f}\n\n"
        
        message += f"💰 <b>Total: ${total_value:,.2f}</b>\n"
        message += f"<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
        
        send_telegram_alert(message)
        print(f"✅ Alerta enviado para {wallet_name}")

async def main():
    print("🤖 MONITOR SOLANA - INICIADO")
    
    for wallet_name, wallet_address in SOLANA_WALLETS.items():
        await analyze_wallet(wallet_name, wallet_address)
        time.sleep(2)  # Pequeno delay entre wallets
    
    print("✅ Análise Solana concluída")

if __name__ == "__main__":
    asyncio.run(main())