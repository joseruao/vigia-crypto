#!/usr/bin/env python3
"""
Teste rápido para verificar se as variáveis estão a ser carregadas
"""

import os
from pathlib import Path

print("\n" + "="*60)
print("🔍 TESTE RÁPIDO - VARIÁVEIS DE AMBIENTE")
print("="*60)

# 1. Verifica se o .env existe
backend_dir = Path(__file__).resolve().parent
env_path = backend_dir / ".env"

if not env_path.exists():
    env_path = backend_dir.parent / ".env"

if not env_path.exists():
    print(f"\n❌ Ficheiro .env não encontrado!")
    print(f"   Procurado em: {backend_dir / '.env'}")
    print(f"   Procurado em: {backend_dir.parent / '.env'}")
    exit(1)

print(f"\n✅ Ficheiro .env encontrado: {env_path}")

# 2. Lê o conteúdo do .env (sem mostrar valores completos)
print("\n📄 Conteúdo do .env:")
print("-" * 60)
with open(env_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        if 'SUPABASE_URL' in line_stripped:
            if '=' in line_stripped:
                parts = line_stripped.split('=', 1)
                value = parts[1].strip().strip('"').strip("'")
                print(f"Linha {i}: ✅ SUPABASE_URL = {value[:30]}... ({len(value)} chars)")
            else:
                print(f"Linha {i}: ❌ SUPABASE_URL (sem '=')")
        
        elif 'SUPABASE_SERVICE_ROLE_KEY' in line_stripped:
            if '=' in line_stripped:
                parts = line_stripped.split('=', 1)
                value = parts[1].strip().strip('"').strip("'")
                print(f"Linha {i}: ✅ SUPABASE_SERVICE_ROLE_KEY = {value[:20]}... ({len(value)} chars)")
                if len(value) < 50:
                    print(f"   ⚠️ PROBLEMA: Valor muito curto!")
            else:
                print(f"Linha {i}: ❌ SUPABASE_SERVICE_ROLE_KEY (sem '=')")
        
        elif 'SUPABASE_KEY' in line_stripped and 'SERVICE_ROLE' not in line_stripped:
            print(f"Linha {i}: ⚠️ SUPABASE_KEY encontrado (deveria ser SUPABASE_SERVICE_ROLE_KEY)")

# 3. Tenta carregar com dotenv
print("\n🧪 TESTE DE CARREGAMENTO:")
print("-" * 60)

try:
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    print(f"SUPABASE_URL: {'✅' if url else '❌'} ({len(url)} chars)")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'✅' if key else '❌'} ({len(key)} chars)")
    
    if url and key:
        print("\n✅ Variáveis carregadas corretamente!")
        print("\n💡 Se a API ainda mostra KEY: ❌, o problema pode ser:")
        print("   1. A API não foi reiniciada após alterar o .env")
        print("   2. A API está a usar um .env diferente")
        print("   3. Há um problema no código que carrega as variáveis")
    elif url and not key:
        print("\n⚠️ PROBLEMA: SUPABASE_URL carregado mas SUPABASE_SERVICE_ROLE_KEY NÃO!")
        print("\n💡 SOLUÇÃO:")
        print("   1. Verifica se a linha no .env tem o nome EXATO: SUPABASE_SERVICE_ROLE_KEY")
        print("   2. Verifica se não há espaços antes/depois do '='")
        print("   3. Verifica se o valor não está vazio")
    else:
        print("\n❌ Nenhuma variável carregada!")
        
except ImportError:
    print("❌ python-dotenv não instalado")
    print("   Instala com: pip install python-dotenv")

# 4. Testa se a API consegue carregar
print("\n🔌 TESTE DE IMPORTAÇÃO DA API:")
print("-" * 60)

try:
    import sys
    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    from utils import supa
    
    print(f"supa.ok(): {supa.ok()}")
    
    # Verifica diretamente
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    print(f"SUPABASE_URL direto: {'✅' if supabase_url else '❌'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY direto: {'✅' if supabase_key else '❌'}")
    
    if supa.ok():
        print("\n✅ Tudo OK! A API deve funcionar.")
    else:
        print("\n❌ supa.ok() retorna False")
        print("   Verifica o código em backend/utils/supa.py")
        
except Exception as e:
    print(f"❌ Erro ao importar: {e}")

print("\n" + "="*60)
