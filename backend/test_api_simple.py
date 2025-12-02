#!/usr/bin/env python3
"""
Script simples para testar se a API pode iniciar
"""

import sys
from pathlib import Path

# Adiciona backend ao path
BACKEND_DIR = Path(__file__).resolve().parent
API_DIR = BACKEND_DIR / "Api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

print("🔍 Verificando imports...")

try:
    print("  - Importando FastAPI...")
    from fastapi import FastAPI
    print("  ✅ FastAPI OK")
except ImportError as e:
    print(f"  ❌ FastAPI não encontrado: {e}")
    print("  💡 Instala com: pip install fastapi uvicorn")
    sys.exit(1)

try:
    print("  - Importando uvicorn...")
    import uvicorn
    print("  ✅ uvicorn OK")
except ImportError as e:
    print(f"  ❌ uvicorn não encontrado: {e}")
    print("  💡 Instala com: pip install uvicorn")
    sys.exit(1)

try:
    print("  - Importando main.py...")
    sys.path.insert(0, str(API_DIR))
    from main import app
    print("  ✅ main.py importado com sucesso")
except Exception as e:
    print(f"  ❌ Erro ao importar main.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Tudo OK! Podes iniciar a API com:")
print("   cd backend/Api")
print("   python -m uvicorn main:app --reload --port 8000")
