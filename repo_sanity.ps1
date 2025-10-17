# Lista ficheiros FastAPI “rivais”
Write-Host "== Procurar múltiplos main.py / Api =="
Get-ChildItem -Recurse -Force -Include main.py | ForEach-Object { $_.FullName }

# Lista diretórios chamados Api na raiz
$root = Get-Location
$apiDirs = Get-ChildItem -Directory -Force -Path $root | Where-Object { $_.Name -ieq "Api" }
if ($apiDirs) {
  Write-Host "`n[ALERTA] Existe um diretório 'Api' na RAIZ:" -ForegroundColor Yellow
  $apiDirs | ForEach-Object { Write-Host $_.FullName -ForegroundColor Yellow }
  Write-Host "Se for lixo antigo, apaga-o (y/n)?"
  $ans = Read-Host
  if ($ans -match '^[Yy]') { $apiDirs | Remove-Item -Recurse -Force }
}

# Opcional: apagar main.py rivais fora de backend/Api
$badMains = Get-ChildItem -Recurse -Force -Include main.py | Where-Object { $_.FullName -notmatch "backend[\\/]+Api[\\/]main.py$" }
if ($badMains) {
  Write-Host "`n[ALERTA] main.py suspeitos (fora de backend/Api):" -ForegroundColor Yellow
  $badMains | ForEach-Object { Write-Host $_.FullName -ForegroundColor Yellow }
  Write-Host "Apagar estes main.py (y/n)?"
  $ans2 = Read-Host
  if ($ans2 -match '^[Yy]') { $badMains | Remove-Item -Force }
}

# Confirma __init__.py
$init1 = Join-Path $root "backend/__init__.py"
$init2 = Join-Path $root "backend/Api/__init__.py"
foreach ($f in @($init1,$init2)) {
  if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f | Out-Null }
}

Write-Host "`nFeito. Faz commit/push e redeploy."
