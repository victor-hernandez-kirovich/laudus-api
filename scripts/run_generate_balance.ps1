# Script para ejecutar la generación del Balance General
# Uso: .\run_generate_balance.ps1 -Date "2025-07-31"

param(
    [Parameter(Mandatory=$true)]
    [string]$Date
)

# Ruta al archivo .env.local del dashboard
$envFile = "..\..\laudus-dashboard\.env.local"

if (-not (Test-Path $envFile)) {
    Write-Error "No se encuentra el archivo .env.local en laudus-dashboard"
    exit 1
}

# Leer variables de entorno del archivo
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.+)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        Set-Item -Path "env:$name" -Value $value
    }
}

if (-not $env:MONGODB_URI) {
    Write-Error "MONGODB_URI no encontrado en .env.local"
    exit 1
}

Write-Host "Generando Balance General para fecha: $Date" -ForegroundColor Green
Write-Host ""

# Ejecutar el script Python
python generate_balance_general.py --date $Date
