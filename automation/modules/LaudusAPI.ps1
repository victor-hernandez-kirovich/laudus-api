# LaudusAPI.ps1
# Modulo para interactuar con la API de Laudus

function Get-LaudusToken {
    param(
        [Parameter(Mandatory=$true)]
        $Config
    )
    
    try {
        $body = @{
            userName = $Config.userName
            password = $Config.password
            companyVATId = $Config.companyVATId
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$($Config.baseUrl)/security/login" `
            -Method POST `
            -Body $body `
            -ContentType "application/json" `
            -TimeoutSec 30
        
        return $response.token
    }
    catch {
        Write-Error "Error obteniendo token: $($_.Exception.Message)"
        return $null
    }
}

function Get-BalanceSheetData {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Token,
        
        [Parameter(Mandatory=$true)]
        [string]$Endpoint,
        
        [Parameter(Mandatory=$true)]
        [string]$DateTo,
        
        [Parameter(Mandatory=$true)]
        $Parameters,
        
        [Parameter(Mandatory=$true)]
        [string]$BaseUrl,
        
        [int]$Timeout = 900
    )
    
    try {
        # Construir query string
        $queryParams = "dateTo=$DateTo"
        
        if ($Parameters.showAccountsWithZeroBalance -ne $null) {
            $queryParams += "&showAccountsWithZeroBalance=$($Parameters.showAccountsWithZeroBalance.ToString().ToLower())"
        }
        
        if ($Parameters.showOnlyAccountsWithActivity -ne $null) {
            $queryParams += "&showOnlyAccountsWithActivity=$($Parameters.showOnlyAccountsWithActivity.ToString().ToLower())"
        }
        
        $url = "$BaseUrl/accounting/balanceSheet/$Endpoint`?$queryParams"
        
        $headers = @{
            Authorization = "Bearer $Token"
            Accept = "application/json"
        }
        
        Write-Host "  Consultando: /balanceSheet/$Endpoint" -ForegroundColor Gray
        Write-Host "  URL: $url" -ForegroundColor DarkGray
        
        $data = Invoke-RestMethod -Uri $url `
            -Headers $headers `
            -TimeoutSec $Timeout
        
        return @{
            Success = $true
            Data = $data
            Count = $data.Count
        }
    }
    catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
            Data = $null
        }
    }
}
