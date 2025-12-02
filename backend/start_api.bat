@echo off
echo ========================================
echo Iniciando API Vigia Crypto
echo ========================================
cd /d %~dp0\Api
echo Diretorio: %CD%
echo.
echo Verificando Python...
python --version
echo.
echo Instalando dependencias se necessario...
pip install fastapi uvicorn python-dotenv requests supabase -q
echo.
echo Iniciando servidor na porta 8000...
echo.
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
pause
