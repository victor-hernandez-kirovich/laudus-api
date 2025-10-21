# Test-Automation.ps1
# Script de prueba rapida del sistema de automatizacion

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  TEST - AUTOMATION SYSTEM" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Cargar modulos
. "$PSScriptRoot\modules\LaudusAPI.ps1"
. "$PSScriptRoot\modules\MongoDB.ps1"

# Cargar configuracion
$config = Get-Content "$PSScriptRoot\config.json" | ConvertFrom-Json

Write-Host "[1/3] Probando obtencion de token..." -ForegroundColor Yellow
$token = Get-LaudusToken -Config $config.laudus

if ($token) {
    Write-Host "[OK] Token obtenido: $($token.Substring(0,50))..." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] No se pudo obtener token" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Probando consulta endpoint (totals)..." -ForegroundColor Yellow

$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
Write-Host "Fecha: $yesterday" -ForegroundColor Gray

$result = Get-BalanceSheetData `
    -Token $token `
    -Endpoint "totals" `
    -DateTo $yesterday `
    -Parameters $config.endpoints.parameters `
    -BaseUrl $config.laudus.baseUrl `
    -Timeout 120

if ($result.Success) {
    Write-Host "[OK] Datos obtenidos: $($result.Count) registros" -ForegroundColor Green
    Write-Host ""
    Write-Host "Primeros 3 registros:" -ForegroundColor Cyan
    $result.Data | Select-Object -First 3 | Format-Table
}
else {
    Write-Host "[FAIL] $($result.Error)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[3/3] Probando conexion MongoDB..." -ForegroundColor Yellow
$mongoOk = Test-MongoDBConnection -ConnectionString $config.mongodb.connectionString

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  TEST COMPLETADO" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
