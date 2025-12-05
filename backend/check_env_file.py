#!/usr/bin/env python3
"""
Script para verificar o conteúdo do ficheiro .env (sem mostrar valores completos por segurança)
"""

from pathlib import Path
import re

print("\n" + "="*60)
print("🔍 VERIFICAÇÃO DO FICHEIRO .env")
print("="*60)

backend_dir = Path(__file__).resolve().parent
env_paths = [
    backend_dir / ".env",
    backend_dir.parent / ".env",
]

found_env = None
for env_path in env_paths:
    if env_path.exists():
        found_env = env_path
        print(f"\n✅ Ficheiro encontrado: {env_path}")
        break

if not found_env:
    print("\n❌ Nenhum ficheiro .env encontrado!")
    print("\n💡 Cria um ficheiro .env em um destes locais:")
    for env_path in env_paths:
        print(f"   - {env_path}")
    exit(1)

# Lê o ficheiro
try:
    with open(found_env, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n📄 Conteúdo do ficheiro ({len(content)} caracteres):")
    print("-" * 60)
    
    lines = content.split('\n')
    supabase_url_found = False
    supabase_key_found = False
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Ignora linhas vazias e comentários
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # Verifica SUPABASE_URL
        if 'SUPABASE_URL' in line_stripped:
            supabase_url_found = True
            if '=' in line_stripped:
                parts = line_stripped.split('=', 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()
                # Remove aspas se existirem
                var_value = var_value.strip('"').strip("'")
                print(f"Linha {i}: ✅ {var_name}")
                print(f"   Valor: {var_value[:30]}...{var_value[-10:] if len(var_value) > 40 else ''} ({len(var_value)} chars)")
                if not var_value:
                    print(f"   ⚠️ PROBLEMA: Valor vazio!")
                elif var_value.startswith('${') or '${' in var_value:
                    print(f"   ⚠️ PROBLEMA: Parece ser uma variável não expandida!")
            else:
                print(f"Linha {i}: ❌ {line_stripped[:50]}...")
                print(f"   ⚠️ PROBLEMA: Falta o sinal '='")
        
        # Verifica SUPABASE_SERVICE_ROLE_KEY
        elif 'SUPABASE_SERVICE_ROLE_KEY' in line_stripped or 'SUPABASE_KEY' in line_stripped:
            supabase_key_found = True
            if '=' in line_stripped:
                parts = line_stripped.split('=', 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()
                # Remove aspas se existirem
                var_value = var_value.strip('"').strip("'")
                print(f"Linha {i}: ✅ {var_name}")
                print(f"   Valor: {var_value[:20]}...{var_value[-10:] if len(var_value) > 30 else ''} ({len(var_value)} chars)")
                if not var_value:
                    print(f"   ⚠️ PROBLEMA: Valor vazio!")
                elif var_value.startswith('${') or '${' in var_value:
                    print(f"   ⚠️ PROBLEMA: Parece ser uma variável não expandida!")
                elif var_value == 'missing' or var_value == 'N/A':
                    print(f"   ⚠️ PROBLEMA: Valor placeholder!")
            else:
                print(f"Linha {i}: ❌ {line_stripped[:50]}...")
                print(f"   ⚠️ PROBLEMA: Falta o sinal '='")
        
        # Mostra outras variáveis (mas não os valores completos)
        elif '=' in line_stripped and not line_stripped.startswith('#'):
            parts = line_stripped.split('=', 1)
            var_name = parts[0].strip()
            var_value = parts[1].strip()
            if var_value:
                print(f"Linha {i}: 📋 {var_name} = {'*' * min(20, len(var_value))}")
    
    print("-" * 60)
    
    # Resumo
    print("\n📊 RESUMO:")
    print(f"   SUPABASE_URL: {'✅ Encontrado' if supabase_url_found else '❌ NÃO ENCONTRADO'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Encontrado' if supabase_key_found else '❌ NÃO ENCONTRADO'}")
    
    if not supabase_url_found:
        print("\n💡 SOLUÇÃO:")
        print("   Adiciona esta linha ao .env:")
        print("   SUPABASE_URL=https://xxxxx.supabase.co")
    
    if not supabase_key_found:
        print("\n💡 SOLUÇÃO:")
        print("   Adiciona esta linha ao .env:")
        print("   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...")
        print("\n   ⚠️ ATENÇÃO: Verifica se o nome está correto!")
        print("   Deve ser: SUPABASE_SERVICE_ROLE_KEY")
        print("   NÃO: SUPABASE_KEY ou SUPABASE_API_KEY")
    
    # Verifica problemas comuns
    print("\n🔍 VERIFICAÇÕES:")
    if 'SUPABASE_KEY' in content and 'SUPABASE_SERVICE_ROLE_KEY' not in content:
        print("   ⚠️ PROBLEMA: Encontrado 'SUPABASE_KEY' mas deveria ser 'SUPABASE_SERVICE_ROLE_KEY'")
    
    if content.count('SUPABASE_SERVICE_ROLE_KEY') > 1:
        print("   ⚠️ PROBLEMA: SUPABASE_SERVICE_ROLE_KEY aparece múltiplas vezes (usa apenas uma)")
    
    # Verifica espaços
    if 'SUPABASE_SERVICE_ROLE_KEY =' in content or 'SUPABASE_SERVICE_ROLE_KEY= ' in content:
        print("   ⚠️ PROBLEMA: Espaços em volta do '=' podem causar problemas")
        print("   Correto: SUPABASE_SERVICE_ROLE_KEY=valor")
        print("   Errado: SUPABASE_SERVICE_ROLE_KEY = valor")
    
except Exception as e:
    print(f"\n❌ Erro ao ler ficheiro: {e}")

print("\n" + "="*60)
