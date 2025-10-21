# Setup-Scheduler.ps1
# Configura Windows Task Scheduler para ejecutar la automatizacion

$scriptPath = "$PSScriptRoot\BalanceSheet-Automation.ps1"
$taskName = "Laudus-BalanceSheet-Daily"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  CONFIGURAR TASK SCHEDULER" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si ya existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Tarea existente encontrada. Eliminando..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Crear accion
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Crear trigger (1:00 AM diario)
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "01:00"

# Configuracion adicional
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Crear principal (usuario actual)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Registrar tarea
Write-Host "Registrando tarea programada..." -ForegroundColor Yellow

$task = Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Automatizacion diaria de consulta Balance Sheet Laudus y almacenamiento en MongoDB Atlas"

Write-Host ""
Write-Host "[OK] Tarea programada creada exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "Detalles:" -ForegroundColor Cyan
Write-Host "  Nombre: $taskName" -ForegroundColor Gray
Write-Host "  Hora: 01:00 AM (diario)" -ForegroundColor Gray
Write-Host "  Script: $scriptPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Para ver la tarea:" -ForegroundColor Yellow
Write-Host "  taskschd.msc" -ForegroundColor White
Write-Host ""
Write-Host "Para ejecutar manualmente:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host ""
Write-Host "Para eliminar la tarea:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
