#!/usr/bin/env python3
"""
Script simples para verificar o .env
"""

import os
from pathlib import Path

print("\n" + "="*60)
print("🔍 VERIFICAÇÃO DO .env")
print("="*60)

# Procura .env
backend_dir = Path(__file__).resolve().parent
env_path = backend_dir / ".env"

if not env_path.exists():
    env_path = backend_dir.parent / ".env"

if not env_path.exists():
    print(f"\n❌ Ficheiro .env não encontrado!")
    print(f"   Procurado em: {backend_dir / '.env'}")
    print(f"   Procurado em: {backend_dir.parent / '.env'}")
    exit(1)

print(f"\n✅ Ficheiro encontrado: {env_path}")

# Lê o ficheiro
with open(env_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"\n📄 Total de linhas: {len(lines)}")

# Procura as variáveis
supabase_url_line = None
supabase_key_line = None
supabase_key_variants = []

for i, line in enumerate(lines, 1):
    line_clean = line.strip()
    if not line_clean or line_clean.startswith('#'):
        continue
    
    if 'SUPABASE_URL' in line_clean:
        supabase_url_line = (i, line_clean)
    
    if 'SUPABASE_SERVICE_ROLE_KEY' in line_clean:
        supabase_key_line = (i, line_clean)
    
    # Verifica variantes incorretas
    if 'SUPABASE_KEY' in line_clean and 'SERVICE_ROLE' not in line_clean:
        supabase_key_variants.append((i, line_clean))
    if 'SUPABASE_API_KEY' in line_clean:
        supabase_key_variants.append((i, line_clean))

print("\n📋 VARIÁVEIS ENCONTRADAS:")
print("-" * 60)

if supabase_url_line:
    num, line = supabase_url_line
    print(f"✅ Linha {num}: SUPABASE_URL")
    if '=' in line:
        parts = line.split('=', 1)
        value = parts[1].strip().strip('"').strip("'")
        if value:
            print(f"   Valor: {value[:30]}... ({len(value)} chars)")
        else:
            print(f"   ⚠️ PROBLEMA: Valor vazio!")
    else:
        print(f"   ⚠️ PROBLEMA: Falta '='")
else:
    print("❌ SUPABASE_URL não encontrado")

if supabase_key_line:
    num, line = supabase_key_line
    print(f"\n✅ Linha {num}: SUPABASE_SERVICE_ROLE_KEY")
    if '=' in line:
        parts = line.split('=', 1)
        value = parts[1].strip().strip('"').strip("'")
        if value:
            print(f"   Valor: {value[:20]}... ({len(value)} chars)")
            if len(value) < 50:
                print(f"   ⚠️ PROBLEMA: Valor muito curto (deve ter ~200 chars)")
        else:
            print(f"   ⚠️ PROBLEMA: Valor vazio!")
        
        # Verifica espaços
        if ' =' in line or '= ' in line:
            print(f"   ⚠️ PROBLEMA: Espaços em volta do '='")
            print(f"   Linha atual: {line[:80]}")
            print(f"   Deve ser: SUPABASE_SERVICE_ROLE_KEY=valor")
    else:
        print(f"   ⚠️ PROBLEMA: Falta '='")
else:
    print("\n❌ SUPABASE_SERVICE_ROLE_KEY não encontrado")
    
    if supabase_key_variants:
        print("\n⚠️ VARIANTES INCORRETAS ENCONTRADAS:")
        for num, line in supabase_key_variants:
            print(f"   Linha {num}: {line[:80]}")
        print("\n💡 SOLUÇÃO:")
        print("   O nome correto é: SUPABASE_SERVICE_ROLE_KEY")
        print("   NÃO: SUPABASE_KEY ou SUPABASE_API_KEY")

# Testa carregamento
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
    elif url and not key:
        print("\n⚠️ PROBLEMA: SUPABASE_URL carregado mas SUPABASE_SERVICE_ROLE_KEY NÃO!")
        print("   Verifica o nome da variável no .env")
    elif not url and key:
        print("\n⚠️ PROBLEMA: SUPABASE_SERVICE_ROLE_KEY carregado mas SUPABASE_URL NÃO!")
    else:
        print("\n❌ Nenhuma variável carregada!")
        
except ImportError:
    print("❌ python-dotenv não instalado")
    print("   Instala com: pip install python-dotenv")

print("\n" + "="*60)
