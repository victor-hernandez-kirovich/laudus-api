# Laudus Balance Sheet Automation - GitHub Actions

Automatización diaria para extraer datos de Balance Sheet desde Laudus API y almacenarlos en MongoDB Atlas.

## 🔧 Configuración

### 1. Secrets de GitHub

Agregar en **Settings > Secrets and variables > Actions**:

| Secret | Valor | Descripción |
|--------|-------|-------------|
| `LAUDUS_API_URL` | `https://api.laudus.cl` | URL base API Laudus |
| `LAUDUS_USERNAME` | `API` | Usuario Laudus |
| `LAUDUS_PASSWORD` | `api123` | Contraseña Laudus |
| `LAUDUS_COMPANY_VAT` | `77548834-4` | RUT empresa |
| `MONGODB_URI` | `mongodb+srv://...` | Connection string MongoDB Atlas |
| `MONGODB_DATABASE` | `laudus_data` | Nombre de base de datos |

### 2. Workflow Schedule

- **Frecuencia**: Diaria
- **Hora**: 01:00 AM Chile (05:00 UTC)
- **Timeout**: 6 horas (360 minutos)

## 🚀 Uso

### Ejecución Automática

El workflow se ejecuta automáticamente todos los días a la 01:00 AM (Chile).

### Ejecución Manual

1. Ir a **Actions** en GitHub
2. Seleccionar **Laudus Balance Sheet Daily Automation**
3. Click en **Run workflow**
4. Seleccionar branch `main`
5. Click en **Run workflow**

## 📊 Endpoints Procesados

1. **Balance Totals** → `balance_totals` collection
2. **Balance Standard** → `balance_standard` collection
3. **Balance 8 Columns** → `balance_8columns` collection

## 🔄 Flujo de Ejecución

```
1. Autenticación → Get JWT token
2. Fecha → Calcular ayer (yesterday)
3. Loop endpoints:
   - Fetch /balanceSheet/totals
   - Fetch /balanceSheet/standard
   - Fetch /balanceSheet/8Columns
4. Guardar en MongoDB Atlas
5. Reintentos cada 5 min si falla
6. Logs → GitHub Actions Artifacts
```

## 📝 Logs

Los logs se guardan como **artifacts** en GitHub Actions:

- Nombre: `laudus-logs-{run_number}`
- Retención: 30 días
- Ubicación: Actions > Workflow run > Artifacts

## ⚠️ Manejo de Errores

- **Timeout por endpoint**: 15 minutos (900 segundos)
- **Reintentos**: Cada 5 minutos hasta completar
- **Ventana total**: 6 horas
- **Exit code**: 0 (éxito), 1 (error)

## 🔍 Monitoreo

### Ver Estado

```bash
# Ver último run
gh run list --workflow=laudus-daily.yml --limit 1

# Ver logs del último run
gh run view --log
```

### Email Notifications

GitHub envía notificaciones automáticas si el workflow falla.

## 🛠️ Desarrollo Local

### Probar script Python:

```bash
# Instalar dependencias
pip install -r scripts/requirements.txt

# Configurar variables de entorno
export LAUDUS_API_URL="https://api.laudus.cl"
export LAUDUS_USERNAME="API"
export LAUDUS_PASSWORD="api123"
export LAUDUS_COMPANY_VAT="77548834-4"
export MONGODB_URI="mongodb+srv://..."
export MONGODB_DATABASE="laudus_data"

# Ejecutar
python scripts/fetch_balancesheet.py
```

## 📦 Dependencias Python

- `requests==2.32.3` - HTTP client
- `pymongo==4.15.3` - MongoDB driver
- `python-dotenv==1.0.1` - Environment variables

## 🔐 Seguridad

✅ Credenciales en GitHub Secrets (encriptadas)  
✅ No se hardcodean passwords en código  
✅ MongoDB connection string con SSL  
✅ Logs no exponen información sensible  

## 📞 Troubleshooting

### Error: "Missing required environment variables"
- Verificar que todos los secrets estén configurados en GitHub

### Error: "Failed to authenticate with Laudus API"
- Verificar credenciales (username, password, VAT)
- Verificar que la API esté disponible

### Error: "MongoDB connection failed"
- Verificar connection string
- Verificar whitelist IP en MongoDB Atlas (permitir GitHub Actions IPs)

### Endpoints lentos (>15 min)
- Normal para Laudus API (DBF database)
- El sistema reintenta automáticamente

## 📈 Historial

Los datos se almacenan con estructura:

```json
{
  "_id": "YYYY-MM-DD-{endpoint}",
  "date": "YYYY-MM-DD",
  "endpointType": "totals|standard|8Columns",
  "recordCount": 128,
  "insertedAt": "2025-10-21T05:00:00.000Z",
  "data": [...]
}
```

## 🎯 Próximos Pasos

- [ ] Email notifications personalizadas
- [ ] Dashboard de monitoreo
- [ ] Alertas si faltan datos
- [ ] Comparativas históricas

---

**Última actualización**: 2025-10-21
