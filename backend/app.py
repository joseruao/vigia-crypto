"""
Shim para facilitar o arranque da API FastAPI quando o Root Directory é 'backend'.
Este ficheiro permite usar 'app:app' como ASGI app no Render.

Uso no Render (com Root Directory = backend):
  Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import sys
from pathlib import Path

# Garante que o diretório backend está no path para imports absolutos
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Importa a app FastAPI
# Este import funciona porque estamos dentro de backend e backend está no sys.path
from Api.main import app

# Exporta para uso do uvicorn/gunicorn
__all__ = ["app"]

