"""
Shim para facilitar o arranque da API FastAPI.
Este ficheiro permite usar 'app:app' como ASGI app no Render.

Uso no Render (Root Directory = raiz do projeto):
  Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório backend ao Python path
# Isso garante que os imports absolutos funcionem
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"

# Verifica se backend existe
if not BACKEND_DIR.exists():
    raise RuntimeError(f"Diretório backend não encontrado em {BACKEND_DIR}")

# Adiciona backend ao path se ainda não estiver
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Importa a app FastAPI
# Este import funciona porque backend está agora no sys.path
try:
    from Api.main import app
except ImportError as e:
    raise ImportError(
        f"Erro ao importar Api.main: {e}\n"
        f"ROOT: {ROOT}\n"
        f"BACKEND_DIR: {BACKEND_DIR}\n"
        f"sys.path (primeiros 3): {sys.path[:3]}"
    ) from e

# Exporta para uso do uvicorn/gunicorn
__all__ = ["app"]
