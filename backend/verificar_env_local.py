#!/usr/bin/env python3
"""
Verifica se .env.local está a sobrescrever o .env
"""

from pathlib import Path
import os

print("\n" + "="*60)
print("🔍 VERIFICAR .env.local")
print("="*60)

root_dir = Path(__file__).resolve().parent.parent
env_local = root_dir / ".env.local"

print(f"\n📁 Ficheiro: {env_local}")
print(f"   Existe: {env_local.exists()}")

if env_local.exists():
    print(f"\n📄 Conteúdo do .env.local:")
    print("-" * 60)
    
    try:
        with open(env_local, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        supabase_found = False
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            if 'SUPABASE' in line_stripped:
                supabase_found = True
                print(f"Linha {i}: {line_stripped[:80]}")
                
                if 'SUPABASE_SERVICE_ROLE_KEY' in line_stripped:
                    if '=' in line_stripped:
                        parts = line_stripped.split('=', 1)
                        value = parts[1].strip().strip('"').strip("'")
                        if value:
                            print(f"   ✅ Tem valor: {len(value)} chars")
                        else:
                            print(f"   ❌ PROBLEMA: Valor VAZIO! Isto vai sobrescrever o .env!")
                    else:
                        print(f"   ⚠️ Sem '='")
        
        if not supabase_found:
            print("   ✅ Não tem variáveis SUPABASE (não vai interferir)")
        else:
            print(f"\n⚠️ ATENÇÃO: .env.local tem variáveis SUPABASE!")
            print(f"   Se o valor estiver vazio, vai sobrescrever o .env correto!")
            
    except Exception as e:
        print(f"   ❌ Erro ao ler: {e}")

# Testa ordem de carregamento
print(f"\n🧪 TESTE DE CARREGAMENTO:")
print("-" * 60)

try:
    from dotenv import load_dotenv
    
    # Carrega .env primeiro
    env_normal = root_dir / ".env"
    if env_normal.exists():
        load_dotenv(env_normal, override=True)
        url1 = os.getenv("SUPABASE_URL", "")
        key1 = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        print(f"Após carregar .env:")
        print(f"   URL: {'✅' if url1 else '❌'} ({len(url1)} chars)")
        print(f"   KEY: {'✅' if key1 else '❌'} ({len(key1)} chars)")
    
    # Depois carrega .env.local (simula o que pode acontecer)
    if env_local.exists():
        load_dotenv(env_local, override=True)
        url2 = os.getenv("SUPABASE_URL", "")
        key2 = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        print(f"\nApós carregar .env.local:")
        print(f"   URL: {'✅' if url2 else '❌'} ({len(url2)} chars)")
        print(f"   KEY: {'✅' if key2 else '❌'} ({len(key2)} chars)")
        
        if key1 and not key2:
            print(f"\n❌ PROBLEMA CONFIRMADO!")
            print(f"   KEY foi sobrescrito de {len(key1)} para {len(key2)} chars")
            print(f"   SOLUÇÃO: Remove ou corrige .env.local")
        
except ImportError:
    print("❌ python-dotenv não instalado")

print("\n" + "="*60)
