# Get-BalanceSheet.ps1
# Obtiene datos del Balance Sheet desde la API de Laudus

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [string]$Format = "standard",  # standard, totals, 8Columns
    
    [string]$DateTo = (Get-Date -Format "yyyy-MM-dd"),
    
    [switch]$ShowAccountsWithZeroBalance = $false,
    
    [switch]$ShowOnlyAccountsWithActivity = $true,
    
    [string]$ShowLevels,
    
    [string]$CostCenterId,
    
    [string]$BookId
)

# Construir URL base
$baseUrl = "https://api.laudus.cl/accounting/balanceSheet/$Format"

# Construir query parameters
$params = @{}

if ($Format -eq "standard" -or $Format -eq "8Columns") {
    $params["dateTo"] = $DateTo
    
    if ($Format -eq "standard") {
        $params["showAccountsWithZeroBalance"] = $ShowAccountsWithZeroBalance.ToString().ToLower()
        $params["showOnlyAccountsWithActivity"] = $ShowOnlyAccountsWithActivity.ToString().ToLower()
        
        if ($ShowLevels) { $params["showLevels"] = $ShowLevels }
        if ($CostCenterId) { $params["costCenterId"] = $CostCenterId }
        if ($BookId) { $params["bookId"] = $BookId }
    }
}

# Construir URL completa
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
$url = if ($queryString) { "$baseUrl?$queryString" } else { $baseUrl }

# Headers
$headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/json"
}

try {
    Write-Host "📊 Obteniendo Balance Sheet ($Format)..." -ForegroundColor Yellow
    Write-Host "URL: $url" -ForegroundColor Gray
    
    $response = Invoke-RestMethod -Uri $url -Method Get -Headers $headers -TimeoutSec 120
    
    Write-Host "✅ Datos obtenidos exitosamente" -ForegroundColor Green
    Write-Host "Total de registros: $($response.Count)" -ForegroundColor Cyan
    
    return $response
}
catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
    return $null
}
