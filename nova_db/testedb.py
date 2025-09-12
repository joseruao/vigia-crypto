# exchange_tokens_to_supabase_enhanced.py
import requests
import time
import json
from supabase import create_client, Client

# -----------------------------
# Configuração Supabase (coloca a tua key aqui OU usa uma variável de ambiente)
# -----------------------------
SUPABASE_URL = "https://qynnajpvxnqcmkzrhpde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Funções de coleta por exchange
# -----------------------------
def fetch_binance_tokens():
    try:
        r = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({s['baseAsset'].upper() for s in data.get('symbols', []) if s.get('status') == 'TRADING' and s.get('baseAsset')})
    except Exception as e:
        print("   ❌ Erro Binance:", e)
    return []

def fetch_coinbase_tokens():
    try:
        r = requests.get("https://api.exchange.coinbase.com/products", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(p.get('base_currency') or "").upper() for p in data if p.get('status') == 'online'})
    except Exception as e:
        print("   ❌ Erro Coinbase:", e)
    return []

def fetch_kucoin_tokens():
    try:
        r = requests.get("https://api.kucoin.com/api/v1/symbols", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(s.get('baseCurrency') or "").upper() for s in data.get('data', []) if s.get('enableTrading')})
    except Exception as e:
        print("   ❌ Erro KuCoin:", e)
    return []

def fetch_okx_tokens():
    try:
        r = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SPOT", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(s.get('baseCcy') or "").upper() for s in data.get('data', []) if s.get('state') == 'live'})
    except Exception as e:
        print("   ❌ Erro OKX:", e)
    return []

def fetch_mexc_tokens():
    try:
        r = requests.get("https://www.mexc.com/open/api/v2/market/symbols", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(item.get('base_currency') or "").upper() for item in data.get('data', []) if item.get('base_currency')})
    except Exception as e:
        print("   ❌ Erro MEXC:", e)
    return []

def fetch_gateio_tokens():
    try:
        r = requests.get("https://api.gateio.ws/api/v4/spot/currency_pairs", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(i.get('base') or "").upper() for i in data if i.get('trade_status') == 'tradable'})
    except Exception as e:
        print("   ❌ Erro Gate.io:", e)
    return []

def fetch_bitget_tokens():
    try:
        r = requests.get("https://api.bitget.com/api/v2/spot/public/symbols", timeout=15)
        if r.status_code == 200:
            data = r.json()
            return list({(i.get('baseCoin') or "").upper() for i in data.get('data', []) if i.get('status') == 'online'})
    except Exception as e:
        print("   ❌ Erro Bitget:", e)
    return []

def fetch_bybit_tokens():
    try:
        r = requests.get("https://api.bybit.com/v5/market/instruments-info?category=spot", timeout=15)
        if r.status_code == 200:
            data = r.json()
            lst = data.get('result', {}).get('list', [])
            return list({(i.get('baseCoin') or "").upper() for i in lst if i.get('status') == 'Trading'})
    except Exception as e:
        print("   ❌ Erro Bybit:", e)
    return []

def fetch_kraken_tokens():
    try:
        r = requests.get("https://api.kraken.com/0/public/AssetPairs", timeout=15)
        if r.status_code == 200:
            pairs = r.json().get('result', {})
            tokens = []
            for p in pairs.values():
                base = p.get('base')
                if base:
                    # Kraken usa X... e Z... prefixos para some assets; tentamos normalizar
                    # remove leading X or Z if followed by 3-5 letters, ex: XBTC -> BTC
                    cleaned = base
                    if cleaned.startswith(('X','Z')) and len(cleaned) > 3:
                        # remove leading X/Z chars until letters found
                        cleaned = ''.join([c for c in cleaned if c.isalpha()])
                    cleaned = cleaned.replace('^', '')  # precaution
                    if 1 < len(cleaned) <= 10:
                        tokens.append(cleaned.upper())
            return list(set(tokens))
    except Exception as e:
        print("   ❌ Erro Kraken:", e)
    return []

def fetch_crypto_com_tokens():
    try:
        r = requests.get("https://api.crypto.com/v2/public/get-ticker", timeout=15)
        if r.status_code == 200:
            instruments = r.json().get('result', {}).get('data', [])
            return list({(i.get('i','').split('_')[0] or "").upper() for i in instruments if i.get('i') and '_' in i.get('i')})
    except Exception as e:
        print("   ❌ Erro Crypto.com:", e)
    return []

def fetch_huobi_tokens():
    try:
        r = requests.get("https://api.huobi.pro/v1/common/symbols", timeout=15)
        if r.status_code == 200:
            data = r.json().get('data', [])
            return list({(d.get('symbol','').split('_')[0] or "").upper() for d in data if d.get('symbol')})
    except Exception as e:
        print("   ❌ Erro Huobi:", e)
    return []

def fetch_gemini_tokens():
    try:
        r = requests.get("https://api.gemini.com/v1/symbols", timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Gemini symbols like 'btcusd' -> take prefix base
            tokens = []
            for s in data:
                s = (s or "").upper()
                # heurística: if contains USD/USDT/ETH etc, split by those suffixes
                for suffix in ("USD","USDT","USDC","ETH","BTC"):
                    if s.endswith(suffix):
                        tokens.append(s[:-len(suffix)])
                        break
            return list({t for t in tokens if t})
    except Exception as e:
        print("   ❌ Erro Gemini:", e)
    return []

#def fetch_bittrex_tokens():
    try:
        r = requests.get("https://api.bittrex.com/v3/markets", timeout=15)
        if r.status_code == 200:
            data = r.json()
            # markets like 'BTC-USD' => base is left of hyphen
            return list({(item.get('symbol') or "").split('-')[0].upper() for item in data if item.get('symbol')})
    except Exception as e:
        print("   ❌ Erro Bittrex:", e)
    return []

# -----------------------------
# Função para enviar ao Supabase (robusta)
# -----------------------------
def send_to_supabase(exchange: str, token: str):
    token = (token or "").strip()
    if not token:
        return
    token = token.upper()
    data = {
        "exchange": exchange,
        "token": token,
        "signature": None
    }
    try:
        # upsert on the unique constraint (exchange, token) — a constraint deve existir no DB
        res = supabase.table("exchange_tokens").upsert(data, on_conflict="exchange,token").execute()
        err = getattr(res, "error", None)
        if err:
            print(f"❌ Erro ao inserir {exchange} - {token}: {err}")
        else:
            print(f"✅ Inserido: {exchange} - {token}")
    except Exception as e:
        print(f"❌ Erro ao inserir {exchange} - {token}: {e}")

# -----------------------------
# Execução principal
# -----------------------------
def main():
    exchanges = [
        ("Binance", fetch_binance_tokens),
        ("Coinbase", fetch_coinbase_tokens),
        ("KuCoin", fetch_kucoin_tokens),
        ("OKX", fetch_okx_tokens),
        ("MEXC", fetch_mexc_tokens),
        ("Gate.io", fetch_gateio_tokens),
        ("Bitget", fetch_bitget_tokens),
        ("Bybit", fetch_bybit_tokens),
        ("Kraken", fetch_kraken_tokens),
        ("Crypto.com", fetch_crypto_com_tokens),
        ("Huobi", fetch_huobi_tokens),
        ("Gemini", fetch_gemini_tokens),
      #  ("Bittrex", fetch_bittrex_tokens),
    ]

    for name, func in exchanges:
        print("==================================================")
        print(f"📊 Buscando {name}...")
        start = time.time()
        tokens = func()
        elapsed = time.time() - start
        print(f"   ✅ {len(tokens)} tokens ({elapsed:.1f}s)")

        for token in tokens:
            send_to_supabase(name, token)
        # pequena pausa para não sobrecarregar APIs
        time.sleep(0.8)

if __name__ == "__main__":
    main()

