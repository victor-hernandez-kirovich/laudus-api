# 🚀 Laudus Balance Sheet Automation

Automatización completa para extracción diaria de datos de Balance Sheet desde Laudus ERP, con almacenamiento en MongoDB Atlas y visualización en dashboard interactivo.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Requisitos](#-requisitos)
- [Componentes del Sistema](#-componentes-del-sistema)
- [Instalación Local](#-instalación-local)
- [Configuración GitHub Actions](#-configuración-github-actions)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Uso y Monitoreo](#-uso-y-monitoreo)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Características

- ✅ **Automatización 100% Cloud** - GitHub Actions ejecuta diariamente a la 01:00 AM (Chile)
- ✅ **3 Endpoints Balance Sheet** - Totales, Standard, 8 Columnas
- ✅ **MongoDB Atlas** - Almacenamiento en la nube con 414 registros actuales
- ✅ **Dashboard Next.js 14** - Visualización interactiva con Recharts
- ✅ **Retry Logic** - Reintentos automáticos cada 5 minutos por hasta 6 horas
- ✅ **Backup Local** - PowerShell automation en PC como respaldo
- ✅ **Logging Completo** - GitHub Actions artifacts + archivos locales
- ✅ **Costo $0/mes** - GitHub Actions (free) + MongoDB Atlas (free) + Vercel (free)

---

## 🏗️ Arquitectura

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────────┐
│ GitHub Actions  │─────▶│ Laudus API   │─────▶│ MongoDB Atlas   │
│ (Daily 01:00 AM)│      │ (30-180s)    │      │ (3 collections) │
└─────────────────┘      └──────────────┘      └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ Next.js Dashboard│
                                                │ (Vercel)         │
                                                └─────────────────┘
```

**Flujo de datos:**
1. GitHub Actions ejecuta `scripts/fetch_balancesheet.py` diariamente
2. Python extrae datos de 3 endpoints Laudus (128, 105, 181 registros)
3. Datos se guardan en MongoDB Atlas con timestamp
4. Dashboard Next.js lee MongoDB y muestra gráficos interactivos

---

## 📦 Requisitos

### Para GitHub Actions (Producción)
- Cuenta GitHub (free)
- MongoDB Atlas (free tier M0)
- Credenciales Laudus API

### Para Desarrollo Local
- Python 3.8+ (para automation)
- PowerShell 5.1+ (para backup local)
- Node.js 18+ (para dashboard - ver laudus-dashboard/)
- MongoDB Atlas connection string

---

## 🧩 Componentes del Sistema

### 1️⃣ **Automatización Python** (GitHub Actions)
- **Archivo**: `scripts/fetch_balancesheet.py`
- **Ejecuta**: Diariamente 01:00 AM Chile (05:00 UTC)
- **Timeout**: 360 minutos (6 horas)
- **Retry**: Cada 5 minutos hasta completar
- **Output**: MongoDB Atlas + logs en GitHub artifacts

### 2️⃣ **Backup PowerShell** (Local PC)
- **Carpeta**: `automation/`
- **Ejecuta**: Windows Task Scheduler (opcional)
- **Propósito**: Backup si GitHub Actions falla
- **Output**: JSON local + MongoDB

### 3️⃣ **Scripts de Testing**
- **Carpeta**: `scripts/`
- PowerShell scripts para testing manual
- Python script principal para automation

---

## 🔧 Instalación Local

### Opción A: Solo Testing (Python)

```bash
# 1. Navegar al proyecto
cd laudus-api

# 2. Instalar dependencias Python
pip install -r scripts/requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Ejecutar manualmente
python scripts/fetch_balancesheet.py
```

### Opción B: Backup PowerShell (Windows)

```powershell
# 1. Navegar a automation
cd automation

# 2. Editar config.json con tus credenciales

# 3. Configurar Task Scheduler
.\Setup-Scheduler.ps1

# 4. Probar manualmente
.\Test-Automation.ps1
```

---

## ⚙️ Configuración GitHub Actions

### Paso 1: Crear GitHub Secrets

En tu repositorio GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Agregar los siguientes 6 secrets:

| Secret Name | Value | Descripción |
|------------|-------|-------------|
| `LAUDUS_API_URL` | `https://api.laudus.cl` | URL base de la API |
| `LAUDUS_USERNAME` | `API` | Usuario de la API |
| `LAUDUS_PASSWORD` | `tu_password` | Contraseña API |
| `LAUDUS_COMPANY_VAT` | `77548834-4` | RUT de la empresa |
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster...` | Connection string MongoDB Atlas |
| `MONGODB_DATABASE` | `laudus_data` | Nombre de la base de datos |

### Paso 2: Activar GitHub Actions

El workflow ya está configurado en `.github/workflows/laudus-daily.yml`

```yaml
# Se ejecuta automáticamente:
# - Todos los días a las 01:00 AM (Chile)
# - También puedes ejecutarlo manualmente desde GitHub Actions tab
```

### Paso 3: Verificar Primera Ejecución

1. Ve a **Actions** tab en GitHub
2. Selecciona "Laudus Balance Sheet Daily Automation"
3. Click en **Run workflow** para test manual
4. Espera ~20 minutos (depende de velocidad de Laudus API)
5. Revisa logs para confirmar éxito

---

## � Endpoints Extraídos

El sistema extrae datos de 3 endpoints de Laudus API:

| Endpoint | Descripción | Registros | Colección MongoDB |
|----------|-------------|-----------|-------------------|
| `/accounting/balanceSheet/totals` | Balance con totales por cuenta | 128 | `balance_totals` |
| `/accounting/balanceSheet/standard` | Balance formato estándar | 105 | `balance_standard` |
| `/accounting/balanceSheet/8Columns` | Balance detallado 8 columnas | 181 | `balance_8columns` |

**Parámetros utilizados:**
```python
{
    'dateTo': '2025-10-21',                    # Fecha actual (YYYY-MM-DD)
    'showAccountsWithZeroBalance': False,      # Ocultar cuentas en cero
    'showOnlyAccountsWithActivity': True       # Solo cuentas activas
}
```

**Estructura de datos guardada:**
```json
{
    "_id": "ObjectId(...)",
    "date": "2025-10-21",
    "timestamp": "2025-10-21T02:08:00Z",
    "endpoint": "balance_totals",
    "data": [
        {
            "accountCode": "1",
            "accountName": "ACTIVO",
            "debit": 123456789,
            "credit": 98765432,
            "balance": 24691357
        },
        // ... más registros
    ]
}
```

---

## 📁 Estructura del Proyecto

```
laudus-api/
│
├── .github/
│   ├── workflows/
│   │   └── laudus-daily.yml           # ✅ GitHub Actions workflow (producción)
│   └── README.md                      # Documentación GitHub Actions
│
├── scripts/
│   ├── fetch_balancesheet.py          # ✅ Script Python principal (usado por GitHub Actions)
│   ├── requirements.txt               # ✅ Dependencias Python
│   ├── Get-LaudusToken.ps1            # Testing manual
│   ├── Get-BalanceSheet.ps1           # Testing manual
│   ├── Test-LaudusAPI.ps1             # Testing manual
│   └── Export-BalanceSheetToJson.ps1  # Exportar JSON
│
├── automation/                        # ⚠️ Backup PowerShell local
│   ├── BalanceSheet-Automation.ps1    # Script principal local
│   ├── Setup-Scheduler.ps1            # Configurar Task Scheduler
│   ├── Test-Automation.ps1            # Probar automation
│   ├── Upload-ToMongoDB.ps1           # Subir a MongoDB
│   ├── config.json                    # Config local
│   ├── README.md                      # Docs automation
│   ├── modules/
│   │   ├── LaudusAPI.ps1              # Módulo API
│   │   └── MongoDB.ps1                # Módulo MongoDB
│   └── logs/                          # Logs locales (git ignored)
│       ├── errors/
│       └── success/
│
├── .env.example                       # Template variables entorno
├── .gitignore                         # Archivos ignorados por Git
├── package.json                       # Metadata del proyecto
├── Quick-BalanceSheet.ps1             # Script rápido de prueba
├── test-laudus-api.ps1                # Testing API
├── README.md                          # Este archivo
├── DEPLOYMENT.md                      # Guía de deploy
└── PROYECTO_COMPLETADO.md             # Resumen del proyecto
```

### 📂 Archivos Clave

| Archivo | Propósito | Usado por |
|---------|-----------|-----------|
| `.github/workflows/laudus-daily.yml` | Workflow GitHub Actions | Producción (cloud) |
| `scripts/fetch_balancesheet.py` | Automation Python | GitHub Actions |
| `scripts/requirements.txt` | Dependencias Python | GitHub Actions |
| `automation/BalanceSheet-Automation.ps1` | Automation PowerShell | PC local (backup) |
| `automation/config.json` | Config local | PowerShell scripts |

---

## �️ Uso y Monitoreo

### Ejecución Automática (GitHub Actions)

El sistema se ejecuta **automáticamente todos los días a la 01:00 AM** (Chile).

**Monitorear ejecuciones:**
1. Ve a tu repositorio en GitHub
2. Click en tab **Actions**
3. Ver historial de ejecuciones

**Ejecutar manualmente:**
1. Tab **Actions** → "Laudus Balance Sheet Daily Automation"
2. Click **Run workflow** → Select branch → **Run**
3. Espera 15-30 minutos (depende de velocidad de Laudus API)

### Verificar Datos en MongoDB

```python
# Conectar a MongoDB Atlas
from pymongo import MongoClient

client = MongoClient("mongodb+srv://...")
db = client.laudus_data

# Ver último registro de cada colección
print("Balance Totals:", db.balance_totals.count_documents({}))
print("Balance Standard:", db.balance_standard.count_documents({}))
print("Balance 8 Columns:", db.balance_8columns.count_documents({}))

# Ver fecha del último registro
latest = db.balance_totals.find_one(sort=[('timestamp', -1)])
print("Última actualización:", latest['timestamp'])
```

### Ver Logs

**GitHub Actions:**
- Automáticamente guarda logs en Artifacts (30 días de retención)
- Descarga desde: Actions → Run específico → Artifacts → `laudus-logs`

**PowerShell local:**
- Success: `automation/logs/success/YYYY-MM-DD.log`
- Errors: `automation/logs/errors/YYYY-MM-DD.log`

### Testing Manual

```powershell
# Test rápido con PowerShell
.\Quick-BalanceSheet.ps1

# Test completo
.\test-laudus-api.ps1

# Test Python
python scripts/fetch_balancesheet.py
```

---

## 🔍 Troubleshooting

### ❌ GitHub Actions falla con timeout

**Causa**: Laudus API tarda más de 6 horas (muy raro).

**Solución**:
1. Verificar logs en GitHub Actions Artifacts
2. Ejecutar backup PowerShell local manualmente
3. Reintentar workflow manualmente

### ❌ MongoDB connection error

**Causa**: URI inválido o credenciales incorrectas.

**Solución**:
1. Verificar secret `MONGODB_URI` en GitHub
2. Confirmar que incluye password URL-encoded (`@` → `%40`, etc.)
3. Probar conexión desde MongoDB Compass

### ❌ Laudus API retorna 401 Unauthorized

**Causa**: Credenciales incorrectas o token expirado.

**Solución**:
1. Verificar secrets en GitHub Actions
2. El script auto-renueva el token cada 3 intentos
3. Verificar que usuario API tiene permisos activos

### ❌ PowerShell "Module not found"

**Causa**: Módulos PowerShell no están en la ubicación correcta.

**Solución**:
```powershell
# Verificar estructura
cd automation
ls modules/  # Debe mostrar LaudusAPI.ps1 y MongoDB.ps1
```

### ❌ Python "Module not found"

**Causa**: Dependencias no instaladas.

**Solución**:
```bash
pip install -r scripts/requirements.txt
```

### 📊 Métricas Actuales

| Colección | Registros | Última actualización |
|-----------|-----------|----------------------|
| `balance_totals` | 128 | 2025-10-21 02:08 |
| `balance_standard` | 105 | 2025-10-21 02:20 |
| `balance_8columns` | 181 | 2025-10-21 02:21 |

**Total datos**: 414 registros en MongoDB Atlas

---

## � Documentación Adicional

- 📖 **DEPLOYMENT.md** - Guía completa de deploy paso a paso
- 📖 **PROYECTO_COMPLETADO.md** - Resumen ejecutivo del proyecto
- 📖 **automation/README.md** - Documentación PowerShell automation
- 📖 **.github/README.md** - Documentación GitHub Actions
- 📖 **C:\Users\victo\Desktop\DEPLOY-INSTRUCTIONS.md** - Instrucciones deployment
- 📖 **C:\Users\victo\Desktop\PROJECT-SUMMARY.md** - Resumen completo con arquitectura

---

## 🔗 Proyectos Relacionados

**Dashboard Interactivo**: Ver proyecto `laudus-dashboard/`
- Next.js 14 con App Router
- Gráficos interactivos con Recharts
- Conecta a MongoDB Atlas
- Deploy en Vercel
- URL: `http://localhost:3000` (desarrollo)

---

## 🎯 Checklist de Deploy

- [ ] Crear repositorio en GitHub
- [ ] Push código a GitHub
- [ ] Configurar 6 GitHub Secrets
- [ ] Activar GitHub Actions
- [ ] Ejecutar workflow manualmente (primera vez)
- [ ] Verificar datos en MongoDB Atlas
- [ ] Deploy dashboard a Vercel (ver laudus-dashboard/)
- [ ] Verificar dashboard muestra datos correctos
- [ ] Configurar dominio custom (opcional)
- [ ] Monitorear ejecución diaria

---

## 💰 Costos

| Servicio | Plan | Costo mensual |
|----------|------|---------------|
| GitHub Actions | Free tier (2000 min/mes) | **$0** |
| MongoDB Atlas | M0 (512 MB) | **$0** |
| Vercel | Hobby | **$0** |
| **TOTAL** | | **$0/mes** |

**Nota**: Uso actual ~20 minutos/día = 600 min/mes (dentro del free tier)

---

## 📄 Licencia

MIT

---

## 👤 Autor

**Proyecto de automatización Laudus Balance Sheet**

Contacto:
- MongoDB Atlas cluster: `kirovich`
- Database: `laudus_data`
- Usuario Laudus API: `API`
- RUT Empresa: `77548834-4`

---

**Sistema de extracción automática de datos Balance Sheet desde Laudus ERP**  
**Última actualización**: Octubre 2025
