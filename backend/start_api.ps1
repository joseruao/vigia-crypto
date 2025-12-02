Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando API Vigia Crypto" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptPath\Api"

Write-Host "`nDiretorio: $(Get-Location)" -ForegroundColor Yellow
Write-Host "`nVerificando Python..." -ForegroundColor Yellow
python --version

Write-Host "`nInstalando dependencias se necessario..." -ForegroundColor Yellow
pip install fastapi uvicorn python-dotenv requests supabase -q

Write-Host "`nIniciando servidor na porta 8000..." -ForegroundColor Green
Write-Host "Abre http://localhost:8000 no browser`n" -ForegroundColor Green

python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
