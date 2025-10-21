# BalanceSheet-Automation.ps1
# Sistema automatizado de consulta y almacenamiento de Balance Sheet

# Cargar modulos
. "$PSScriptRoot\modules\LaudusAPI.ps1"
. "$PSScriptRoot\modules\MongoDB.ps1"

# Cargar configuracion
$config = Get-Content "$PSScriptRoot\config.json" | ConvertFrom-Json

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  LAUDUS BALANCE SHEET AUTOMATION" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Inicio: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "Plazo final: 06:00 AM" -ForegroundColor Gray
Write-Host ""

# Calcular fecha (dia anterior)
$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
Write-Host "Fecha a consultar: $yesterday" -ForegroundColor Cyan
Write-Host ""

# Endpoints a consultar
$endpoints = @(
    @{ Name = "totals"; Collection = $config.mongodb.collections.totals },
    @{ Name = "standard"; Collection = $config.mongodb.collections.standard },
    @{ Name = "8Columns"; Collection = $config.mongodb.collections.eightColumns }
)

# Estado de endpoints
$endpointStatus = @{}
foreach ($ep in $endpoints) {
    $endpointStatus[$ep.Name] = @{
        Completed = $false
        Attempts = 0
        LastError = $null
    }
}

# Crear archivos de log
$dateStamp = Get-Date -Format "yyyy-MM-dd"
$successLog = "$PSScriptRoot\logs\success\$dateStamp-success.log"
$errorLog = "$PSScriptRoot\logs\errors\$dateStamp-errors.log"

function Write-Log {
    param(
        [string]$Message,
        [string]$Type = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Type] $Message"
    
    if ($Type -eq "ERROR") {
        Add-Content -Path $errorLog -Value $logMessage
        Write-Host $logMessage -ForegroundColor Red
    }
    else {
        Add-Content -Path $successLog -Value $logMessage
        Write-Host $logMessage -ForegroundColor Green
    }
}

# Obtener token inicial
Write-Host "[1/4] Obteniendo token de autenticacion..." -ForegroundColor Yellow
$token = Get-LaudusToken -Config $config.laudus

if (-not $token) {
    Write-Log "FATAL: No se pudo obtener token de autenticacion" "ERROR"
    exit 1
}

Write-Host "[OK] Token obtenido" -ForegroundColor Green
Write-Host ""

# Verificar conexion MongoDB
Write-Host "[2/4] Verificando conexion MongoDB..." -ForegroundColor Yellow
$mongoOk = Test-MongoDBConnection -ConnectionString $config.mongodb.connectionString

if (-not $mongoOk) {
    Write-Log "ADVERTENCIA: No se pudo verificar conexion MongoDB (continuando de todos modos)" "ERROR"
}
Write-Host ""

# Loop principal hasta las 6 AM
Write-Host "[3/4] Iniciando consultas..." -ForegroundColor Yellow
Write-Host ""

$endTime = Get-Date -Hour 6 -Minute 0 -Second 0
$currentHour = (Get-Date).Hour

# Si ya pasaron las 6 AM, establecer limite para manana
if ($currentHour -ge 6) {
    $endTime = $endTime.AddDays(1)
}

$attemptNumber = 1

while ((Get-Date) -lt $endTime) {
    Write-Host "--- Intento #$attemptNumber ---" -ForegroundColor Cyan
    Write-Host "Hora actual: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    $allCompleted = $true
    
    foreach ($endpoint in $endpoints) {
        $epName = $endpoint.Name
        
        # Saltar si ya fue completado
        if ($endpointStatus[$epName].Completed) {
            Write-Host "[SKIP] $epName (ya completado)" -ForegroundColor DarkGray
            continue
        }
        
        $allCompleted = $false
        $endpointStatus[$epName].Attempts++
        
        Write-Host "[RUN] Consultando /$epName..." -ForegroundColor Yellow
        
        # Renovar token cada 3 intentos
        if ($attemptNumber % 3 -eq 0) {
            Write-Host "  Renovando token..." -ForegroundColor Gray
            $token = Get-LaudusToken -Config $config.laudus
            if (-not $token) {
                Write-Log "Error renovando token para $epName" "ERROR"
                continue
            }
        }
        
        # Consultar endpoint
        $result = Get-BalanceSheetData `
            -Token $token `
            -Endpoint $epName `
            -DateTo $yesterday `
            -Parameters $config.endpoints.parameters `
            -BaseUrl $config.laudus.baseUrl `
            -Timeout $config.endpoints.timeout
        
        if ($result.Success) {
            Write-Host "[SUCCESS] $epName - $($result.Count) registros obtenidos" -ForegroundColor Green
            
            # Guardar en MongoDB
            Write-Host "  Guardando en MongoDB..." -ForegroundColor Gray
            $saveResult = Save-ToMongoDB `
                -ConnectionString $config.mongodb.connectionString `
                -Database $config.mongodb.database `
                -Collection $endpoint.Collection `
                -Data $result.Data `
                -Date $yesterday `
                -EndpointType $epName
            
            if ($saveResult.Success) {
                Write-Host "[OK] Guardado en MongoDB" -ForegroundColor Green
                $endpointStatus[$epName].Completed = $true
                Write-Log "Endpoint $epName completado: $($result.Count) registros guardados en $($endpoint.Collection)"
            }
            else {
                Write-Host "[ERROR] No se pudo guardar en MongoDB: $($saveResult.Error)" -ForegroundColor Red
                Write-Log "Error guardando $epName en MongoDB: $($saveResult.Error)" "ERROR"
            }
        }
        else {
            Write-Host "[FAIL] $epName - $($result.Error)" -ForegroundColor Red
            $endpointStatus[$epName].LastError = $result.Error
            Write-Log "Intento #$($endpointStatus[$epName].Attempts) fallido para $epName : $($result.Error)" "ERROR"
        }
        
        Write-Host ""
    }
    
    # Si todos completados, salir
    if ($allCompleted) {
        Write-Host "=====================================" -ForegroundColor Green
        Write-Host "  TODOS LOS ENDPOINTS COMPLETADOS!" -ForegroundColor Green
        Write-Host "=====================================" -ForegroundColor Green
        Write-Log "Proceso completado exitosamente. Todos los endpoints procesados."
        break
    }
    
    # Esperar antes del siguiente intento
    $remainingTime = ($endTime - (Get-Date)).TotalMinutes
    
    if ($remainingTime -le 0) {
        Write-Host "=====================================" -ForegroundColor Red
        Write-Host "  TIEMPO AGOTADO (06:00 AM)" -ForegroundColor Red
        Write-Host "=====================================" -ForegroundColor Red
        Write-Log "Proceso finalizado por tiempo agotado (06:00 AM)" "ERROR"
        break
    }
    
    Write-Host "Esperando $($config.schedule.retryDelaySeconds) segundos antes del proximo intento..." -ForegroundColor Yellow
    Write-Host "Tiempo restante: $([math]::Round($remainingTime, 1)) minutos" -ForegroundColor Gray
    Write-Host ""
    
    Start-Sleep -Seconds $config.schedule.retryDelaySeconds
    $attemptNumber++
}

# Resumen final
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  RESUMEN FINAL" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

foreach ($ep in $endpoints) {
    $status = $endpointStatus[$ep.Name]
    $statusText = if ($status.Completed) { "[OK]" } else { "[PENDIENTE]" }
    $color = if ($status.Completed) { "Green" } else { "Red" }
    
    Write-Host "$statusText $($ep.Name) - Intentos: $($status.Attempts)" -ForegroundColor $color
    if ($status.LastError -and -not $status.Completed) {
        Write-Host "  Ultimo error: $($status.LastError)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Fin: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "Logs guardados en:" -ForegroundColor Gray
Write-Host "  Success: $successLog" -ForegroundColor Gray
Write-Host "  Errors: $errorLog" -ForegroundColor Gray
