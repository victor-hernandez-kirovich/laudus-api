# Script para probar API de Laudus desde PowerShell
# Ejecutar: .\test-laudus-api.ps1

Write-Host "=== LAUDUS API TEST ===" -ForegroundColor Cyan
Write-Host ""

# 1. Obtener token
Write-Host "1. Obteniendo token de autenticación..." -ForegroundColor Yellow
$body = @{
    userName = "API"
    password = "api123"
    companyVATId = "77548834-4"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "https://api.laudus.cl/security/login" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ Token obtenido exitosamente" -ForegroundColor Green
    Write-Host "   Expira: $($loginResponse.expiration)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "❌ Error al obtener token: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# 2. Configurar headers
$headers = @{
    Authorization = "Bearer $($loginResponse.token)"
    Accept = "application/json"
}

# 3. Probar Balance Sheet - Standard
Write-Host "2. Obteniendo Balance Sheet (Standard)..." -ForegroundColor Yellow
try {
    $standardResponse = Invoke-RestMethod -Uri "https://api.laudus.cl/accounting/balanceSheet/standard?dateTo=2025-10-20&showAccountsWithZeroBalance=false&showOnlyAccountsWithActivity=true" -Method Get -Headers $headers
    Write-Host "✅ Balance Sheet Standard obtenido" -ForegroundColor Green
    Write-Host "   Total de cuentas: $($standardResponse.Count)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Primeras 3 cuentas:" -ForegroundColor Cyan
    $standardResponse | Select-Object -First 3 | Format-Table accountNumber, accountName, balance
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Probar Balance Sheet - Totals
Write-Host "3. Obteniendo Balance Sheet (Totals)..." -ForegroundColor Yellow
try {
    $totalsResponse = Invoke-RestMethod -Uri "https://api.laudus.cl/accounting/balanceSheet/totals" -Method Get -Headers $headers
    Write-Host "✅ Balance Sheet Totals obtenido" -ForegroundColor Green
    Write-Host "   Total de registros: $($totalsResponse.Count)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== FIN DEL TEST ===" -ForegroundColor Cyan
