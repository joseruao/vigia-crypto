# vigia_solana_complete.py
import requests
import time
import json
import sqlite3
import logging
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

DB_FILE = "alerts.db"
# ============================
# CONFIGURAÇÃO (edita conforme preciso)
# ============================
TELEGRAM_BOT_TOKEN = "8350004696:AAGVXDH0hRr9S4EPsuQdwDbrG0Pa1m3i_-U"
TELEGRAM_CHAT_ID = "5239378332"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
LISTED_TOKENS_FILE = "listed_tokens.json"
DB_FILE = "alerts.sqlite"

# Exchanges + wallets (podes adicionar/remover)
EXCHANGE_WALLETS = {
    "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "Binance 3": "8kPLJg9eKSwCoDJjK3CixgB3Mf7i5p2hWQqRgt7F5Xk",
    "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE",
    "Coinbase Hot": "FpwQQhQQoEaVu3WU2qZMfF1hx48YyfwsLoRgXG83E99Q",
    "Bybit": "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
    "Gate.io": "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w",
    "Bitget": "A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR",
    "Kraken Cold 1": "9cNE6KBg2Xmf34FPMMvzDF8yUHMrgLRzBV3vD7b1JnUS",
    "Kraken Cold 2": "F7RkX6Y1qTfBqoX5oHoZEgrG1Dpy55UZ3GfWwPbM58nQ",
    "OKX": "HWpGJNxbQRW5HiwHfL2QwF45vweKD2tSfRo8FwY3SgKp",
    "FTX": "2npR8J6kKgrY2T6VioeS5pbgjRtx6eXG3wJ8kYF8tX9L",
    "MEXC": "H7gyjxzXm7fQ6pfx9WkQqJk4DfjRk7Vc1nG5VcJqJ5qj",
    "Binance 2": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
}

# Insiders / early movers — tratados como "special" (sempre alertar)
SPECIAL_WALLETS = {
    "Alameda Research": "MJKqp326RZCHnAAbew9MDdui3iCKWco7fsK9sVuZTX2",
    "Suspicious Early Mover": "GkPtg9Lt38syNpdBGsNJu4YMkLi5wFXq3PM8PQhxT8ry"
}

# Threshold e API DexScreener
THRESHOLD_USD = 5000
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VigiaSolana")

# ============================
# UTILs de persistência
# ============================


import sqlite3

def init_db():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()

    # Criar tabela se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            exchange TEXT,
            token_symbol TEXT,
            token_mint TEXT,
            value_usd REAL,
            price REAL,
            liquidity REAL,
            count_tx INTEGER,
            pair_url TEXT,
            message TEXT
        )
    """)

    # Verificar colunas existentes
    cur.execute("PRAGMA table_info(alerts)")
    existing_cols = [row[1] for row in cur.fetchall()]

    # Lista de colunas obrigatórias
    required_cols = {
        "source_wallet": "TEXT"
    }

    # Adicionar colunas que faltam
    for col, col_type in required_cols.items():
        if col not in existing_cols:
            print(f"⚡ Adicionando coluna em falta: {col}")
            cur.execute(f"ALTER TABLE alerts ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def save_alert_db(source_wallet, alert_info, total_value, total_count, message):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alerts (ts, source_wallet, exchange, token_symbol, token_mint, value_usd, price, liquidity, count_tx, pair_url, message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), source_wallet, alert_info.get("exchange"), alert_info.get("token_symbol"),
          alert_info.get("token_address"), total_value, alert_info.get("price"), alert_info.get("liquidity"),
          total_count, alert_info.get("pair_url"), message))
    conn.commit()
    conn.close()

# ============================
# Load listed tokens (suporta 2 formatos: exchange->tokens ou token->exchanges)
# ============================
def load_listed_tokens():
    try:
        with open(LISTED_TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Não foi possível carregar {LISTED_TOKENS_FILE}: {e}")
        return {}

def normalize_exchange_name(name):
    # remove dígitos e caracteres não-alfabéticos e torna lowercase
    return re.sub(r'[^a-z]', '', name.lower())

def is_listed_in_data(listed_tokens, token_symbol, exchange_name):
    """
    Aceita listed_tokens em ambos formatos:
    - formato A: { "Binance": ["BTC","ETH", ...], ... }
    - formato B: { "btc": ["Binance","KuCoin"], "ray": ["Binance", ...] }
    Faz normalizações robustas.
    """
    token_sym = token_symbol.upper()
    ex_norm = normalize_exchange_name(exchange_name)

    # Detect format A (keys são exchanges)
    sample_keys = list(listed_tokens.keys())[:5]
    if any(k.lower() in ("binance", "kucoin", "gate", "kraken", "coinbase") for k in sample_keys):
        # formato A
        for ex, tokens in listed_tokens.items():
            if normalize_exchange_name(ex) == ex_norm:
                # tokens podem ser maiúsculos/minúsculos
                if any(token_sym == (t.upper() if isinstance(t, str) else "") for t in tokens):
                    return True
        return False
    else:
        # formato B: top-level keys são tokens -> list of exchanges
        token_key = None
        # procurar chave por symbol case-insensitive
        for k in listed_tokens.keys():
            if str(k).lower() == token_sym.lower():
                token_key = k
                break
        if not token_key:
            return False
        exchanges = listed_tokens.get(token_key) or []
        return any(normalize_exchange_name(e) == ex_norm for e in exchanges)

# ============================
# HTTP helpers
# ============================
def safe_post(url, json_payload=None, timeout=12):
    try:
        r = requests.post(url, json=json_payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            logger.debug(f"POST {url} -> {r.status_code}")
    except Exception as e:
        logger.debug(f"POST {url} -> err {e}")
    return None

def safe_get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            logger.debug(f"GET {url} -> {r.status_code}")
    except Exception as e:
        logger.debug(f"GET {url} -> err {e}")
    return None

# ============================
# Helius / DexScreener helpers
# ============================
def get_recent_transactions(wallet_address, hours=24, limit=200):
    start_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    payload = {
        "jsonrpc": "2.0",
        "id": "vigia-signatures",
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    resp = safe_post(HELIUS_URL, json_payload=payload)
    if not resp:
        return []
    batch = resp.get("result", []) or []
    # filtrar por blockTime
    return [tx for tx in batch if tx.get("blockTime", 0) >= start_time]

def get_transaction_details(signature):
    payload = {
        "jsonrpc": "2.0",
        "id": "vigia-details",
        "method": "getTransaction",
        "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
    }
    return safe_post(HELIUS_URL, json_payload=payload)

def get_dexscreener_data(token_address):
    if not token_address:
        return None
    url = f"{DEXSCREENER_API}{token_address}"
    return safe_get(url)

# ============================
# Análise de transacções
# ============================
def analyze_transaction(tx_data, wallet_address, source_name):
    """Retorna alert_info dict ou None"""
    try:
        if not tx_data or 'result' not in tx_data:
            return None
        result = tx_data['result']
        meta = result.get('meta', {})
        if meta.get('err'):
            return None

        for balance in meta.get('postTokenBalances', []):
            owner = balance.get('owner') or ""
            ui = balance.get('uiTokenAmount', {}) or {}
            amount = ui.get('uiAmount', 0) or 0
            if amount <= 0:
                continue
            # Se o owner não corresponder à wallet, ainda pode ser um depósito: aceitamos
            mint = balance.get('mint')
            dex = get_dexscreener_data(mint)
            if not dex or not dex.get('pairs'):
                continue
            pair = dex['pairs'][0]
            price_usd = pair.get('priceUsd') or pair.get('priceUsd', None)
            if not price_usd:
                continue
            try:
                price = float(price_usd)
            except:
                continue
            value_usd = amount * price
            # filtrar stables/bluechips
            base_token = (pair.get('baseToken') or {}).get('symbol') or 'UNKNOWN'
            if base_token.upper() in {"USDC","USDT","SOL","BTC","ETH"}:
                continue
            # threshold
            if value_usd < THRESHOLD_USD:
                continue
            liquidity = (pair.get('liquidity') or 0) or pair.get('liquidity', {}).get('usd', 0)
            return {
                "exchange": source_name,
                "token_symbol": base_token.upper(),
                "token_address": mint,
                "amount": amount,
                "value_usd": value_usd,
                "price": price,
                "liquidity": liquidity or 0,
                "pair_url": pair.get('url', ''),
                "signature": result.get('transaction', {}).get('signatures', [None])[0],
                "timestamp": result.get('blockTime', int(time.time()))
            }
    except Exception as e:
        logger.debug(f"Erro analyze_transaction: {e}")
    return None

# ============================
# Mensagens / alerts
# ============================
def generate_comment(alert_info, total_value, count):
    if total_value >= 5_000_000:
        return "Grande oportunidade, possível listing 🚨⭐️"
    if total_value >= 1_000_000:
        return "Oportunidade relevante, observar ⚠️"
    return "Estar atento ⚡"

def format_alert(alert_info, total_amount=None, total_value=None, comment=None):
    """
    Formata a mensagem de alerta para envio no Telegram.
    """
    token = alert_info.get("token", "UNKNOWN")
    symbol = alert_info.get("token_symbol", token)
    price = alert_info.get("price", 0)
    amount = total_amount if total_amount is not None else alert_info.get("amount", 0)
    value_usd = total_value if total_value is not None else alert_info.get("value_usd", 0)
    
    liquidity = alert_info.get("liquidity", 0)
    # Se vier como dict, pega no campo USD
    if isinstance(liquidity, dict):
        liquidity = liquidity.get("usd", 0)
    try:
        liquidity = float(liquidity)
    except:
        liquidity = 0

    exchanges_listed = alert_info.get("exchanges_listed", [])
    exchanges_str = ", ".join(exchanges_listed) if exchanges_listed else "Nenhuma"

    message = f"🚨 ⭐️ *Possível listing, {comment or ''}* 🚨\n\n"
    message += f"🏦 Exchange monitorizada: {alert_info.get('exchange_name', 'UNKNOWN')}\n"
    message += f"💎 Token: {token}\n"
    message += f"💰 Valor movimentado: ${value_usd:,.2f}\n"
    message += f"📦 Quantidade: {amount:,.2f} {symbol}\n"
    message += f"💧 Liquidez: ${liquidity:,.0f}\n"
    message += f"📊 Preço: ${price:,.8f}\n"
    message += f"⭐ Comentário: {comment or '—'}\n"
    message += f"🔗 Exchanges listadas: {exchanges_str}\n"
    message += f"🔗 DexScreener: {alert_info.get('dexscreener_link', '—')}\n"
    message += f"🔗 Coingecko: {alert_info.get('coingecko_link', '—')}\n"
    message += f"📝 Transação: {alert_info.get('tx_link', '—')}\n"
    message += f"⏰ Detectado às {alert_info.get('detected_time', '—')}\n"

    return message


def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": False}
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Erro Telegram: {e}")
        return False

# ============================
# MAIN (com suporte a insiders + todas as wallets)
# ============================
def main():
    logger.info("Iniciando Vigia Solana (com listed_tokens check)...")
    init_db()
    listed_tokens = load_listed_tokens()

    # junta exchanges e special wallets — percorre EXCHANGE_WALLETS primeiro, depois SPECIAL_WALLETS
    all_wallets = []
    for k,v in EXCHANGE_WALLETS.items():
        all_wallets.append( (k,v,"exchange") )
    for k,v in SPECIAL_WALLETS.items():
        all_wallets.append( (k,v,"special") )

    while True:
        start_round = time.time()
        total_alerts_round = 0

        for name, address, wtype in all_wallets:
            logger.info(f"=====================================")
            logger.info(f"🔍 Analisando {name} ({wtype}) ...")
            # limitar o número de signatures para não travar com 10k
            txs = get_recent_transactions(address, hours=24, limit=500)
            if not txs:
                logger.info("   ℹ️  Nenhuma transação nas últimas 24h")
                continue

            logger.info(f"   ✅ {len(txs)} transferência(s) nas últimas 24h")
            # buscar details em paralelo
            alert_candidates = []

            with ThreadPoolExecutor(max_workers=8) as exe:
                future_map = { exe.submit(get_transaction_details, tx['signature']): tx for tx in txs }
                for fut in as_completed(future_map):
                    tx_meta = future_map[fut]
                    sig = tx_meta['signature']
                    resp = fut.result()
                    if not resp:
                        continue
                    info = analyze_transaction(resp, address, name)
                    if info:
                        alert_candidates.append(info)

            if not alert_candidates:
                logger.info("   ℹ️  Nenhum token relevante detectado nesta wallet")
                continue

            # agrupar por token_address
            grouped = {}
            for info in alert_candidates:
                key = info['token_address']
                g = grouped.setdefault(key, {"info": info, "total_amount": 0, "total_value": 0, "count": 0})
                g['total_amount'] += info['amount']
                g['total_value'] += info['value_usd']
                g['count'] += 1

            # processar cada grupo
            alerts_found = 0
            for key, g in grouped.items():
                info = g['info']
                total_value = g['total_value']
                total_amount = g['total_amount']
                count = g['count']

                # Se for exchange wallet: verifica se já está listado na exchange monitorizada
                if wtype == "exchange":
                    # normalizar nome da exchange base (ex: "Binance 1" -> "Binance")
                    base_exchange = name.split()[0]
                    listed_flag = is_listed_in_data(listed_tokens, info['token_symbol'], base_exchange)
                    if listed_flag:
                        logger.info(f"   🔹 {info['token_symbol']} já está listado em {name} (skip)")
                        continue
                # se for special wallet: sempre notifica (podes ajustar regras aqui)

                # preparar mensagem
                comment = generate_comment(info, total_value, count)
                msg = format_alert(info, total_amount, total_value, comment)
                # acrescentar exchanges listadas (se tiveres esse ficheiro no formato token->exchanges)
                # opcional: adicionar o coingecko link se preferires

                sent = send_telegram_alert(msg)
                if sent:
                    alerts_found += 1
                    total_alerts_round += 1
                    save_alert_db(name, info, total_value, count, msg)
                    logger.info(f"   🚨 ALERTA enviado: {info['token_symbol']} - ${total_value:,.2f} ({count} txs)")
                else:
                    logger.warning("   ❌ Falha ao enviar alerta Telegram")

                # curtas pausas para não spammar
                time.sleep(0.6)

            if alerts_found == 0:
                logger.info("   ℹ️ Nenhum alerta relevante nesta wallet (após filtros)")

            # pequeno delay antes da próxima wallet para reduzir QPS
            time.sleep(0.5)

        elapsed = time.time() - start_round
        logger.info(f"Round completo. Alertas enviados: {total_alerts_round}. Tempo: {elapsed:.1f}s")
        # dormir antes da ronda seguinte
        time.sleep(30)


if __name__ == "__main__":
    main()


