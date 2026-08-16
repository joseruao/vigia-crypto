# AI Business Auditor - interface web local
# Corre:  .\start_auditor_web.ps1   -> abre http://localhost:8765
Set-Location $PSScriptRoot
Write-Host "AI Business Auditor - http://localhost:8765  (Ctrl+C para parar)"
python -m uvicorn auditor.web:app --port 8765
