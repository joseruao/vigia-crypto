#!/usr/bin/env python3
"""
Script para testar inserção de dados no Supabase.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

# Adiciona backend ao path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Carregar .env
dotenv_path = BACKEND_DIR / ".env"
if not dotenv_path.exists():
    dotenv_path = BACKEND_DIR.parent / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✅ Carregado .env de: {dotenv_path}")
else:
    print("⚠️ Nenhum ficheiro .env encontrado")
    sys.exit(1)

from supabase import create_client

print("\n" + "="*60)
print("🧪 TESTE DE INSERÇÃO NO SUPABASE")
print("="*60)

# Verificar variáveis
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not url or not key:
    print("❌ Variáveis de ambiente não configuradas!")
    sys.exit(1)

print(f"\n✅ SUPABASE_URL: {url[:30]}...")
print(f"✅ SUPABASE_SERVICE_ROLE_KEY: {key[:20]}...")

# Criar cliente
try:
    supabase = create_client(url, key)
    print("\n✅ Cliente Supabase criado")
except Exception as e:
    print(f"❌ Erro ao criar cliente: {e}")
    sys.exit(1)

# Dados de teste
test_data = {
    "type": "holding",
    "exchange": "Binance",
    "token": "TEST",
    "token_address": "TestAddress123456789",
    "chain": "solana",
    "score": 75.5,
    "value_usd": 50000.0,
    "liquidity": 1000000.0,
    "volume_24h": 500000.0,
    "ts": datetime.now(timezone.utc).isoformat(),
    "pair_url": "https://dexscreener.com/solana/test",
    "analysis_text": "Teste de inserção via script Python",
    "ai_analysis": "Este é um registo de teste inserido via script test_insert_data.py"
}

print("\n📝 Dados a inserir:")
for key, value in test_data.items():
    print(f"   {key}: {value}")

# Tentar inserir
print("\n🔄 Tentando inserir...")
try:
    response = supabase.table("transacted_tokens").insert(test_data).execute()
    
    if hasattr(response, 'data') and response.data:
        print("✅ INSERÇÃO BEM SUCEDIDA!")
        print(f"\n📊 Dados inseridos:")
        inserted = response.data[0]
        for key in ["id", "token", "exchange", "score", "ts"]:
            if key in inserted:
                print(f"   {key}: {inserted[key]}")
        
        # Verificar se foi inserido
        print("\n🔍 Verificando se o registo existe...")
        check = supabase.table("transacted_tokens").select("*").eq("token", "TEST").execute()
        if check.data:
            print(f"✅ Confirmado! Encontrados {len(check.data)} registos com token='TEST'")
        else:
            print("⚠️ Não encontrado após inserção (pode ser normal se houver delay)")
            
    else:
        print("❌ Resposta sem dados")
        print(f"   Response: {response}")
        
except Exception as e:
    print(f"❌ ERRO ao inserir: {e}")
    import traceback
    traceback.print_exc()

# Verificar total de holdings agora
print("\n📊 Verificando total de holdings na tabela...")
try:
    result = supabase.table("transacted_tokens").select("id", count="exact").eq("type", "holding").execute()
    count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
    print(f"   Total de holdings: {count}")
except Exception as e:
    print(f"   Erro ao contar: {e}")

print("\n" + "="*60)
print("✅ TESTE CONCLUÍDO")
print("="*60)
