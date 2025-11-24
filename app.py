"""
Shim para facilitar o arranque da API FastAPI.
Este ficheiro permite usar 'app:app' como ASGI app no Render.
Alternativamente, use: uvicorn Api.main:app --app-dir backend
"""
import sys
from pathlib import Path

# Adiciona o diretório backend ao Python path
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Importa a app FastAPI
from Api.main import app

# Exporta para uso do uvicorn/gunicorn
__all__ = ["app"]
