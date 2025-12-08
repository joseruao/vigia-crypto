#!/usr/bin/env python3
"""
Teste direto da API para verificar se consegue carregar variáveis
"""

import requests
import json

API_BASE = "http://localhost:8000"

print("\n" + "="*60)
print("🔍 TESTE DIRETO DA API")
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
        
        if not data.get('has_key') or not data.get('supa_ok'):
            print("\n   ⚠️ PROBLEMA DETETADO!")
            print(f"      has_key: {data.get('has_key')}")
            print(f"      supa_ok: {data.get('supa_ok')}")
            print(f"      URL length: {data.get('supabase_url_length')}")
            print(f"      KEY length: {data.get('supabase_key_length')}")
    else:
        print(f"   ❌ Erro: {r.status_code} - {r.text[:200]}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ ERRO: API não está a correr em {API_BASE}")
    print("   💡 Inicia a API com: cd backend && .\\start_api.ps1")
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
