import os
from dotenv import load_dotenv
from supabase import create_client

# Carregar variáveis do .env
dotenv_path_backend = os.path.join(os.path.dirname(__file__), ".env")
dotenv_path_root = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(dotenv_path_backend):
    load_dotenv(dotenv_path_backend)
elif os.path.exists(dotenv_path_root):
    load_dotenv(dotenv_path_root)
else:
    print("⚠️ Nenhum ficheiro .env encontrado")

# Obter variáveis do .env
url = os.getenv("SUPABASE_URL")
service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not service_role:
    raise ValueError("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY em falta no .env")

# Criar cliente Supabase
supabase = create_client(url, service_role)

print("=== Teste de ligação ao Supabase ===")

try:
    # Exemplo: ler até 5 linhas da tabela exchange_tokens
    response = supabase.table("exchange_tokens").select("*").limit(5).execute()

    if hasattr(response, "data") and response.data:
        print("✅ Ligação bem sucedida. Dados recebidos:")
        for row in response.data:
            print(row)
    else:
        print("⚠️ Ligação ok, mas não vieram dados (tabela vazia ou não existe).")

except Exception as e:
    print("❌ Erro ao ligar ao Supabase:", e)
