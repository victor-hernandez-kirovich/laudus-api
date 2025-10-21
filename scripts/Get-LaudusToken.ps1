# Get-LaudusToken.ps1
# Obtiene un token JWT de la API de Laudus

param(
    [string]$UserName = "API",
    [string]$Password = "api123",
    [string]$CompanyVATId = "77548834-4"
)

$body = @{
    userName = $UserName
    password = $Password
    companyVATId = $CompanyVATId
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.laudus.cl/security/login" -Method Post -Body $body -ContentType "application/json"
    
    Write-Host "✅ Token obtenido exitosamente" -ForegroundColor Green
    Write-Host "Expira: $($response.expiration)" -ForegroundColor Gray
    
    # Retornar el token
    return $response.token
}
catch {
    Write-Host "❌ Error al obtener token: $($_.Exception.Message)" -ForegroundColor Red
    return $null
}
