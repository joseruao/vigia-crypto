#!/usr/bin/env python3
"""
Verifica se há espaços antes do = no backend/.env
"""

from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"

if not env_path.exists():
    print("❌ backend/.env não existe")
    exit(1)

print(f"\n🔍 Verificando: {env_path}")
print("="*60)

with open(env_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'SUPABASE_SERVICE_ROLE_KEY' in line:
        print(f"\nLinha {i}:")
        print(f"   Original: {repr(line.rstrip())}")
        
        # Verifica espaços
        if ' =' in line or '= ' in line:
            print(f"   ⚠️ PROBLEMA: Espaços encontrados!")
            print(f"   Correto seria: SUPABASE_SERVICE_ROLE_KEY=valor")
        else:
            print(f"   ✅ Sem espaços - OK!")
        
        # Verifica se tem valor
        if '=' in line:
            parts = line.split('=', 1)
            value = parts[1].strip().strip('"').strip("'")
            if value:
                print(f"   Valor: {value[:30]}... ({len(value)} chars)")
            else:
                print(f"   ⚠️ PROBLEMA: Valor vazio!")

print("\n" + "="*60)
