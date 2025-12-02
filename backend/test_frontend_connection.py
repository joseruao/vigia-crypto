#!/usr/bin/env python3
"""
Teste para verificar se o frontend consegue comunicar com o backend
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_cors():
    """Testa se CORS está configurado corretamente"""
    print("\n" + "="*60)
    print("🧪 TESTE DE CORS")
    print("="*60)
    
    try:
        # Simula request do frontend
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type"
        }
        
        # OPTIONS request (preflight)
        response = requests.options(
            f"{API_BASE}/alerts/predictions",
            headers=headers,
            timeout=5
        )
        
        print(f"OPTIONS Status: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'N/A')}")
        print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'N/A')}")
        
        # GET request normal
        response = requests.get(
            f"{API_BASE}/alerts/predictions",
            headers={"Origin": "http://localhost:3000"},
            timeout=5
        )
        
        print(f"\nGET Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CORS OK! Recebidos {len(data)} predictions")
        else:
            print(f"❌ Erro: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_endpoints():
    """Testa endpoints principais"""
    print("\n" + "="*60)
    print("🧪 TESTE DE ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("GET", "/alerts/predictions"),
        ("GET", "/alerts/holdings"),
        ("POST", "/alerts/ask", {"prompt": "Que tokens achas que vão ser listados?"}),
    ]
    
    for method, path, *data in endpoints:
        print(f"\n📡 {method} {path}")
        try:
            if method == "GET":
                r = requests.get(f"{API_BASE}{path}", timeout=5)
            else:
                r = requests.post(f"{API_BASE}{path}", json=data[0] if data else {}, timeout=5)
            
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                try:
                    result = r.json()
                    if isinstance(result, list):
                        print(f"   ✅ Lista com {len(result)} itens")
                    elif isinstance(result, dict):
                        if "answer" in result:
                            print(f"   ✅ Resposta: {result.get('answer', '')[:100]}...")
                        elif "items" in result:
                            print(f"   ✅ Objeto com {len(result.get('items', []))} items")
                        else:
                            print(f"   ✅ Objeto: {list(result.keys())}")
                except:
                    print(f"   ✅ Resposta (texto): {r.text[:100]}...")
            else:
                print(f"   ❌ Erro: {r.text[:200]}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 TESTE DE COMUNICAÇÃO FRONTEND-BACKEND")
    print("="*60)
    
    test_cors()
    test_endpoints()
    
    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)
