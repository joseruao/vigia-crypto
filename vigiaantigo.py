# vigia_solana_teste_supabase.py
import time
from datetime import datetime
from supabase import create_client, Client

# ============================
# CONFIGURAÇÃO SUPABASE
# ============================
SUPABASE_URL = "https://qynnajpvxnqcmkzrhpde.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================
# WALLETS DE TESTE
# ============================
EXCHANGE_WALLETS_SOL = {
    "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE"
}

# ============================
# FUNÇÕES
# ============================

def load_listed_tokens_supabase():
    """Carrega tokens listados no Supabase"""
    try:
        response = supabase.table("exchange_tokens").select("*").execute()
        if response.data:
            tokens = {}
            for row in response.data:
                ex = row["exchange"]
                token = row["token_symbol"]
                tokens.setdefault(ex, []).append(token)
            return tokens
        return {}
    except Exception as e:
        print("❌ Erro ao carregar tokens listados:", e)
        return {}

def save_transacted_token_supabase(token_data):
    """Salva transação no Supabase"""
    try:
        response = supabase.table("transacted_tokens").insert(token_data).execute()
        return True
    except Exception as e:
        print("❌ Erro ao salvar transação:", e)
        return False

# ============================
# FUNÇÃO DE TESTE
# ============================
def main():
    print("🤖 VIGIA SOLANA - TESTE SUPABASE")
    listed_tokens = load_listed_tokens_supabase()
    print("✅ Tokens carregados:", listed_tokens)

    # Simulando transações de teste
    for exchange_name, wallet in EXCHANGE_WALLETS_SOL.items():
        print(f"🔍 Analisando {exchange_name} ({wallet})...")
        # Exemplo de transação falsa
        test_tx = {
            "exchange": exchange_name,
            "token": "TEST",
            "token_address": "ABC123",
            "amount": 100,
            "value_usd": 5000,
            "price": 50,
            "liquidity": 10000,
            "pair_url": "",
            "signature": "TESTSIG123",
            "timestamp": int(time.time()),
            "listed_exchanges": [],
            "special": False
        }
        success = save_transacted_token_supabase(test_tx)
        print(f"   💾 {test_tx['token']} salvo:", success)

if __name__ == "__main__":
    main()
