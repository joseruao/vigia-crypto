#!/usr/bin/env python3
"""
Teste final para verificar se tudo está a funcionar
"""

import os
import sys
from pathlib import Path

# Adiciona backend ao path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

print("\n" + "="*60)
print("🔍 TESTE FINAL - SUPABASE CONFIG")
print("="*60)

# 1. Carrega .env
print("\n1️⃣ Carregando .env...")
try:
    from dotenv import load_dotenv
    env_paths = [
        backend_dir / ".env",
        backend_dir.parent / ".env",
    ]
    loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            print(f"   ✅ Carregado de: {env_path}")
            loaded = True
            break
    if not loaded:
        print("   ❌ Nenhum .env encontrado!")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. Verifica variáveis
print("\n2️⃣ Verificando variáveis...")
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

print(f"   SUPABASE_URL: {'✅' if url else '❌'} ({len(url)} chars)")
print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if key else '❌'} ({len(key)} chars)")

# 3. Testa supa.ok()
print("\n3️⃣ Testando utils.supa.ok()...")
try:
    from utils import supa
    
    # Força recarregamento
    supa._load_env()
    
    is_ok = supa.ok()
    print(f"   supa.ok(): {is_ok}")
    
    if is_ok:
        print("\n✅ TUDO OK! A API deve funcionar agora.")
    else:
        print("\n❌ supa.ok() retorna False")
        print("\n💡 SOLUÇÃO:")
        print("   1. Verifica se o .env tem SUPABASE_SERVICE_ROLE_KEY=... (sem espaços)")
        print("   2. REINICIA a API após alterar o .env")
        print("   3. Verifica os logs da API quando inicia")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
