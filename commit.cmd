@echo off
:: =====================================================
:: Script rápido para commit & push
:: Uso: basta dar duplo clique neste ficheiro
:: (deve estar dentro da pasta principal do repositório)
:: =====================================================

setlocal enabledelayedexpansion

:: Detecta o diretório atual
set "REPO=%cd%"

:: Pede mensagem do commit
set /p MESSAGE="Mensagem do commit: "

if "%MESSAGE%"=="" (
  set MESSAGE=auto commit
)

echo.
echo [INFO] A fazer commit em %REPO%
cd /d "%REPO%"

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
