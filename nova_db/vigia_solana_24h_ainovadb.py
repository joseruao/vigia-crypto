import requests
import time
from datetime import datetime, timedelta
from supabase import create_client, Client

# ============================
# CONFIGURAÇÃO
# ============================
TELEGRAM_BOT_TOKEN_SOL = "8350004696:AAGVXDH0hRr9S4EPsuQdwDbrG0Pa1m3i_-U"
TELEGRAM_CHAT_ID_SOL = "5239378332"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
THRESHOLD_USD = 5000

SUPABASE_URL = "https://qynnajpvxnqcmkzrhpde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# WALLETS / SPECIAL WALLETS
# ============================
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

# ============================
# LISTED TOKENS CACHE (pode vir de Supabase)
# ============================
LISTED_TOKENS = {}  # {'Binance': ['SOL','USDC'], ...}

def load_listed_tokens_from_supabase():
    global LISTED_TOKENS
    try:
        data = supabase.table("exchange_tokens").select("*").execute()
        if hasattr(data, "data") and data.data:
            temp = {}
            for row in data.data:
                ex = row['exchange']
                tok = row['token']
                temp.setdefault(ex, []).append(tok)
            LISTED_TOKENS = temp
            print(f"✅ Tokens carregados do Supabase: {sum(len(v) for v in temp.values())} tokens em {len(temp)} exchanges")
    except Exception as e:
        print(f"❌ Erro ao carregar tokens listados: {e}")

# ============================
# FUNÇÕES AUXILIARES
# ============================

def is_token_listed_on_exchange(token_symbol, exchange_name):
    """Verifica se token já existe na exchange específica"""
    return token_symbol.upper() in [t.upper() for t in LISTED_TOKENS.get(exchange_name, [])]

def get_listed_exchanges(token_symbol, exclude_exchange=None):
    """Retorna lista de exchanges onde o token está listado, exceto a exchange atual"""
    token_upper = token_symbol.upper()
    exchanges = []
    for ex, tokens in LISTED_TOKENS.items():
        if ex.lower() == (exclude_exchange or "").lower():
            continue
        if token_upper in [t.upper() for t in tokens]:
            exchanges.append(ex)
    return exchanges

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
    except Exception as e:
        return None

def get_transaction_details(signature):
    """Obtém detalhes de transação via Helius"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-details",
            "method": "getTransaction",
            "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        }
        response = requests.post(HELIUS_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_recent_transactions(wallet_address, hours=24):
    """Obtém transações recentes via Helius"""
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
            if not dex_data or not isinstance(dex_data, dict):
                continue
            price_str = dex_data.get('priceUsd')
            if not price_str:
                continue
            price = float(price_str)
            value_usd = amount * price
            token_symbol = dex_data.get('baseToken', {}).get('symbol', 'UNKNOWN')

            # Ignorar stablecoins e tokens principais
            if token_symbol in ["USDC", "USDT", "SOL", "BTC", "ETH"]:
                continue

            # Verifica se já listado na exchange
            if is_token_listed_on_exchange(token_symbol, exchange_name):
                print(f"   ⚠️  {token_symbol} já listado em {exchange_name} - Ignorando")
                continue

            if value_usd < THRESHOLD_USD:
                continue

            listed_exchanges = get_listed_exchanges(token_symbol, exclude_exchange=exchange_name)
            special_flag = wallet_address in SPECIAL_WALLETS.values()

            return {
                "exchange": exchange_name,
                "token": token_symbol,
                "token_address": mint_address,
                "amount": amount,
                "value_usd": value_usd,
                "price": price,
                "liquidity": dex_data.get('liquidity', {}).get('usd', 0),
                "pair_url": dex_data.get('url', ''),
                "signature": result.get('transaction', {}).get('signatures', [None])[0],
                "timestamp": result.get('blockTime', int(time.time())),
                "listed_exchanges": listed_exchanges,
                "special": special_flag
            }
        return None
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

def save_transaction_supabase(alert_info):
    """Insere ou ignora transacao na tabela transacted_tokens"""
    try:
        payload = {
            "exchange": alert_info.get("exchange"),
            "token": alert_info.get("token"),
            "token_address": alert_info.get("token_address"),
            "signature": alert_info.get("signature"),
            "amount": alert_info.get("amount"),
            "value_usd": alert_info.get("value_usd"),
            "price": alert_info.get("price"),
            "liquidity": alert_info.get("liquidity"),
            "pair_url": alert_info.get("pair_url"),
            "listed_exchanges": alert_info.get("listed_exchanges", []),
            "special": alert_info.get("special", False),
            "ts": datetime.fromtimestamp(alert_info.get("timestamp", int(time.time()))).isoformat()
        }
        res = supabase.table("transacted_tokens").upsert(payload, on_conflict="token_address,signature").execute()
        err = getattr(res, "error", None)
        if err:
            serr = str(err).lower()
            if "duplicate" in serr or "23505" in serr:
                return True
            print(f"❌ Exceção ao salvar transação: {err}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exceção ao salvar transação: {e}")
        return False

def format_alert(alert_info):
    """Formata alerta para Telegram"""
    message = ""
    if alert_info['special']:
        message += "🐋💥🚨 <b>WHALE / INSIDER ALERT!</b> 🐋💥🚨\n\n"
    elif not alert_info['listed_exchanges']:
        message += "🎺🚀 <b>POSSÍVEL NOVO LISTING!</b> 🎺🚀\n\n"
    else:
        message += "🔔 <b>Movimentação relevante</b>\n\n"

    message += f"🏦 <b>Exchange:</b> {alert_info['exchange']}\n"
    message += f"💎 <b>Token:</b> {alert_info['token']}\n"
    message += f"💰 <b>Valor:</b> ${alert_info['value_usd']:,.2f}\n"
    message += f"📦 <b>Quantidade:</b> {alert_info['amount']:,.2f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info['price']:.8f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info['liquidity']:,.0f}\n\n"
    if alert_info.get('pair_url'):
        message += f"🔗 <a href='{alert_info['pair_url']}'>Ver no DexScreener</a>\n"
    if alert_info['listed_exchanges']:
        message += f"💹 <b>Já listado em:</b> {', '.join(alert_info['listed_exchanges'])}\n"
    else:
        message += f"🆕 <b>NOVO TOKEN - Não listado em nenhuma exchange major!</b>\n"
    message += f"<i>⏰ Detectado às {datetime.fromtimestamp(alert_info['timestamp']).strftime('%H:%M:%S')}</i>"
    return message

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
        if response.status_code != 200:
            print(f"❌ Erro Telegram ({response.status_code}): {response.text}")
            return False
        result = response.json()
        if not result.get("ok"):
            print(f"❌ Telegram rejeitou: {result}")
            return False
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar para Telegram: {e}")
        return False

# ============================
# LOOP PRINCIPAL
# ============================

def main():
    print("🤖 VIGILANTE SOLANA - VERSÃO SUPABASE INTEGRADA")
    print("============================================================")

    load_listed_tokens_from_supabase()

    for exchange, wallet in EXCHANGE_WALLETS_SOL.items():
        print(f"🔍 Analisando {exchange}...")
        transactions = get_recent_transactions(wallet)
        print(f"   ✅ {len(transactions)} transações encontradas")
        for tx in transactions:
            tx_data = get_transaction_details(tx['signature'])
            alert = analyze_transaction(tx_data, wallet, exchange)
            if not alert:
                continue
            if save_transaction_supabase(alert):
                msg = format_alert(alert)
                send_telegram_alert_sol(msg)

if __name__ == "__main__":
    main()
