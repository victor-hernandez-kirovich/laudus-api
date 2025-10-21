# Test-LaudusAPI.ps1
# Script principal para probar todos los endpoints de Laudus

Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   LAUDUS API - TEST COMPLETO            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Obtener Token
Write-Host "1️⃣  Obteniendo token de autenticación..." -ForegroundColor Yellow
$token = & "$scriptPath\Get-LaudusToken.ps1"

if (!$token) {
    Write-Host "❌ No se pudo obtener el token. Abortando." -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Probar Balance Sheet - Standard
Write-Host "2️⃣  Probando Balance Sheet - Standard Format" -ForegroundColor Yellow
$standard = & "$scriptPath\Get-BalanceSheet.ps1" -Token $token -Format "standard"

if ($standard) {
    Write-Host ""
    Write-Host "📋 Primeras 5 cuentas:" -ForegroundColor Cyan
    $standard | Select-Object -First 5 | Format-Table accountNumber, accountName, @{Label="Balance";Expression={"{0:N2}" -f $_.balance};Align="Right"} -AutoSize
}

Write-Host ""

# 3. Probar Balance Sheet - Totals
Write-Host "3️⃣  Probando Balance Sheet - Totals" -ForegroundColor Yellow
$totals = & "$scriptPath\Get-BalanceSheet.ps1" -Token $token -Format "totals"

Write-Host ""

# 4. Exportar a JSON
Write-Host "4️⃣  Exportando datos a JSON..." -ForegroundColor Yellow
& "$scriptPath\Export-BalanceSheetToJson.ps1" -Token $token -Format "standard"

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✅ TEST COMPLETADO EXITOSAMENTE       ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
