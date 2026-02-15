#!/usr/bin/env python3
"""
Script para remover moedas de teste do Supabase.
Remove registos com tokens: TEST, FOO, etc.
"""

import os
import sys
from pathlib import Path

# Adiciona backend ao path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
from utils import supa

# Carrega .env
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Tokens de teste a remover
TEST_TOKENS = ["TEST", "FOO", "Pnut"]

def remove_test_tokens():
    """Remove tokens de teste do Supabase"""
    print("="*60)
    print("🗑️  REMOVENDO MOEDAS DE TESTE DO SUPABASE")
    print("="*60)
    
    if not supa.ok():
        print("❌ Erro: Supabase não configurado!")
        return
    
    total_removed = 0
    
    for token in TEST_TOKENS:
        print(f"\n🔍 Procurando registos com token: {token}")
        
        # Busca registos com este token
        params = {
            "token": f"eq.{token}",
            "select": "id,token,exchange"
        }
        
        try:
            r = supa.rest_get("transacted_tokens", params=params)
            
            if r.status_code == 200:
                data = r.json() or []
                count = len(data)
                
                if count > 0:
                    print(f"   ✅ Encontrados {count} registos")
                    
                    # Remove cada registo
                    for item in data:
                        item_id = item.get("id")
                        token_name = item.get("token", "N/A")
                        exchange = item.get("exchange", "N/A")
                        
                        if item_id:
                            try:
                                # Usa rest_delete com params para filtrar por ID
                                delete_params = {"id": f"eq.{item_id}"}
                                delete_r = supa.rest_delete("transacted_tokens", params=delete_params)
                                if delete_r.status_code in [200, 204]:
                                    print(f"   ✅ Removido: {token_name} ({exchange})")
                                    total_removed += 1
                                else:
                                    print(f"   ❌ Erro ao remover {token_name}: {delete_r.status_code} - {delete_r.text[:100]}")
                            except Exception as e:
                                print(f"   ❌ Erro ao remover {token_name}: {e}")
                else:
                    print(f"   ℹ️  Nenhum registo encontrado")
            else:
                print(f"   ❌ Erro ao buscar: {r.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print("\n" + "="*60)
    print(f"✅ Remoção concluída: {total_removed} registos removidos")
    print("="*60)

if __name__ == "__main__":
    remove_test_tokens()

