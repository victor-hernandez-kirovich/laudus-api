# README.md - Balance Sheet Automation

## 📋 Sistema de Automatización Laudus Balance Sheet

Sistema automatizado para consultar los endpoints de Balance Sheet de Laudus API y almacenar los resultados en MongoDB Atlas.

---

## 🚀 Características

✅ **Consulta automática diaria** a las 01:00 AM (UTC-4 Santiago)  
✅ **3 endpoints** de Balance Sheet (totals, standard, 8Columns)  
✅ **Reintentos inteligentes** hasta las 06:00 AM  
✅ **Almacenamiento en MongoDB Atlas** automático  
✅ **Logs separados** (éxitos y errores)  
✅ **Fecha dinámica** (siempre día anterior)  
✅ **Windows Task Scheduler** integrado  

---

## 📁 Estructura

```
automation/
├── config.json                     # Configuración
├── BalanceSheet-Automation.ps1     # Script principal
├── Setup-Scheduler.ps1             # Configurar Task Scheduler
├── modules/
│   ├── LaudusAPI.ps1              # Funciones API Laudus
│   └── MongoDB.ps1                # Funciones MongoDB
└── logs/
    ├── success/                   # Logs exitosos
    │   └── YYYY-MM-DD-success.log
    └── errors/                    # Logs de errores
        └── YYYY-MM-DD-errors.log
```

---

## ⚙️ Configuración

### 1. Verificar `config.json`

Archivo ya configurado con:
- Credenciales Laudus API
- Connection string MongoDB Atlas
- Hora de inicio: 01:00 AM
- Plazo límite: 06:00 AM
- Timeout: 900 segundos (15 min) por endpoint

### 2. Configurar Task Scheduler

Ejecutar como **Administrador**:

```powershell
cd automation
.\Setup-Scheduler.ps1
```

Esto creará una tarea programada que ejecutará el script diariamente a la 01:00 AM.

---

## 🎯 Uso

### Ejecución Automática (Recomendado)

Una vez configurado el Task Scheduler, el sistema correrá automáticamente todas las noches.

### Ejecución Manual

```powershell
cd automation
.\BalanceSheet-Automation.ps1
```

### Ejecutar tarea programada manualmente

```powershell
Start-ScheduledTask -TaskName "Laudus-BalanceSheet-Daily"
```

---

## 📊 Lógica de Reintentos

1. **01:00 AM** - Inicio automático
2. Consulta los 3 endpoints en orden:
   - `/balanceSheet/totals`
   - `/balanceSheet/standard`
   - `/balanceSheet/8Columns`
3. Si alguno falla → **espera 5 minutos** → reintenta solo los fallidos
4. Continúa reintentando hasta las **06:00 AM**
5. Guarda cada resultado exitoso en MongoDB inmediatamente

---

## 🗄️ Estructura MongoDB

### Database: `laudus_data`

### Collections:

**1. balance_totals**
```json
{
  "date": "2025-10-20",
  "endpointType": "totals",
  "recordCount": 105,
  "insertedAt": "2025-10-21T05:15:32.123Z",
  "data": [...]
}
```

**2. balance_standard**
```json
{
  "date": "2025-10-20",
  "endpointType": "standard",
  "recordCount": 105,
  "insertedAt": "2025-10-21T05:16:45.456Z",
  "data": [...]
}
```

**3. balance_8columns**
```json
{
  "date": "2025-10-20",
  "endpointType": "8Columns",
  "recordCount": 105,
  "insertedAt": "2025-10-21T05:18:23.789Z",
  "data": [...]
}
```

---

## 📝 Logs

### Logs de Éxito
`logs/success/YYYY-MM-DD-success.log`

Registra:
- Token obtenido correctamente
- Endpoints consultados exitosamente
- Número de registros guardados
- Hora de finalización

### Logs de Errores
`logs/errors/YYYY-MM-DD-errors.log`

Registra:
- Errores de autenticación
- Timeouts
- Errores de MongoDB
- Intentos fallidos

---

## 🔧 Parámetros Configurables

En `config.json`:

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `startTime` | "01:00" | Hora de inicio |
| `endTime` | "06:00" | Hora límite |
| `retryDelaySeconds` | 300 | Espera entre reintentos (5 min) |
| `timeout` | 900 | Timeout por endpoint (15 min) |
| `showAccountsWithZeroBalance` | false | Filtro Laudus |
| `showOnlyAccountsWithActivity` | true | Filtro Laudus |

---

## ⚠️ Troubleshooting

### Problema: Token expira durante la ejecución
**Solución:** El sistema renueva el token automáticamente cada 3 intentos.

### Problema: Endpoint da timeout
**Solución:** El sistema reintenta automáticamente. Si persiste, revisar logs de errores.

### Problema: No se conecta a MongoDB
**Solución:** Verificar connection string en `config.json` y que el cluster esté activo en Atlas.

### Problema: Task Scheduler no ejecuta
**Solución:** 
1. Abrir `taskschd.msc`
2. Buscar "Laudus-BalanceSheet-Daily"
3. Click derecho → "Run"
4. Ver "Last Run Result"

---

## 📞 Comandos Útiles

```powershell
# Ver estado de la tarea programada
Get-ScheduledTask -TaskName "Laudus-BalanceSheet-Daily"

# Ejecutar manualmente
Start-ScheduledTask -TaskName "Laudus-BalanceSheet-Daily"

# Ver últimos logs
Get-Content .\logs\success\$(Get-Date -Format 'yyyy-MM-dd')-success.log -Tail 20
Get-Content .\logs\errors\$(Get-Date -Format 'yyyy-MM-dd')-errors.log -Tail 20

# Eliminar tarea programada
Unregister-ScheduledTask -TaskName "Laudus-BalanceSheet-Daily" -Confirm:$false
```

---

## 🎯 Próximos Pasos

1. ✅ Sistema configurado y listo
2. ⏳ **PENDIENTE:** Instalar driver MongoDB para PowerShell (opcional)
3. ⏳ **PENDIENTE:** Habilitar Data API en MongoDB Atlas para inserción real
4. ⏳ Prueba manual ejecutando `.\BalanceSheet-Automation.ps1`
5. ⏳ Verificar que funcione la tarea programada mañana a la 01:00 AM

---

## 📧 Notificaciones (Futuro)

Para agregar notificaciones por email cuando complete/falle, editar `BalanceSheet-Automation.ps1` y agregar función `Send-EmailNotification` al final del script.

---

**Creado:** 2025-10-20  
**Última actualización:** 2025-10-20
