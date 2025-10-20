import requests
import time
import json
import asyncio
from datetime import datetime
import os
# ===========================
# CONFIGURAÇÃO
# ===========================
SUPABASE_URL = "https://qynnajpvxnqcmkzrhpde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc0Mzg4NjCsImV4cCI6MjA3MzAxNDg2M30.M30wZ79mQz2i3verO9JtyMn7JVE3yW1FjtcFJlnTvaw"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
ETHERSCAN_API_KEY = "Y14X9JDHZY5QM3RV51GE2V8M6XSTWBNTYW"

# Headers para Supabase REST API
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===========================
# THRESHOLDS REALISTAS
# ===========================
HOLDING_THRESHOLDS = {
    # SOLANA WALLETS
    "Binance 1": 500000,      # $500k+
    "Binance 2": 500000,      # $500k+
    "Binance 3": 500000,      # $500k+
    "Coinbase 1": 300000,     # $300k+
    "Coinbase Hot": 300000,   # $300k+
    "OKX": 200000,            # $200k+
    "Gate.io": 150000,        # $150k+
    "Bybit": 150000,          # $150k+
    "Kraken Cold 1": 100000,  # $100k+
    "Kraken Cold 2": 100000,  # $100k+
    "Bitget": 100000,         # $100k+
    "MEXC": 50000,            # $50k+
    
    # ETHEREUM WALLETS
    "Binance 8": 500000,      # $500k+
    "Binance 14": 500000,     # $500k+
    "Binance 7": 500000,      # $500k+
    "Binance 16": 500000,     # $500k+
    "Kraken": 300000,         # $300k+
    "OKX 73": 200000,         # $200k+
    "OKX 93": 200000,         # $200k+
    "Coinbase 10": 300000,    # $300k+
    "Gate.io": 150000,        # $150k+
    "Bitget Hot Wallet 1": 100000, # $100k+
    "Bitfinex 2": 150000,     # $150k+
    "Bitfinex 19": 150000,    # $150k+
    "Gemini 3": 100000,       # $100k+
    "Robinhood": 200000,      # $200k+
    "Upbit": 150000,          # $150k+
}

MIN_LIQUIDITY = 2000000  # $2M+ liquidez mínima
MIN_VOLUME_24H = 500000  # $500k+ volume mínimo
MIN_SCORE_ALERT = 80     # Score mínimo para alerta

# ===========================
# WALLETS
# ===========================
SOLANA_WALLETS = {
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
    "MEXC": "H7gyjxzXm7fQ6pfx9WkQqJk4DfjRk7Vc1nG5VcJqJ5qj"
}

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

# ===========================
# MONITORIZAÇÃO E RESILIÊNCIA
# ===========================
class WorkerMetrics:
    def __init__(self):
        self.start_time = None
        self.wallets_processed = 0
        self.holdings_found = 0
        self.holdings_saved = 0
        self.errors = 0
    
    def start(self):
        self.start_time = datetime.now()
    
    def get_summary(self):
        if not self.start_time:
            return "Worker não iniciado"
        
        duration = datetime.now() - self.start_time
        return {
            "duration": str(duration),
            "wallets_processed": self.wallets_processed,
            "holdings_found": self.holdings_found,
            "holdings_saved": self.holdings_saved,
            "errors": self.errors,
            "success_rate": f"{(self.holdings_saved/max(self.holdings_found,1))*100:.1f}%"
        }

# Instância global de métricas
metrics = WorkerMetrics()

# ===========================
# FUNÇÕES DE RESILIÊNCIA
# ===========================
async def safe_api_call(func, *args, max_retries=3, delay=2, **kwargs):
    """Executa chamadas de API com retry e backoff"""
    for attempt in range(max_retries):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = delay * (2 ** attempt)  # Exponential backoff
            print(f"   ⚠️  Tentativa {attempt + 1} falhou, retry em {wait_time}s: {e}")
            await asyncio.sleep(wait_time)

def validate_holding_data(holding_data):
    """Valida dados do holding antes de guardar"""
    required_fields = ['symbol', 'value_usd', 'liquidity', 'score']
    
    for field in required_fields:
        if field not in holding_data:
            return False
    
    # Validar valores
    if (holding_data['value_usd'] <= 0 or 
        holding_data['liquidity'] <= 0 or
        holding_data['score'] < 0 or holding_data['score'] > 100):
        return False
    
    return True

# ===========================
# FUNÇÕES SUPABASE
# ===========================
def supabase_query(table, query_params=None):
    """Faz query à Supabase usando REST API"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = requests.get(url, headers=SUPABASE_HEADERS, params=query_params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"❌ Erro Supabase query: {e}")
        return []

def supabase_insert(table, data):
    """Insere dados na Supabase usando REST API"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = requests.post(url, headers=SUPABASE_HEADERS, json=data, timeout=10)
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"❌ Erro Supabase insert: {e}")
        return False

def supabase_upsert(table, data, conflict_columns):
    """Upsert na Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = SUPABASE_HEADERS.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        conflict_str = ",".join(conflict_columns)
        url += f"?on_conflict={conflict_str}"
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"❌ Erro Supabase upsert: {e}")
        return False

# ===========================
# FUNÇÕES DE DADOS
# ===========================
def get_token_data_dexscreener(token_address, chain=None):
    """Busca dados do token no DexScreener"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            if pairs:
                # Escolher o par com maior liquidez
                best_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)))
                
                # Extrair dados de forma segura
                liquidity_data = best_pair.get('liquidity', {})
                volume_data = best_pair.get('volume', {})
                price_change_data = best_pair.get('priceChange', {})
                
                return {
                    'symbol': best_pair.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                    'name': best_pair.get('baseToken', {}).get('name', ''),
                    'price': float(best_pair.get('priceUsd', 0)),
                    'liquidity': float(liquidity_data.get('usd', 0)),
                    'volume_24h': float(volume_data.get('h24', 0)),
                    'price_change_24h': float(price_change_data.get('h24', 0)) if isinstance(price_change_data, dict) else float(best_pair.get('priceChange', 0)),
                    'pair_url': best_pair.get('url', ''),
                }
    except Exception as e:
        print(f"   ❌ Erro DexScreener: {e}")
    return {'symbol': 'UNKNOWN', 'price': 0, 'liquidity': 0, 'volume_24h': 0, 'price_change_24h': 0}

def is_token_listed_on_exchange(token_symbol, exchange_name):
    """Verifica se o token já está listado na exchange"""
    try:
        query_params = {
            "exchange": f"eq.{exchange_name}",
            "token": f"eq.{token_symbol.upper()}"
        }
        result = supabase_query("exchange_tokens", query_params)
        return len(result) > 0
    except Exception as e:
        print(f"   ❌ Erro ao verificar listing: {e}")
        return False

def calculate_holding_score(holding_data, exchange_name):
    """Calcula score REALISTA para holdings"""
    token_symbol = holding_data['symbol']
    value_usd = holding_data['value_usd']
    liquidity = holding_data['liquidity']
    volume_24h = holding_data['volume_24h']
    
    # Base score BAIXA - somos exigentes!
    score = 30
    
    # Threshold específico por exchange
    threshold = HOLDING_THRESHOLDS.get(exchange_name, 100000)
    
    # 1. VALOR (PESO MÁXIMO)
    if value_usd > threshold * 3:  # 3x acima do threshold
        score += 35
    elif value_usd > threshold * 2:  # 2x acima do threshold
        score += 25
    elif value_usd > threshold:  # Apenas acima do threshold
        score += 15
        
    # 2. LIQUIDEZ (MUITO IMPORTANTE)
    if liquidity > 10000000:  # $10M+
        score += 25
    elif liquidity > 5000000:  # $5M+
        score += 20
    elif liquidity > 2000000:  # $2M+
        score += 15
    elif liquidity < MIN_LIQUIDITY:  # Abaixo do mínimo
        score -= 20
        
    # 3. VOLUME (IMPORTANTE)
    if volume_24h > 2000000:  # $2M+
        score += 15
    elif volume_24h > 1000000:  # $1M+
        score += 10
    elif volume_24h > MIN_VOLUME_24H:  # $500k+
        score += 5
    elif volume_24h < 100000:  # Volume muito baixo
        score -= 10
        
    # 4. SE NÃO ESTÁ LISTADO (BÔNUS MODERADO)
    if not is_token_listed_on_exchange(token_symbol, exchange_name):
        score += 10
        
    return min(max(score, 0), 100)  # Garantir entre 0-100

def is_scam_token(token_data, value_usd):
    """Verifica se é um token scam/lixo"""
    # 1. Liquidez muito baixa
    if token_data["liquidity"] < 100000:  # $100k
        return True
    
    # 2. Nomes suspeitos
    suspicious_keywords = ["http", "www", ".com", ".org", ".fi", ".website", "reward", "claim", "visit", "bounty", "invitation"]
    name_lower = (token_data.get("name", "") or "").lower()
    symbol_lower = (token_data.get("symbol", "") or "").lower()
    
    for keyword in suspicious_keywords:
        if keyword in name_lower or keyword in symbol_lower:
            return True
    
    # 3. Volume zero com valor alto
    if token_data["volume_24h"] == 0 and value_usd > 100000:
        return True
    
    return False

# ===========================
# SOLANA HOLDINGS
# ===========================
async def get_solana_holdings(wallet_address, wallet_name):
    """Busca holdings de uma wallet Solana (usando requests)"""
    try:
        holdings = []
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address, 
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, 
                {"encoding": "jsonParsed", "commitment": "processed"}
            ]
        }
        
        # TROCA aiohttp por requests
        response = requests.post(HELIUS_URL, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'value' in data['result']:
                print(f"   📊 {len(data['result']['value'])} token accounts encontrados")
                
                for token_account in data['result']['value']:
                    try:
                        token_info = token_account['account']['data']['parsed']['info']
                        mint = token_info['mint']
                        balance = float(token_info['tokenAmount']['uiAmount'])
                        
                        # ... resto do código IGUAL ...
                        # Ignorar stablecoins, SOL e balances muito pequenos
                        if balance <= 0.001 or mint in [
                            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                            "So11111111111111111111111111111111111111112"     # SOL
                        ]:
                            continue
                        
                        # Buscar dados do token
                        token_data = get_token_data_dexscreener(mint)
                        price = token_data['price']
                        value_usd = balance * price
                        
                        # APLICAR FILTROS REALISTAS
                        threshold = HOLDING_THRESHOLDS.get(wallet_name, 100000)
                        
                        if (value_usd >= threshold and 
                            token_data['liquidity'] >= MIN_LIQUIDITY and
                            token_data['symbol'] != 'UNKNOWN' and
                            not is_scam_token(token_data, value_usd)):
                            
                            # Calcular score
                            score = calculate_holding_score({
                                'symbol': token_data['symbol'],
                                'value_usd': value_usd,
                                'liquidity': token_data['liquidity'],
                                'volume_24h': token_data['volume_24h']
                            }, wallet_name)
                            
                            holding_info = {
                                "symbol": token_data['symbol'],
                                "name": token_data.get('name', ''),
                                "balance": balance, 
                                "value_usd": value_usd,
                                "address": mint, 
                                "liquidity": token_data['liquidity'],
                                "volume_24h": token_data['volume_24h'],
                                "price": price,
                                "price_change_24h": token_data['price_change_24h'],
                                "pair_url": token_data['pair_url'],
                                "score": score,
                                "chain": "solana"
                            }
                            
                            holdings.append(holding_info)
                            print(f"   ✅ {token_data['symbol']}: ${value_usd:,.0f} (Score: {score})")
                            
                    except Exception as e:
                        continue
        else:
            print(f"   ❌ Erro API Helius: {response.status_code}")
        return holdings
    except Exception as e:
        print(f"   ❌ Erro geral get_solana_holdings: {e}")
        return []

# ===========================
# ETHEREUM HOLDINGS
# ===========================
async def get_ethereum_holdings(wallet_address, wallet_name):
    """Busca holdings de uma wallet Ethereum"""
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
                                    token_data = get_token_data_dexscreener(token_address)
                                    if token_data["price"] > 0:
                                        value_usd = balance * token_data["price"]
                                        
                                        # APLICAR FILTROS REALISTAS
                                        threshold = HOLDING_THRESHOLDS.get(wallet_name, 100000)
                                        
                                        if (value_usd >= threshold and 
                                            token_data['liquidity'] >= MIN_LIQUIDITY and
                                            token_data['symbol'] != 'UNKNOWN' and
                                            not is_scam_token(token_data, value_usd)):
                                            
                                            # Calcular score
                                            score = calculate_holding_score({
                                                'symbol': token_data['symbol'],
                                                'value_usd': value_usd,
                                                'liquidity': token_data['liquidity'],
                                                'volume_24h': token_data['volume_24h']
                                            }, wallet_name)
                                            
                                            holding_info = {
                                                "symbol": token_data['symbol'],
                                                "name": token_data.get('name', ''),
                                                "balance": balance, 
                                                "value_usd": value_usd,
                                                "address": token_address,
                                                "liquidity": token_data['liquidity'],
                                                "volume_24h": token_data['volume_24h'],
                                                "price": token_data['price'],
                                                "price_change_24h": token_data['price_change_24h'],
                                                "pair_url": token_data['pair_url'],
                                                "score": score,
                                                "chain": "ethereum"
                                            }
                                            
                                            holdings.append(holding_info)
                                            processed_tokens.add(token_address)
                                            print(f"   ✅ {token_data['symbol']}: ${value_usd:,.0f} (Score: {score})")
                    
                    except Exception as e:
                        continue
        
        return holdings
        
    except Exception as e:
        print(f"❌ Erro ao obter holdings Ethereum: {e}")
        return []

# ===========================
# FUNÇÕES PRINCIPAIS
# ===========================
def save_holding_to_supabase(holding_data, exchange_name):
    """Guarda o holding na base de dados"""
    try:
        payload = {
            "exchange": exchange_name,
            "token": holding_data['symbol'],
            "token_address": holding_data['address'],
            "amount": holding_data['balance'],
            "value_usd": holding_data['value_usd'],
            "liquidity": holding_data['liquidity'],
            "volume_24h": holding_data['volume_24h'],
            "price": holding_data['price'],
            "price_change_24h": holding_data['price_change_24h'],
            "pair_url": holding_data['pair_url'],
            "score": holding_data['score'],
            "type": "holding",
            "chain": holding_data['chain'],
            "ts": datetime.now().isoformat(),
        }
        
        return supabase_upsert("transacted_tokens", payload, ["token_address", "type", "chain"])
        
    except Exception as e:
        print(f"❌ Erro ao guardar holding: {e}")
        return False

async def analyze_wallet_holdings(wallet_name, wallet_address, chain="solana"):
    """Analisa holdings de uma wallet e guarda os significativos"""
    print(f"🔍 Analisando {chain.upper()} holdings de {wallet_name}...")
    
    if chain == "solana":
        holdings = await safe_api_call(get_solana_holdings, wallet_address, wallet_name)
    else:
        holdings = await safe_api_call(get_ethereum_holdings, wallet_address, wallet_name)
    
    if not holdings:
        print(f"   ℹ️  Nenhum holding significativo encontrado em {wallet_name}")
        return 0
    
    saved_count = 0
    high_score_count = 0
    
    for holding in holdings:
        metrics.holdings_found += 1
        
        # Validar dados antes de guardar
        if not validate_holding_data(holding):
            continue
            
        # Só guardar holdings com score ALTO
        if holding['score'] >= MIN_SCORE_ALERT:
            if save_holding_to_supabase(holding, wallet_name):
                saved_count += 1
                metrics.holdings_saved += 1
                print(f"   💾 Guardado: {holding['symbol']} (Score: {holding['score']})")
        
        if holding['score'] >= 70:
            high_score_count += 1
    
    print(f"   📈 {saved_count}/{len(holdings)} holdings guardados")
    print(f"   🎯 {high_score_count} holdings com score ≥ 70")
    
    return saved_count

async def update_listed_tokens():
    """Atualiza lista de tokens listados nas exchanges"""
    print("🔄 ATUALIZANDO TOKENS LISTADOS...")
    
    # Funções de coleta (simplificadas)
    def fetch_binance_tokens():
        try:
            r = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({s['baseAsset'].upper() for s in data.get('symbols', []) if s.get('status') == 'TRADING'})
        except:
            return []
        return []

    def fetch_coinbase_tokens():
        try:
            r = requests.get("https://api.exchange.coinbase.com/products", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(p.get('base_currency') or "").upper() for p in data if p.get('status') == 'online'})
        except:
            return []
        return []

    exchanges = [
        ("Binance", fetch_binance_tokens),
        ("Coinbase", fetch_coinbase_tokens),
    ]

    total_tokens = 0
    for name, func in exchanges:
        print(f"📊 Buscando {name}...")
        tokens = func()
        print(f"   ✅ {len(tokens)} tokens encontrados")
        
        for token in tokens[:500]:  # Limitar para não sobrecarregar
            data = {"exchange": name, "token": token.upper()}
            supabase_upsert("exchange_tokens", data, ["exchange", "token"])
        
        total_tokens += len(tokens)
        time.sleep(1)
    
    print(f"🎯 {total_tokens} tokens listados atualizados")
    return total_tokens

async def main():
    """Worker principal melhorado com métricas e resiliência"""
    metrics.start()
    
    print("🤖 WORKER DIÁRIO UNIFICADO - INICIADO")
    print("==================================================")
    print(f"🎯 Thresholds: Liquidez ${MIN_LIQUIDITY:,}+ | Volume ${MIN_VOLUME_24H:,}+")
    print(f"🎯 Score mínimo: {MIN_SCORE_ALERT} | Análise REALISTA")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("==================================================")
    
    try:
        # 1. Atualizar tokens listados
        print("\n📊 FASE 1: ATUALIZAR TOKENS LISTADOS")
        listed_tokens = await safe_api_call(update_listed_tokens)
        print(f"✅ {listed_tokens} tokens listados atualizados")
        
        total_saved = 0
        
        # 2. Analisar Solana
        print("\n🔵 FASE 2: ANALISAR SOLANA WALLETS")
        for wallet_name, wallet_address in SOLANA_WALLETS.items():
            try:
                saved = await safe_api_call(
                    analyze_wallet_holdings, 
                    wallet_name, 
                    wallet_address, 
                    "solana"
                )
                total_saved += saved
                metrics.wallets_processed += 1
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"❌ Erro em {wallet_name}: {e}")
                metrics.errors += 1
        
        # 3. Analisar Ethereum
        print("\n🟠 FASE 3: ANALISAR ETHEREUM WALLETS")
        for wallet_name, wallet_address in ETHEREUM_WALLETS.items():
            try:
                saved = await safe_api_call(
                    analyze_wallet_holdings, 
                    wallet_name, 
                    wallet_address, 
                    "ethereum"
                )
                total_saved += saved
                metrics.wallets_processed += 1
                await asyncio.sleep(3)  # Rate limiting
            except Exception as e:
                print(f"❌ Erro em {wallet_name}: {e}")
                metrics.errors += 1
        
        # Relatório final
        print("\n==================================================")
        print("📈 RELATÓRIO FINAL DO WORKER")
        print("==================================================")
        summary = metrics.get_summary()
        for key, value in summary.items():
            print(f"   {key}: {value}")
        print("==================================================")
        
    except Exception as e:
        print(f"💥 ERRO CRÍTICO NO WORKER: {e}")
        metrics.errors += 1

if __name__ == "__main__":
    asyncio.run(main())