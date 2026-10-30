$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    python scripts/configure.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar o ambiente.' }
    docker compose up -d --build --wait
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar. Verifique se o Docker Desktop esta aberto.' }
    python scripts/scan_vulnerabilities.py --background
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar o monitor de vulnerabilidades.' }
    Write-Host 'Dashboard: http://localhost:8000'
    Write-Host 'E-mails locais: http://localhost:8025'
    Write-Host 'O token dos controles do laboratorio esta no arquivo .env (LAB_TOKEN).'
} finally { Pop-Location }
