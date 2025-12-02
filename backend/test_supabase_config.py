#!/usr/bin/env python3
"""
Teste direto para verificar configuração do Supabase na API
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

print("\n" + "="*60)
print("🔍 TESTE DE CONFIGURAÇÃO SUPABASE NA API")
print("="*60)

# Teste 1: Health check
print("\n1️⃣ Testando /alerts/health...")
try:
    r = requests.get(f"{API_BASE}/alerts/health", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Status: {r.status_code}")
        print(f"   📊 Resposta:")
        print(f"      - supabase_url: {data.get('supabase_url')}")
        print(f"      - has_key: {data.get('has_key')}")
        print(f"      - supa_ok: {data.get('supa_ok')}")
        print(f"      - supabase_url_length: {data.get('supabase_url_length')}")
        print(f"      - supabase_key_length: {data.get('supabase_key_length')}")
        
        if not data.get('supabase_url') or not data.get('has_key'):
            print("\n   ⚠️ PROBLEMA DETETADO:")
            if not data.get('supabase_url'):
                print("      ❌ SUPABASE_URL não está definido")
            if not data.get('has_key'):
                print("      ❌ SUPABASE_SERVICE_ROLE_KEY não está definido")
            print("\n   💡 SOLUÇÃO:")
            print("      1. Verifica se existe ficheiro .env em backend/.env")
            print("      2. Verifica se tem SUPABASE_URL=... e SUPABASE_SERVICE_ROLE_KEY=...")
            print("      3. REINICIA a API (Ctrl+C e depois uvicorn main:app --reload)")
        else:
            print("\n   ✅ Variáveis de ambiente carregadas corretamente!")
    else:
        print(f"   ❌ Erro: {r.status_code} - {r.text[:200]}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ ERRO: API não está a correr em {API_BASE}")
    print("   💡 Inicia a API com: cd backend/Api && uvicorn main:app --reload --port 8000")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# Teste 2: Ask endpoint
print("\n2️⃣ Testando /alerts/ask...")
try:
    payload = {"prompt": "Que tokens achas que vão ser listados?"}
    r = requests.post(f"{API_BASE}/alerts/ask", json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Status: {r.status_code}")
        print(f"   📊 Resposta:")
        print(f"      - ok: {data.get('ok')}")
        print(f"      - error: {data.get('error', 'N/A')}")
        print(f"      - answer: {data.get('answer', 'N/A')[:200]}...")
        print(f"      - count: {data.get('count', 0)}")
        
        if not data.get('ok'):
            print("\n   ⚠️ Endpoint retornou erro!")
            print(f"      Erro: {data.get('error', 'N/A')}")
    else:
        print(f"   ❌ Erro: {r.status_code} - {r.text[:200]}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ ERRO: API não está a correr")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "="*60)
print("✅ TESTE CONCLUÍDO")
print("="*60)
