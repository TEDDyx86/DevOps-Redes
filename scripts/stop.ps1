$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    docker compose down
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar os servicos.' }
    Write-Host 'Laboratorio encerrado. Historico preservado nos volumes.'
} finally { Pop-Location }
