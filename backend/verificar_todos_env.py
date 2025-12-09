#!/usr/bin/env python3
"""
Verifica TODOS os ficheiros .env* no projeto
"""

from pathlib import Path
import os

print("\n" + "="*60)
print("🔍 VERIFICAR TODOS OS FICHEIROS .env*")
print("="*60)

backend_dir = Path(__file__).resolve().parent
root_dir = backend_dir.parent

# Procura todos os ficheiros .env*
env_files = []
for directory in [backend_dir, root_dir]:
    for file in directory.glob(".env*"):
        if file.is_file():
            env_files.append(file)

print(f"\n📁 Ficheiros .env* encontrados:")
if env_files:
    for env_file in env_files:
        print(f"   ✅ {env_file}")
        
        # Verifica conteúdo
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"      Total de linhas: {len(lines)}")
                
                # Procura SUPABASE_SERVICE_ROLE_KEY
                for i, line in enumerate(lines, 1):
                    if 'SUPABASE_SERVICE_ROLE_KEY' in line:
                        parts = line.split('=', 1)
                        value = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                        print(f"      Linha {i}: SUPABASE_SERVICE_ROLE_KEY = {'✅' if value else '❌'} ({len(value)} chars)")
                        if not value:
                            print(f"         ⚠️ VALOR VAZIO!")
                        break
                else:
                    print(f"      ⚠️ SUPABASE_SERVICE_ROLE_KEY não encontrado neste ficheiro")
        except Exception as e:
            print(f"      ❌ Erro ao ler: {e}")
else:
    print("   ❌ Nenhum ficheiro .env* encontrado!")

# Testa ordem de carregamento
print(f"\n🧪 TESTE DE ORDEM DE CARREGAMENTO:")
print("-" * 60)

try:
    from dotenv import load_dotenv
    
    # Simula a ordem atual do código
    env_paths = [
        backend_dir / ".env.local",
        backend_dir / ".env",
        root_dir / ".env.local",
        root_dir / ".env",
    ]
    
    print("Ordem de carregamento:")
    for i, env_path in enumerate(env_paths, 1):
        exists = env_path.exists()
        print(f"   {i}. {env_path} {'✅' if exists else '❌'}")
        
        if exists:
            # Carrega e verifica
            load_dotenv(env_path, override=True)
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            print(f"      Após carregar: URL={'✅' if url else '❌'}, KEY={'✅' if key else '❌'}")
    
    # Resultado final
    print(f"\n📊 RESULTADO FINAL:")
    final_url = os.getenv("SUPABASE_URL", "")
    final_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    print(f"   SUPABASE_URL: {'✅' if final_url else '❌'} ({len(final_url)} chars)")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅' if final_key else '❌'} ({len(final_key)} chars)")
    
    if not final_key:
        print(f"\n⚠️ PROBLEMA: KEY está vazio após carregar todos os .env*")
        print(f"   Verifica se algum .env.local está a sobrescrever com valor vazio!")
        
except ImportError:
    print("❌ python-dotenv não instalado")

print("\n" + "="*60)
