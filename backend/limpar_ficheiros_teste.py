#!/usr/bin/env python3
"""
Script para listar e remover ficheiros de teste desnecessários.
"""

import os
from pathlib import Path

# Ficheiros de teste a remover
TEST_FILES = [
    "test_api_endpoints.py",
    "test_api_simple.py",
    "test_ask_endpoint.py",
    "test_env_loading.py",
    "test_env.py",
    "test_frontend_connection.py",
    "test_insert_data.py",
    "test_supabase_config.py",
    "test_supabase.py",
    "teste_completo.py",
    "teste_direto_api.py",
    "teste_final.py",
    "teste_rapido.py",
    "teste.py",
    "verificar_env_local.py",
    "verificar_env.py",
    "verificar_espacos.py",
    "verificar_qual_env.py",
    "verificar_todos_env.py",
    "check_env_file.py",
]

# Ficheiros de documentação de teste a remover
TEST_DOCS = [
    "DEBUG_FRONTEND.md",
    "DIAGNOSTICO.md",
    "TESTE_SUPABASE.md",
    "SOLUCAO_RLS.md",
    "INICIAR_API.md",
]

def list_test_files():
    """Lista ficheiros de teste encontrados"""
    backend_dir = Path(__file__).resolve().parent
    
    found_files = []
    found_docs = []
    
    print("="*60)
    print("🔍 PROCURANDO FICHEIROS DE TESTE")
    print("="*60)
    
    # Procura ficheiros Python de teste
    for filename in TEST_FILES:
        filepath = backend_dir / filename
        if filepath.exists():
            found_files.append(filepath)
            print(f"✅ Encontrado: {filename}")
    
    # Procura ficheiros de documentação de teste
    for filename in TEST_DOCS:
        filepath = backend_dir / filename
        if filepath.exists():
            found_docs.append(filepath)
            print(f"📄 Encontrado (doc): {filename}")
    
    return found_files, found_docs

def remove_files(files, confirm=True):
    """Remove ficheiros"""
    if not files:
        print("\n✅ Nenhum ficheiro encontrado para remover")
        return
    
    print(f"\n🗑️  Encontrados {len(files)} ficheiro(s) para remover:")
    for f in files:
        print(f"   - {f.name}")
    
    if confirm:
        response = input("\n❓ Desejas remover estes ficheiros? (s/N): ")
        if response.lower() != 's':
            print("❌ Operação cancelada")
            return
    
    removed = 0
    for filepath in files:
        try:
            filepath.unlink()
            print(f"✅ Removido: {filepath.name}")
            removed += 1
        except Exception as e:
            print(f"❌ Erro ao remover {filepath.name}: {e}")
    
    print(f"\n✅ Remoção concluída: {removed}/{len(files)} ficheiros removidos")

if __name__ == "__main__":
    import sys
    
    # Lista ficheiros
    test_files, test_docs = list_test_files()
    
    all_files = test_files + test_docs
    
    if all_files:
        print(f"\n📊 Total: {len(all_files)} ficheiro(s) encontrado(s)")
        
        # Remove se executado com --remove
        if "--remove" in sys.argv:
            remove_files(all_files, confirm=False)
        else:
            print("\n💡 Para remover, executa: python limpar_ficheiros_teste.py --remove")
            print("   Ou responde 's' quando perguntado:")
            remove_files(all_files, confirm=True)
    else:
        print("\n✅ Nenhum ficheiro de teste encontrado!")
