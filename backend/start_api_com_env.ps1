Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando API Vigia Crypto" -ForegroundColor Cyan
Write-Host "Com variáveis de ambiente definidas" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Define variáveis de ambiente ANTES de iniciar
$env:SUPABASE_URL="https://qynnajpvxnqcmkzrhpde.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF5bm5hanB2eG5xY21renJocGRlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzQzODg2MywiZXhwIjoyMDczMDE0ODYzfQ.P6jxgFLmQZnVSalWB3UykT9QO3EAW-tljTdoGZ6pY7A"

Write-Host "`n✅ Variáveis de ambiente definidas" -ForegroundColor Green

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptPath\Api"

Write-Host "`nDiretorio: $(Get-Location)" -ForegroundColor Yellow
Write-Host "`nVerificando Python..." -ForegroundColor Yellow
python --version

Write-Host "`nIniciando servidor na porta 8000..." -ForegroundColor Green
Write-Host "Abre http://localhost:8000 no browser`n" -ForegroundColor Green

python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
