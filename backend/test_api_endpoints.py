#!/usr/bin/env python3
"""
Script para testar os endpoints da API diretamente.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"  # Ajusta se necessário

def test_endpoint(name, method, path, data=None):
    """Testa um endpoint e mostra resultados"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTE: {name}")
    print(f"{'='*60}")
    
    url = f"{API_BASE}{path}"
    print(f"URL: {url}")
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Método {method} não suportado")
            return
        
        elapsed = time.time() - start_time
        
        print(f"⏱️  Tempo: {elapsed:.2f}s")
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, list):
                    print(f"✅ Resposta: Lista com {len(result)} itens")
                    if result:
                        print(f"   Primeiro item: {json.dumps(result[0], indent=2)[:200]}...")
                elif isinstance(result, dict):
                    if "items" in result:
                        print(f"✅ Resposta: Objeto com {len(result.get('items', []))} items")
                    else:
                        print(f"✅ Resposta: {json.dumps(result, indent=2)[:300]}...")
                else:
                    print(f"✅ Resposta: {result}")
            except:
                print(f"✅ Resposta (texto): {response.text[:200]}...")
        else:
            print(f"❌ Erro: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT (>10s)")
    except requests.exceptions.ConnectionError:
        print(f"❌ ERRO DE CONEXÃO: API não está a correr em {API_BASE}")
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 TESTE DE ENDPOINTS DA API")
    print("="*60)
    
    # Teste de health
    test_endpoint("Health Check", "GET", "/")
    
    # Teste de predictions
    test_endpoint("Predictions", "GET", "/alerts/predictions")
    
    # Teste de holdings
    test_endpoint("Holdings", "GET", "/alerts/holdings")
    
    # Teste de ask
    test_endpoint("Ask Alerts", "POST", "/alerts/ask", {"prompt": "mostra-me os tokens da binance"})
    
    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)
    print("\n💡 Dica: Se a API não estiver a correr, inicia com:")
    print("   cd backend/Api && uvicorn main:app --reload")

