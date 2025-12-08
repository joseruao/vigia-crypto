#!/usr/bin/env python3
"""
Teste completo para diagnosticar o problema
"""

import os
import sys
from pathlib import Path

# Adiciona backend ao path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

print("\n" + "="*60)
print("🔍 TESTE COMPLETO - DIAGNÓSTICO")
print("="*60)

# 1. Verifica ficheiros .env
print("\n1️⃣ Verificando ficheiros .env...")
env_backend = backend_dir / ".env"
env_root = backend_dir.parent / ".env"

if env_backend.exists():
    print(f"   ✅ backend/.env existe")
    with open(env_backend, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if 'SUPABASE_SERVICE_ROLE_KEY' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip().strip('"').strip("'")
                    print(f"      Linha {i}: {len(value)} chars")
                    if ' =' in line or '= ' in line:
                        print(f"      ⚠️ Espaços encontrados!")
else:
    print(f"   ❌ backend/.env NÃO existe")

if env_root.exists():
    print(f"   ✅ .env (raiz) existe")

# 2. Carrega .env
print("\n2️⃣ Carregando .env...")
try:
    from dotenv import load_dotenv
    
    loaded = False
    for env_path in [env_backend, env_root]:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"   ✅ Carregado: {env_path}")
            loaded = True
            break
    
    if not loaded:
        print("   ❌ Nenhum .env encontrado!")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 3. Verifica variáveis após carregar
print("\n3️⃣ Verificando variáveis após carregar...")
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

print(f"   SUPABASE_URL: {'✅' if url else '❌'} ({len(url)} chars)")
print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if key else '❌'} ({len(key)} chars)")

# 4. Testa importação do módulo supa
print("\n4️⃣ Testando importação de utils.supa...")
try:
    # Limpa cache do módulo para forçar recarregamento
    if 'utils.supa' in sys.modules:
        del sys.modules['utils.supa']
    if 'utils' in sys.modules:
        del sys.modules['utils']
    
    from utils import supa
    
    print(f"   ✅ Módulo importado")
    
    # Testa _get_url e _get_key diretamente
    if hasattr(supa, '_get_url'):
        url_from_supa = supa._get_url()
        print(f"   supa._get_url(): {'✅' if url_from_supa else '❌'} ({len(url_from_supa)} chars)")
    
    if hasattr(supa, '_get_key'):
        key_from_supa = supa._get_key()
        print(f"   supa._get_key(): {'✅' if key_from_supa else '❌'} ({len(key_from_supa)} chars)")
    
    # Testa ok()
    is_ok = supa.ok()
    print(f"   supa.ok(): {is_ok}")
    
    if is_ok:
        print("\n✅ TUDO OK! O problema pode ser na API não estar a usar o código atualizado.")
    else:
        print("\n❌ supa.ok() retorna False")
        print("\n💡 Verifica:")
        print("   1. Se o .env tem SUPABASE_SERVICE_ROLE_KEY=... (sem espaços)")
        print("   2. Se o valor não está vazio")
        print("   3. Se reiniciou a API após alterar o código")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")
    import traceback
    traceback.print_exc()

# 5. Testa se consegue fazer request ao Supabase
print("\n5️⃣ Testando conexão ao Supabase...")
try:
    from utils import supa
    
    if supa.ok():
        print("   Fazendo request de teste...")
        r = supa.rest_get("transacted_tokens", params={"limit": "1"}, timeout=5)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print("   ✅ Conexão ao Supabase OK!")
        elif r.status_code == 401:
            print("   ❌ ERRO 401: Chave inválida!")
        else:
            print(f"   ⚠️ Status {r.status_code}: {r.text[:100]}")
    else:
        print("   ❌ supa.ok() retorna False - não pode testar conexão")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "="*60)
print("✅ TESTE CONCLUÍDO")
print("="*60)
