# vigia_solana_final_v3.py - VERSÃO COM ERRO CORRIGIDO
import requests
import time
import json
from datetime import datetime, timedelta

# ============================
# CONFIGURAÇÃO
# ============================
TELEGRAM_BOT_TOKEN_SOL = "8350004696:AAGVXDH0hRr9S4EPsuQdwDbrG0Pa1m3i_-U"
TELEGRAM_CHAT_ID_SOL = "5239378332"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
LISTED_TOKENS_FILE = "listed_tokens.json"

# WALLETS ATIVAS
EXCHANGE_WALLETS_SOL = {
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

THRESHOLD_USD = 5000
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# ============================
# FUNÇÕES
# ============================

def load_listed_tokens():
    """Carrega tokens listados por exchange"""
    try:
        with open(LISTED_TOKENS_FILE, 'r') as f:
            return json.load(f)
    except:
        # Fallback com algumas exchanges principais
        return {
            "Binance": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH", "W", "JUP", "RAY", "BONK"],
            "Coinbase": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH", "JUP"],
            "Bybit": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH"],
            "Gate.io": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH", "W"],
            "Bitget": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH"],
            "Kraken": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH"],
            "OKX": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH", "W"],
            "MEXC": ["BTC", "ETH", "SOL", "USDC", "USDT", "PYTH"]
        }

LISTED_TOKENS = load_listed_tokens()

def is_token_listed_on_exchange(token_symbol, exchange_name):
    """Verifica se um token está listado em uma exchange específica"""
    # Normalizar nomes das exchanges
    exchange_map = {
        "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
        "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
        "Bybit": "Bybit", 
        "Gate.io": "Gate.io",
        "Bitget": "Bitget",
        "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
        "OKX": "OKX",
        "MEXC": "MEXC"
    }
    
    target_exchange = exchange_map.get(exchange_name, exchange_name)
    
    if target_exchange in LISTED_TOKENS:
        listed_tokens = [t.upper() for t in LISTED_TOKENS[target_exchange]]
        return token_symbol.upper() in listed_tokens
    
    return False

def send_telegram_alert_sol(message):
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
        return response.status_code == 200
    except:
        return False

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
    except:
        return None

def get_dexscreener_data_solana(token_address):
    """Obtém dados do DexScreener"""
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                return data['pairs'][0]
        return None
    except:
        return None

def get_recent_transactions(wallet_address, hours=24):
    """Obtém transações recentes"""
    try:
        start_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-signatures",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 50}]  # CORREÇÃO AQUI: wallet_address correto
        }
        response = requests.post(HELIUS_URL, json=payload, timeout=15)
        if response.status_code != 200:
            return []
        data = response.json()
        if "error" in data or not data.get('result'):
            return []

        recent_transactions = []
        for tx in data['result']:
            if tx.get('blockTime', 0) >= start_timestamp:
                recent_transactions.append(tx)
        return recent_transactions
    except Exception as e:
        print(f"❌ Erro ao buscar transações: {e}")
        return []

def analyze_transaction(tx_data, wallet_address, exchange_name):
    """Analisa a transação e retorna alerta se relevante"""
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
            if amount <= 0:
                continue
            mint_address = balance.get('mint')
            dex_data = get_dexscreener_data_solana(mint_address)
            if not dex_data or not dex_data.get('priceUsd'):
                continue
            price = float(dex_data['priceUsd'])
            value_usd = amount * price
            token_symbol = dex_data.get('baseToken', {}).get('symbol', 'UNKNOWN')
            
            # Ignorar stablecoins e tokens principais
            if token_symbol in ["USDC", "USDT", "SOL", "BTC", "ETH"]:
                continue
            
            # 🔹 CORREÇÃO: Verificar se o token já está listado na PRÓPRIA exchange
            if is_token_listed_on_exchange(token_symbol, exchange_name):
                print(f"   ⚠️  {token_symbol} já listado em {exchange_name} - Ignorando")
                continue
            
            if value_usd < THRESHOLD_USD:
                continue

            # Verificar se está listado em outras exchanges
            listed_exchanges = []
            for ex, tokens in LISTED_TOKENS.items():
                if ex.lower() != exchange_name.lower() and token_symbol.upper() in [t.upper() for t in tokens]:
                    listed_exchanges.append(ex)

            special_flag = any(wallet_address == w for w in SPECIAL_WALLETS.values())

            return {
                "exchange": exchange_name,
                "token": token_symbol,
                "token_address": mint_address,
                "amount": amount,
                "value_usd": value_usd,
                "price": price,
                "liquidity": dex_data.get('liquidity', {}).get('usd', 0),
                "pair_url": dex_data.get('url', ''),
                "signature": result['transaction']['signatures'][0],
                "timestamp": result.get('blockTime', int(time.time())),
                "listed_exchanges": listed_exchanges,
                "special": special_flag
            }
        return None
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def format_alert(alert_info, total_amount=None, total_value=None):
    """Formata alerta para Telegram"""
    message = ""

    if alert_info['special']:
        message += "🐋💥🚨 <b>WHALE / INSIDER ALERT!</b> 🐋💥🚨\n\n"
    elif not alert_info['listed_exchanges']:
        message += "🎺🚀 <b>POSSÍVEL NOVO LISTING!</b> 🎺🚀\n\n"
    elif total_amount and total_value and total_value > THRESHOLD_USD*2:
        message += "🔥 <b>ALTA PROBABILIDADE DE LISTING!</b> 🔥\n\n"
    else:
        message += "🔔 <b>Movimentação relevante</b>\n\n"

    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    if total_amount and total_value:
        message += f"💰 <b>Valor Total:</b> ${total_value:,.2f}\n"
        message += f"📦 <b>Quantidade Total:</b> {total_amount:,.2f}\n"
    else:
        message += f"💰 <b>Valor:</b> ${alert_info['value_usd']:,.2f}\n"
        message += f"📦 <b>Quantidade:</b> {alert_info['amount']:,.2f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info['price']:.8f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.0f}\n\n"

    if alert_info.get('pair_url'):
        message += f"🔗 <a href='{alert_info['pair_url']}'>Ver no DexScreener</a>\n"
        message += f"🌐 <a href='https://www.coingecko.com/en/coins/{alert_info['token'].lower()}'>Ver no Coingecko</a>\n\n"

    if alert_info['listed_exchanges']:
        message += f"💹 <b>Já listado em:</b> {', '.join(alert_info['listed_exchanges'])}\n"
    else:
        message += f"🆕 <b>NOVO TOKEN - Não listado em nenhuma exchange major!</b>\n"

    message += f"<i>⏰ Detectado às {datetime.fromtimestamp(alert_info['timestamp']).strftime('%H:%M:%S')}</i>"

    return message

# ============================
# PROGRAMA PRINCIPAL
# ============================
def main():
    print("🤖 VIGILANTE SOLANA - VERSÃO CORRIGIDA")
    print("=" * 55)
    total_alerts = 0

    for exchange_name, wallet_address in EXCHANGE_WALLETS_SOL.items():
        print(f"🔍 Analisando {exchange_name}...")
        transactions = get_recent_transactions(wallet_address, hours=48)

        if not transactions:
            print(f"   ℹ️  Nenhuma transação recente")
            continue

        print(f"   ✅ {len(transactions)} transações encontradas")

        # Agrupar transações por token
        token_alerts = {}
        for tx in transactions:
            signature = tx['signature']
            tx_details = get_transaction_details(signature)
            if not tx_details:
                continue
            alert_info = analyze_transaction(tx_details, wallet_address, exchange_name)
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
                message = format_alert(alert_info, data['total_amount'], data['total_value'])
                message += f"\n📊 <b>Transações agrupadas:</b> {data['count']}"
            else:
                message = format_alert(alert_info)

            if send_telegram_alert_sol(message):
                print(f"   🚨 ALERTA: {alert_info['token']} - ${data['total_value']:,.2f} ({data['count']} transações)")
                alerts_found += 1
                total_alerts += 1
                time.sleep(1)

        if alerts_found == 0:
            print(f"   ℹ️  Nenhum alerta significativo")

    print(f"\n🎯 Total de alertas: {total_alerts}")

if __name__ == "__main__":
    main()