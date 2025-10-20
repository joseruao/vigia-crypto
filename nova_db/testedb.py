# exchange_tokens_to_supabase_enhanced.py
import requests
import time
import json

# -----------------------------
# Configuração Supabase (SEM supabase-py)
# -----------------------------
SUPABASE_URL = "https://qynnajpvxnqcmkzrhpde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjMsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw"

# Headers para Supabase REST API
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def supabase_query(table, query_params=None):
    """Faz query à Supabase usando REST API"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = requests.get(url, headers=SUPABASE_HEADERS, params=query_params, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"❌ Erro Supabase query: {response.status_code}")
        return []
    except Exception as e:
        print(f"❌ Erro Supabase query: {e}")
        return []

def supabase_insert(table, data):
    """Insere dados na Supabase usando REST API"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = requests.post(url, headers=SUPABASE_HEADERS, json=data, timeout=10)
        if response.status_code in [200, 201, 204]:
            return True
        print(f"❌ Erro Supabase insert: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ Erro Supabase insert: {e}")
        return False

def supabase_upsert(table, data, conflict_columns):
    """Upsert na Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = SUPABASE_HEADERS.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        # Adicionar on_conflict como query parameter
        conflict_str = ",".join(conflict_columns)
        url += f"?on_conflict={conflict_str}"
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [200, 201, 204]:
            return True
        print(f"❌ Erro Supabase upsert: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ Erro Supabase upsert: {e}")
        return False

# -----------------------------
# Funções de coleta por exchange (MANTIDAS)
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
                    cleaned = base
                    if cleaned.startswith(('X','Z')) and len(cleaned) > 3:
                        cleaned = ''.join([c for c in cleaned if c.isalpha()])
                    cleaned = cleaned.replace('^', '')
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
            tokens = []
            for s in data:
                s = (s or "").upper()
                for suffix in ("USD","USDT","USDC","ETH","BTC"):
                    if s.endswith(suffix):
                        tokens.append(s[:-len(suffix)])
                        break
            return list({t for t in tokens if t})
    except Exception as e:
        print("   ❌ Erro Gemini:", e)
    return []

# -----------------------------
# Função para enviar ao Supabase
# -----------------------------
def send_to_supabase(exchange: str, token: str):
    token = (token or "").strip()
    if not token:
        return
    token = token.upper()
    
    try:
        # Verificar se já existe
        query_params = {
            "exchange": f"eq.{exchange}",
            "token": f"eq.{token}"
        }
        existing = supabase_query("exchange_tokens", query_params)
        
        if existing:
            print(f"⏭️  Já existe: {exchange} - {token}")
            return
        
        # Inserir novo
        data = {"exchange": exchange, "token": token}
        if supabase_insert("exchange_tokens", data):
            print(f"✅ Inserido: {exchange} - {token}")
        else:
            print(f"❌ Erro ao inserir {exchange} - {token}")
            
    except Exception as e:
        print(f"❌ Exception ao inserir {exchange} - {token}: {e}")

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
    ]

    print("🚀 INICIANDO ATUALIZAÇÃO DE TOKENS LISTADOS")
    print("==================================================")

    for name, func in exchanges:
        print(f"📊 Buscando {name}...")
        start = time.time()
        try:
            tokens = func()
            elapsed = time.time() - start
            print(f"   ✅ {len(tokens)} tokens encontrados ({elapsed:.1f}s)")
            
            # Inserir tokens (limitar a 1000 por exchange para não sobrecarregar)
            tokens = tokens[:1000]
            for i, token in enumerate(tokens):
                send_to_supabase(name, token)
                if i % 50 == 0:  # Pequena pausa a cada 50 tokens
                    time.sleep(0.3)
                    
        except Exception as e:
            print(f"   ❌ Erro em {name}: {e}")
        
        time.sleep(1)  # Pausa entre exchanges

    print("==================================================")
    print("🎯 ATUALIZAÇÃO CONCLUÍDA")

if __name__ == "__main__":
    main()