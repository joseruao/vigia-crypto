@echo off
:: =====================================================
:: Script para commit & push do ambiente de trabalho
:: Coloca este ficheiro no Desktop e dá duplo clique
:: =====================================================

setlocal enabledelayedexpansion

:: Vai diretamente para a pasta do projeto
cd /d "C:\Users\joser\vigia_crypto"

:: Pede mensagem do commit
set /p MESSAGE="Mensagem do commit: "

if "%MESSAGE%"=="" (
  set MESSAGE=auto commit
)

echo.
echo [INFO] A fazer commit em %cd%
echo.

:: Mostra branch atual
for /f "tokens=2 delims=* " %%a in ('git branch ^| find "*"') do set BRANCH=%%a
if "%BRANCH%"=="" set BRANCH=main

:: Adiciona tudo
git add .

:: Faz commit
git commit -m "%MESSAGE%"

:: Envia para o repositório remoto
git push origin %BRANCH%

echo.
echo [OK] Commit e push efetuados com sucesso!
echo.
pause
