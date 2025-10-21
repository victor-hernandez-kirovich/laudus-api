# Export-BalanceSheetToJson.ps1
# Exporta Balance Sheet a archivo JSON

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [string]$Format = "standard",
    
    [string]$OutputPath = ".\data\balance-sheet-$(Get-Date -Format 'yyyy-MM-dd').json"
)

# Obtener datos
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = & "$scriptPath\Get-BalanceSheet.ps1" -Token $Token -Format $Format

if ($data) {
    # Crear directorio si no existe
    $outputDir = Split-Path -Parent $OutputPath
    if (!(Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Guardar a JSON
    $data | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8
    
    Write-Host "✅ Datos exportados a: $OutputPath" -ForegroundColor Green
    Write-Host "Total de registros: $($data.Count)" -ForegroundColor Cyan
}
else {
    Write-Host "❌ No se pudieron obtener los datos" -ForegroundColor Red
}
