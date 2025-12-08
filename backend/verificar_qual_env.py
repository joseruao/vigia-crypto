#!/usr/bin/env python3
"""
Verifica qual ficheiro .env está a ser usado
"""

from pathlib import Path

print("\n" + "="*60)
print("🔍 VERIFICAR QUAL .env ESTÁ A SER USADO")
print("="*60)

backend_dir = Path(__file__).resolve().parent
root_dir = backend_dir.parent

env_backend = backend_dir / ".env"
env_root = root_dir / ".env"

print(f"\n📁 Caminhos:")
print(f"   backend/.env: {env_backend}")
print(f"   .env (raiz):  {env_root}")

print(f"\n📄 Ficheiros encontrados:")
if env_backend.exists():
    print(f"   ✅ backend/.env existe")
    with open(env_backend, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if 'SUPABASE_SERVICE_ROLE_KEY' in line:
                print(f"      Linha {i}: {line.strip()[:80]}")
else:
    print(f"   ❌ backend/.env NÃO existe")

if env_root.exists():
    print(f"   ✅ .env (raiz) existe")
    with open(env_root, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if 'SUPABASE_SERVICE_ROLE_KEY' in line:
                print(f"      Linha {i}: {line.strip()[:80]}")
else:
    print(f"   ❌ .env (raiz) NÃO existe")

print(f"\n🔍 Qual está a ser usado pela API?")
print(f"   A API procura primeiro em: backend/.env")
print(f"   Depois procura em: .env (raiz)")

if env_backend.exists() and env_root.exists():
    print(f"\n⚠️ ATENÇÃO: Há DOIS ficheiros .env!")
    print(f"   A API vai usar: backend/.env (primeiro)")
    print(f"   Se quiseres usar o da raiz, move ou apaga backend/.env")

print("\n" + "="*60)
