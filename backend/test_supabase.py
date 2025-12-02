#!/usr/bin/env python3
"""
Script de teste para verificar conexão com Supabase e dados das tabelas.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

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

from utils import supa

print("\n" + "="*60)
print("🔍 TESTE DE CONEXÃO SUPABASE")
print("="*60)

# 1. Verificar variáveis de ambiente
print("\n1️⃣ Verificando variáveis de ambiente...")
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if url:
    print(f"   ✅ SUPABASE_URL: {url[:30]}...")
else:
    print("   ❌ SUPABASE_URL: NÃO DEFINIDO")

if key:
    print(f"   ✅ SUPABASE_SERVICE_ROLE_KEY: {key[:20]}...")
else:
    print("   ❌ SUPABASE_SERVICE_ROLE_KEY: NÃO DEFINIDO")

if not supa.ok():
    print("\n❌ ERRO: Variáveis de ambiente não configuradas corretamente!")
    sys.exit(1)

# 2. Teste de conexão básica
print("\n2️⃣ Testando conexão básica...")
try:
    start_time = time.time()
    # Teste simples - buscar uma linha qualquer
    params = {"limit": "1"}
    r = supa.rest_get("transacted_tokens", params=params, timeout=10)
    elapsed = time.time() - start_time
    
    print(f"   ⏱️  Tempo de resposta: {elapsed:.2f}s")
    print(f"   📊 Status HTTP: {r.status_code}")
    
    if r.status_code == 200:
        print("   ✅ Conexão bem sucedida!")
    elif r.status_code == 401:
        print("   ❌ ERRO 401: Chave de autenticação inválida!")
    elif r.status_code == 404:
        print("   ⚠️  ERRO 404: Tabela não encontrada ou URL incorreta")
    else:
        print(f"   ⚠️  ERRO {r.status_code}: {r.text[:200]}")
        
except Exception as e:
    print(f"   ❌ ERRO na conexão: {e}")
    sys.exit(1)

# 3. Teste de contagem de registos
print("\n3️⃣ Testando contagem de registos...")
try:
    start_time = time.time()
    
    # Contar todos os holdings
    params = {"type": "eq.holding", "select": "id"}
    r = supa.rest_get("transacted_tokens", params=params, timeout=10)
    elapsed = time.time() - start_time
    
    if r.status_code == 200:
        data = r.json() or []
        count = len(data)
        print(f"   ✅ Total de holdings: {count}")
        print(f"   ⏱️  Tempo: {elapsed:.2f}s")
    else:
        print(f"   ⚠️  Status {r.status_code}: {r.text[:200]}")
        
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 4. Teste de predictions (score >= 50)
print("\n4️⃣ Testando predictions (score >= 50)...")
try:
    start_time = time.time()
    
    params = {
        "type": "eq.holding",
        "select": "id,exchange,token,chain,score,ts,value_usd,liquidity"
    }
    r = supa.rest_get("transacted_tokens", params=params, timeout=10)
    elapsed = time.time() - start_time
    
    if r.status_code == 200:
        data = r.json() or []
        filtered = [x for x in data if float(x.get("score") or 0) >= 50]
        print(f"   ✅ Total de registos: {len(data)}")
        print(f"   ✅ Predictions (score >= 50): {len(filtered)}")
        print(f"   ⏱️  Tempo: {elapsed:.2f}s")
        
        if filtered:
            print("\n   📋 Primeiros 3 predictions:")
            for i, item in enumerate(filtered[:3], 1):
                print(f"      {i}. {item.get('token', 'N/A')} - {item.get('exchange', 'N/A')} - Score: {item.get('score', 0)}")
        else:
            print("   ⚠️  Nenhuma prediction encontrada (score >= 50)")
    else:
        print(f"   ⚠️  Status {r.status_code}: {r.text[:200]}")
        
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 5. Teste de estrutura da resposta
print("\n5️⃣ Testando estrutura da resposta...")
try:
    params = {
        "type": "eq.holding",
        "select": "id,exchange,token,chain,score,ts,analysis_text,ai_analysis,pair_url,value_usd,liquidity,volume_24h,token_address",
        "limit": "1"
    }
    r = supa.rest_get("transacted_tokens", params=params, timeout=10)
    
    if r.status_code == 200:
        data = r.json() or []
        if data:
            print("   ✅ Estrutura do primeiro registo:")
            first = data[0]
            for key in ["id", "exchange", "token", "chain", "score", "ts", "value_usd", "liquidity"]:
                value = first.get(key, "N/A")
                print(f"      - {key}: {value}")
        else:
            print("   ⚠️  Tabela vazia ou sem holdings")
    else:
        print(f"   ⚠️  Status {r.status_code}")
        
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 6. Teste de timeout
print("\n6️⃣ Testando timeout (5 segundos)...")
try:
    start_time = time.time()
    r = supa.rest_get("transacted_tokens", params={"limit": "1000"}, timeout=5)
    elapsed = time.time() - start_time
    print(f"   ⏱️  Tempo: {elapsed:.2f}s")
    if elapsed > 5:
        print("   ⚠️  AVISO: Query demorou mais de 5 segundos!")
    else:
        print("   ✅ Query dentro do timeout")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

print("\n" + "="*60)
print("✅ TESTE CONCLUÍDO")
print("="*60)

