#!/usr/bin/env python3
"""
Teste rápido do endpoint /alerts/ask
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_ask(prompt):
    print(f"\n{'='*60}")
    print(f"🧪 Testando: {prompt: {prompt}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{API_URL}/alerts/ask",
            json={"prompt": prompt},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Resposta recebida:")
            print(f"  - ok: {data.get('ok')}")
            print(f"  - answer: {data.get('answer', 'N/A')[:200]}...")
            print(f"  - count: {data.get('count', 0)}")
            print(f"  - items: {len(data.get('items', []))} itens")
            
            if data.get('answer'):
                print(f"\n📝 Resposta completa:")
                print(data.get('answer'))
            else:
                print("\n⚠️ Resposta sem campo 'answer'!")
                print(f"  Dados completos: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            print(f"  Resposta: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: API não está a correr em localhost:8000")
        print("   Inicia a API primeiro!")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 TESTE DO ENDPOINT /alerts/ask")
    print("="*60)
    
    # Teste 1: Pergunta sobre listings
    test_ask("Que tokens achas que vão ser listados?")
    
    # Teste 2: Pergunta sobre Binance
    test_ask("Que tokens a binance tem?")
    
    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)
