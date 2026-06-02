import requests
import time
import json
import asyncio
from datetime import datetime, timezone
import os
import math
import inspect
from pathlib import Path

try:
    from dotenv import load_dotenv
    for env_path in (
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ):
        if env_path.exists():
            load_dotenv(env_path, override=False)
except ImportError:
    pass

# ===========================
# CONFIGURAÇÃO
# ===========================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)
_helius_raw = (os.getenv("HELIUS_API_KEY") or os.getenv("HELIUS_KEYS") or "").strip()
HELIUS_API_KEY = _helius_raw.split(",")[0].strip() if _helius_raw else ""
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
SNOWSCAN_API_KEY = os.getenv("SNOWSCAN_API_KEY", "") or os.getenv("SNOWTRACE_API_KEY", "")

TELEGRAM_BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN_SOL")
    or os.getenv("TELEGRAM_BOT_TOKEN_1")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or ""
)
TELEGRAM_CHAT_ID = (
    os.getenv("TELEGRAM_CHAT_ID_SOL")
    or os.getenv("TELEGRAM_CHAT_ID_1")
    or os.getenv("TELEGRAM_CHAT_ID")
    or ""
)

EXCHANGE_NORMALIZE = {
    "Binance 1": "Binance", "Binance 2": "Binance", "Binance 3": "Binance",
    "Binance BNB 51": "Binance", "Binance AVAX 74": "Binance",
    "Coinbase 1": "Coinbase", "Coinbase Hot": "Coinbase",
    "Kraken Cold 1": "Kraken", "Kraken Cold 2": "Kraken",
}

def token_candidates(token_symbol):
    base = (token_symbol or "").strip().upper().lstrip("$")
    if not base:
        return set()
    candidates = {base, f"1000{base}", f"10000{base}", f"1000000{base}", f"1M{base}"}
    for prefix in ("1000000", "10000", "1000", "1M"):
        if base.startswith(prefix) and len(base) > len(prefix):
            candidates.add(base[len(prefix):])
    if base == "BABYDOGE":
        candidates.update({"1MBABYDOGE", "1000000BABYDOGE"})
    return candidates

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
    
    # ETHEREUM WALLETS — thresholds mais baixos que Solana porque ETH tem tokens
    # de médio porte que ainda não chegaram às exchanges mas já têm valor real
    "Binance 8": 200000,      # $200k+
    "Binance 14": 200000,     # $200k+
    "Binance 7": 200000,      # $200k+
    "Binance 16": 200000,     # $200k+
    "Kraken": 100000,         # $100k+
    "OKX 73": 75000,          # $75k+
    "OKX 93": 75000,          # $75k+
    "Coinbase 10": 100000,    # $100k+
    "Gate.io": 50000,         # $50k+
    "Bitget Hot Wallet 1": 50000,  # $50k+
    "Bitfinex 2": 75000,      # $75k+
    "Bitfinex 19": 75000,     # $75k+
    "Gemini 3": 50000,        # $50k+
    "Robinhood": 75000,       # $75k+
    "Upbit": 50000,           # $50k+

    # BNB Chain / Avalanche C-Chain exchange wallets
    "Binance BNB 51": 200000,
    "Binance AVAX 74": 50000,
}

MIN_LIQUIDITY = 2000000  # $2M+ liquidez mínima
MIN_VOLUME_24H = 500000  # $500k+ volume mínimo
MIN_SCORE_ALERT = 70     # Score mínimo para alerta

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

BNB_WALLETS = {
    # BscScan tag: Binance 51 / Binance Exchange / Binance hot wallet.
    "Binance BNB 51": "0x8894E0a0c962CB723c1976a4421c95949bE2D4E3",
}

AVALANCHE_WALLETS = {
    # SnowScan tag: Binance 74 on Avalanche C-Chain.
    "Binance AVAX 74": "0xa7C0D36c4698981FAb42a7d8c783674c6Fe2592d",
}


def _load_extra_wallets(env_name):
    """Optional env format: Name=0xabc,Other Name=0xdef"""
    out = {}
    for item in (os.getenv(env_name, "") or "").split(","):
        if "=" not in item:
            continue
        name, address = item.split("=", 1)
        name = name.strip()
        address = address.strip()
        if name and address.startswith("0x"):
            out[name] = address
    return out


BNB_WALLETS.update(_load_extra_wallets("BNB_WALLETS"))
AVALANCHE_WALLETS.update(_load_extra_wallets("AVAX_WALLETS"))

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
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
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
        if response.status_code in [200, 201, 204]:
            return True
        print(f"Erro Supabase insert {table}: HTTP {response.status_code} - {response.text[:300]}")
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
        
        conflict_str = ",".join(conflict_columns)
        url += f"?on_conflict={conflict_str}"
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [200, 201, 204]:
            return True
        print(f"Erro Supabase upsert {table}: HTTP {response.status_code} - {response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ Erro Supabase upsert: {e}")
        return False

# ===========================
# FUNÇÕES DE DADOS
# ===========================
def supabase_upsert_many(table, rows, conflict_columns, timeout=25):
    """Upsert em lote para evitar 100 chamadas seguidas no cron."""
    if not rows:
        return 0
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = SUPABASE_HEADERS.copy()
        headers["Prefer"] = "resolution=merge-duplicates"
        conflict_str = ",".join(conflict_columns)
        url += f"?on_conflict={conflict_str}"

        response = requests.post(url, headers=headers, json=rows, timeout=timeout)
        if response.status_code in [200, 201, 204]:
            return len(rows)
        print(f"⚠️ Erro Supabase bulk upsert {table}: HTTP {response.status_code} - {response.text[:200]}")
        return 0
    except Exception as e:
        print(f"⚠️ Erro Supabase bulk upsert {table}: {e}")
        return 0

def supabase_count_rows(table, query_params=None, timeout=10):
    """Conta linhas visiveis via REST para confirmar que o cron gravou mesmo."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = SUPABASE_HEADERS.copy()
        headers["Prefer"] = "count=exact"
        params = {"select": "*", "limit": "1"}
        if query_params:
            params.update(query_params)
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        if response.status_code != 200:
            print(f"Erro Supabase count {table}: HTTP {response.status_code} - {response.text[:200]}")
            return None
        content_range = response.headers.get("Content-Range", "")
        if "/" in content_range:
            return int(content_range.rsplit("/", 1)[1])
        return len(response.json() or [])
    except Exception as e:
        print(f"Erro Supabase count {table}: {e}")
        return None

def get_token_data_dexscreener(token_address, chain=None):
    """Busca dados do token no DexScreener"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])
            if chain:
                chain_aliases = {
                    "ethereum": {"ethereum", "ether"},
                    "bsc": {"bsc", "bnb", "binance-smart-chain"},
                    "avalanche": {"avalanche", "avax"},
                }
                allowed = chain_aliases.get(chain, {chain})
                filtered_pairs = [
                    p for p in pairs
                    if str(p.get("chainId") or "").lower() in allowed
                ]
                if filtered_pairs:
                    pairs = filtered_pairs
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
        exchange = EXCHANGE_NORMALIZE.get(exchange_name, exchange_name)
        candidates = sorted(token_candidates(token_symbol))
        if not exchange or not candidates:
            return False
        query_params = {
            "exchange": f"eq.{exchange}",
            "token": f"in.({','.join(candidates)})"
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
    
    # Threshold específico por exchange
    threshold = HOLDING_THRESHOLDS.get(exchange_name, 100000)

    # Score continuo: diferencia candidatos sem empatar quase tudo em 70/90.
    score = 22.0
    if value_usd > 0:
        score += min(28.0, math.log10(value_usd + 1) * 3.8)
        score += min(10.0, (value_usd / max(threshold, 1)) * 4.0)
    else:
        score -= 8.0

    if liquidity > 0:
        score += min(24.0, math.log10(liquidity + 1) * 3.2)
    if liquidity < MIN_LIQUIDITY:
        score -= 10.0

    if volume_24h > 0:
        score += min(14.0, math.log10(volume_24h + 1) * 2.1)
    if volume_24h < 100000:
        score -= 6.0

    if not is_token_listed_on_exchange(token_symbol, exchange_name):
        score += 4.0

    return round(min(max(score, 0), 100), 1)

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
def _evm_api_config(chain):
    chain = chain or "ethereum"
    if chain == "bsc":
        if ETHERSCAN_API_KEY:
            return "https://api.etherscan.io/v2/api", ETHERSCAN_API_KEY, "56"
        return "https://api.bscscan.com/api", BSCSCAN_API_KEY, None
    if chain == "avalanche":
        if ETHERSCAN_API_KEY:
            return "https://api.etherscan.io/v2/api", ETHERSCAN_API_KEY, "43114"
        return "https://api.snowscan.xyz/api", SNOWSCAN_API_KEY, None
    return "https://api.etherscan.io/api", ETHERSCAN_API_KEY, None


async def get_ethereum_holdings(wallet_address, wallet_name, chain="ethereum"):
    """Busca holdings de uma wallet EVM (Ethereum, BNB Chain ou Avalanche C-Chain)."""
    try:
        holdings = []
        processed_tokens = set()
        api_url, api_key, chain_id = _evm_api_config(chain)
        if not api_key:
            print(f"   ⚠️ Sem API key para {chain}. Define ETHERSCAN_API_KEY ou key especifica da chain.")
            return []
        
        # Obter tokens ERC-20
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet_address,
            "page": 1,
            "offset": 100,
            "sort": "desc",
            "apikey": api_key
        }
        if chain_id:
            params["chainid"] = chain_id
        
        response = requests.get(api_url, params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1' and data.get('result'):
                for tx in data['result']:
                    try:
                        token_address = tx.get('contractAddress', '')
                        symbol = tx.get('tokenSymbol', '')
                        
                        # Ignorar tokens já processados, ETH e stablecoins
                        if (not token_address or token_address in processed_tokens or
                            symbol.upper() in ["ETH", "BNB", "AVAX", "USDT", "USDC", "DAI", "BUSD", "TUSD"]):
                            continue
                        
                        # Obter balanço atual
                        balance_params = {
                            "module": "account",
                            "action": "tokenbalance",
                            "contractaddress": token_address,
                            "address": wallet_address,
                            "tag": "latest",
                            "apikey": api_key
                        }
                        if chain_id:
                            balance_params["chainid"] = chain_id
                        
                        balance_response = requests.get(api_url, params=balance_params, timeout=15)
                        if balance_response.status_code == 200:
                            balance_data = balance_response.json()
                            if balance_data.get('status') == '1':
                                decimals = int(tx.get('tokenDecimal', 18))
                                balance = int(balance_data['result']) / 10**decimals
                                
                                if balance > 0:
                                    token_data = get_token_data_dexscreener(token_address, chain=chain)
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
                                                "chain": chain
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

def generate_holding_analysis(holding_data, exchange_name):
    """Gera análise automática para o holding"""
    score = holding_data['score']
    value = holding_data['value_usd']
    liquidity = holding_data['liquidity']
    volume = holding_data['volume_24h']
    symbol = holding_data['symbol']
    
    if score >= 90:
        return f"🚀 ALTO POTENCIAL - {symbol} tem ${value:,.0f} na {exchange_name} com liquidez sólida (${liquidity:,.0f}). Volume 24h: ${volume:,.0f}. Forte candidato a listing."
    elif score >= 80:
        return f"✅ BOM POTENCIAL - {symbol} com exposição significativa (${value:,.0f}) na {exchange_name}. Liquidez: ${liquidity:,.0f}. Volume: ${volume:,.0f}."
    elif score >= 70:
        return f"📊 INTERESSANTE - {symbol} detido pela {exchange_name}. Valor: ${value:,.0f}. Liquidez: ${liquidity:,.0f}. Merece monitorização."
    else:
        return f"👀 EM OBSERVAÇÃO - {symbol} presente na {exchange_name}."

def _normalize_exchange_name(raw: str) -> str:
    """Converte 'Binance 2', 'Kraken Cold 1', etc. para o nome limpo da exchange."""
    return EXCHANGE_NORMALIZE.get(raw, raw.split(" ")[0])


def send_telegram_alert(holding: dict, exchange_name: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        symbol   = holding.get("symbol", "?")
        score    = holding.get("score", 0)
        value    = holding.get("value_usd", 0)
        liquidity= holding.get("liquidity", 0)
        volume   = holding.get("volume_24h", 0)
        chain    = holding.get("chain", "").capitalize()
        pair_url = holding.get("pair_url", "")
        exchange = _normalize_exchange_name(exchange_name)

        if score >= 90:
            badge = "🔥 Score muito alto"
            verdict = "Forte candidato a listing"
        elif score >= 80:
            badge = "✅ Score alto"
            verdict = "Bom sinal — merece atenção"
        else:
            badge = "📊 Score moderado"
            verdict = "Em monitorização"

        sep = "─" * 22
        lines = [
            f"🏦 *Novo token detetado*",
            sep,
            f"*{symbol}*  ·  {exchange}  ·  {chain}",
            sep,
            f"*{badge}*   {score:.0f}/100",
            f"",
            f"💰 Valor na wallet    *${value:,.0f}*",
            f"💧 Liquidez no par    *${liquidity:,.0f}*",
        ]
        if volume:
            lines.append(f"📈 Volume 24h         *${volume:,.0f}*")
        lines += [
            f"",
            f"_{verdict}_",
        ]
        if pair_url:
            lines.append(f"[🔗 Ver no DexScreener]({pair_url})")

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": "\n".join(lines),
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        print(f"   📨 Telegram alert enviado: {symbol} ({exchange})")
    except Exception as e:
        print(f"   ⚠️ Telegram alert falhou: {e}")


def save_holding_to_supabase(holding_data, exchange_name):
    """Guarda o holding na base de dados - ✅ COMPATÍVEL COM SCHEMA SUPABASE"""
    try:
        # ✅ FIX: Gerar hash único para signature (campo obrigatório)
        import hashlib
        signature = hashlib.md5(
            f"{holding_data['address']}{exchange_name}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()
        
        analysis = generate_holding_analysis(holding_data, exchange_name)
        
        # ✅ FIX: Campos OBRIGATÓRIOS (NOT NULL) na tabela
        payload = {
            # Campos obrigatórios
            "token_address": holding_data['address'],  # NOT NULL - chave de uniqueness
            "type": "holding",                         # NOT NULL - chave de uniqueness
            "chain": holding_data['chain'],            # NOT NULL - chave de uniqueness
            "signature": signature,                    # Agora preenchido
            
            # Campos opcionais (nullable)
            "token": holding_data['symbol'],
            "exchange": exchange_name,
            "amount": holding_data['balance'],
            "value_usd": holding_data['value_usd'],
            "price": holding_data['price'],
            "liquidity": holding_data['liquidity'],
            "pair_url": holding_data['pair_url'],
            "volume_24h": holding_data['volume_24h'],
            "score": holding_data['score'],
            "analysis_text": analysis,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        
        # Guardar um snapshot por token/exchange. Se a migration ainda nao tiver
        # sido aplicada no Supabase, mantemos fallback para nao partir o cron.
        success = supabase_upsert("transacted_tokens", payload, ["token_address", "type", "chain", "exchange"])
        if not success:
            print("   ⚠️ Upsert com exchange falhou; fallback para unique antiga token/type/chain")
            success = supabase_upsert("transacted_tokens", payload, ["token_address", "type", "chain"])
        if success:
            print(f"   💾 GUARDADO: {holding_data['symbol']} (Score: {holding_data['score']})")
        return success
        
    except Exception as e:
        print(f"❌ Erro ao guardar holding: {e}")
        return False

async def analyze_wallet_holdings(wallet_name, wallet_address, chain="solana"):
    """Analisa holdings de uma wallet e guarda os significativos"""
    print(f"🔍 Analisando {chain.upper()} holdings de {wallet_name}...")
    
    if chain == "solana":
        holdings = await safe_api_call(get_solana_holdings, wallet_address, wallet_name)
    else:
        holdings = await safe_api_call(get_ethereum_holdings, wallet_address, wallet_name, chain)
    
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
                if holding['score'] >= 80:
                    send_telegram_alert(holding, wallet_name)
        
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

    def fetch_kucoin_tokens():
        try:
            r = requests.get("https://api.kucoin.com/api/v1/symbols", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(s.get('baseCurrency') or "").upper() for s in data.get('data', []) if s.get('enableTrading')})
        except:
            return []
        return []

    def fetch_okx_tokens():
        try:
            r = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SPOT", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(s.get('baseCcy') or "").upper() for s in data.get('data', []) if s.get('state') == 'live'})
        except:
            return []
        return []

    def fetch_mexc_tokens():
        try:
            r = requests.get("https://www.mexc.com/open/api/v2/market/symbols", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(i.get('base_currency') or "").upper() for i in data.get('data', []) if i.get('base_currency')})
        except:
            return []
        return []

    def fetch_gateio_tokens():
        try:
            r = requests.get("https://api.gateio.ws/api/v4/spot/currency_pairs", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(i.get('base') or "").upper() for i in data if i.get('trade_status') == 'tradable'})
        except:
            return []
        return []

    def fetch_bitget_tokens():
        try:
            r = requests.get("https://api.bitget.com/api/v2/spot/public/symbols", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return list({(i.get('baseCoin') or "").upper() for i in data.get('data', []) if i.get('status') == 'online'})
        except:
            return []
        return []

    def fetch_bybit_tokens():
        try:
            r = requests.get("https://api.bybit.com/v5/market/instruments-info?category=spot", timeout=15)
            if r.status_code == 200:
                data = r.json()
                items = data.get('result', {}).get('list', [])
                return list({(i.get('baseCoin') or "").upper() for i in items if i.get('status') == 'Trading'})
        except:
            return []
        return []

    exchanges = [
        ("Binance", fetch_binance_tokens),
        ("Coinbase", fetch_coinbase_tokens),
        ("KuCoin", fetch_kucoin_tokens),
        ("OKX", fetch_okx_tokens),
        ("MEXC", fetch_mexc_tokens),
        ("Gate.io", fetch_gateio_tokens),
        ("Bitget", fetch_bitget_tokens),
        ("Bybit", fetch_bybit_tokens),
    ]

    total_tokens = 0
    for name, func in exchanges:
        print(f"📊 Buscando {name}...")
        tokens = func()
        print(f"   ✅ {len(tokens)} tokens encontrados")
        
        for token in tokens:
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
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
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

        # 4. Analisar BNB Chain
        print("\n🟡 FASE 4: ANALISAR BNB CHAIN WALLETS")
        for wallet_name, wallet_address in BNB_WALLETS.items():
            try:
                saved = await safe_api_call(
                    analyze_wallet_holdings,
                    wallet_name,
                    wallet_address,
                    "bsc"
                )
                total_saved += saved
                metrics.wallets_processed += 1
                await asyncio.sleep(3)
            except Exception as e:
                print(f"❌ Erro em {wallet_name}: {e}")
                metrics.errors += 1

        # 5. Analisar Avalanche C-Chain
        print("\n🔴 FASE 5: ANALISAR AVALANCHE C-CHAIN WALLETS")
        for wallet_name, wallet_address in AVALANCHE_WALLETS.items():
            try:
                saved = await safe_api_call(
                    analyze_wallet_holdings,
                    wallet_name,
                    wallet_address,
                    "avalanche"
                )
                total_saved += saved
                metrics.wallets_processed += 1
                await asyncio.sleep(3)
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
