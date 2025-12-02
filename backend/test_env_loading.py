#!/usr/bin/env python3
"""
Teste para verificar se as variáveis de ambiente estão a ser carregadas
"""

import os
from pathlib import Path

print("\n" + "="*60)
print("🔍 TESTE DE CARREGAMENTO DE VARIÁVEIS DE AMBIENTE")
print("="*60)

# Tenta carregar .env
try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent
    env_paths = [
        backend_dir / ".env",
        backend_dir.parent / ".env",
    ]
    
    loaded = False
    for env_path in env_paths:
        if env_path.exists():
            print(f"📁 Encontrado .env em: {env_path}")
            load_dotenv(env_path, override=False)
            loaded = True
            break
    
    if not loaded:
        print("⚠️ Nenhum ficheiro .env encontrado")
except ImportError:
    print("⚠️ python-dotenv não instalado")
    print("💡 Instala com: pip install python-dotenv")

# Verifica variáveis
print("\n📋 Variáveis de Ambiente:")
print(f"   SUPABASE_URL: {'✅ Definido' if os.getenv('SUPABASE_URL') else '❌ NÃO DEFINIDO'}")
if os.getenv('SUPABASE_URL'):
    url = os.getenv('SUPABASE_URL')
    print(f"      Valor: {url[:30]}...{url[-10:] if len(url) > 40 else ''}")

print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Definido' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else '❌ NÃO DEFINIDO'}")
if os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    print(f"      Valor: {key[:20]}...{key[-10:] if len(key) > 30 else ''}")

# Testa função supa.ok()
print("\n🧪 Testando utils.supa.ok():")
try:
    from utils import supa
    is_ok = supa.ok()
    print(f"   supa.ok() = {is_ok}")
    if is_ok:
        print("   ✅ Supabase configurado corretamente!")
    else:
        print("   ❌ Supabase NÃO configurado")
        print("   💡 Verifica se o .env tem SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY")
except Exception as e:
    print(f"   ❌ Erro ao importar utils.supa: {e}")

print("\n" + "="*60)
