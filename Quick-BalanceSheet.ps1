# Quick-BalanceSheet.ps1
# Script rapido para obtener Balance Sheet con un solo comando

Write-Host ">>> Obteniendo Balance Sheet de Laudus..." -ForegroundColor Cyan

# Obtener token
$body = '{"userName":"API","password":"api123","companyVATId":"77548834-4"}'
$login = Invoke-RestMethod -Uri "https://api.laudus.cl/security/login" -Method POST -Body $body -ContentType "application/json"

Write-Host "[OK] Autenticado" -ForegroundColor Green

# Obtener datos
$headers = @{
    Authorization = "Bearer $($login.token)"
    Accept = "application/json"
}

$data = Invoke-RestMethod -Uri "https://api.laudus.cl/accounting/balanceSheet/standard?dateTo=$(Get-Date -Format 'yyyy-MM-dd')&showAccountsWithZeroBalance=false&showOnlyAccountsWithActivity=true" -Headers $headers -TimeoutSec 120

Write-Host "[OK] Datos obtenidos: $($data.Count) cuentas" -ForegroundColor Green
Write-Host ""

# Mostrar resumen
Write-Host "=== RESUMEN ===" -ForegroundColor Cyan
$data | Select-Object -First 10 | Format-Table accountNumber, accountName, @{Label="Balance";Expression={"{0:N2}" -f $_.balance};Align="Right"} -AutoSize

# Exportar
if (-not (Test-Path ".\data")) {
    New-Item -Path ".\data" -ItemType Directory -Force | Out-Null
}

$outputPath = ".\data\balance-sheet-$(Get-Date -Format 'yyyy-MM-dd').json"
$data | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Encoding UTF8 -Force

Write-Host ""
Write-Host "[OK] Exportado a: $outputPath" -ForegroundColor Green
