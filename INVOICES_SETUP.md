# Sistema de Facturas Mensuales - Laudus

## 📋 Descripción

Sistema completo para obtener, almacenar y visualizar facturas mensuales desde la API de Laudus. Incluye automatización, almacenamiento en MongoDB y dashboard interactivo.

## 🏗️ Arquitectura

### Backend (Scripts Python)
- **Script**: `scripts/fetch_invoices_monthly.py`
- **Función**: Obtiene facturas mes por mes desde la API de Laudus
- **Almacenamiento**: MongoDB colección `invoices_by_month`
- **Endpoint API**: `/reports/sales/invoices/ByMonth`

### Automatización (GitHub Actions)
- **Workflow**: `.github/workflows/laudus-invoices-backfill.yml`
- **Tipo**: Ejecución manual (workflow_dispatch)
- **Propósito**: Carga histórica y backfill de datos

### API Routes (Next.js)
- **Route**: `app/api/data/invoices/route.ts`
- **Función**: Sirve datos desde MongoDB al frontend
- **Filtros**: Por mes individual o rango de fechas

### Frontend (Dashboard)
- **Página**: `app/dashboard/invoices/page.tsx`
- **Función**: Visualización de facturas mensuales con métricas y comparativos

## 📊 Estructura de Datos

### MongoDB Document
```json
{
  "month": "2025-01",
  "year": 2025,
  "monthNumber": 1,
  "totalAmount": 150000000,
  "quantity": 1500,
  "invoicesCount": 250,
  "insertedAt": "2025-10-29T12:00:00.000Z",
  "data": {
    "result": "string",
    "salesInvoicesList": [],
    "totalAmount": 150000000,
    "totalAmountNotPaidAge": 5000000,
    "associatedDocumentsList": [],
    "totalAmountWithoutDiscount": 160000000,
    "quantity": 1500
  }
}
```

## 🚀 Uso

### 1. Carga Inicial de Datos

Ejecutar el workflow manualmente desde GitHub:

```
GitHub → Actions → "Laudus Invoices - Backfill Historical Data" → Run workflow
```

**Parámetros por defecto:**
- Año inicial: 2025
- Mes inicial: 1 (Enero)
- Año final: 2025
- Mes final: 10 (Octubre)
- Saltar existentes: false

### 2. Ejecución Local (Desarrollo)

```bash
# Navegar al directorio de scripts
cd laudus-api/scripts

# Configurar variables de entorno
export LAUDUS_PASSWORD="tu_password"
export LAUDUS_COMPANY_VAT="tu_rut"
export MONGODB_URI="tu_mongodb_uri"
export INVOICES_START_YEAR="2025"
export INVOICES_START_MONTH="1"
export INVOICES_END_YEAR="2025"
export INVOICES_END_MONTH="10"

# Ejecutar script
python fetch_invoices_monthly.py
```

### 3. Personalizar Rango de Fechas

Modificar variables de entorno en el workflow o localmente:

```yaml
INVOICES_START_YEAR: '2024'
INVOICES_START_MONTH: '6'
INVOICES_END_YEAR: '2025'
INVOICES_END_MONTH: '10'
```

### 4. Saltar Meses Existentes

Para no sobrescribir datos existentes:

```yaml
SKIP_EXISTING_MONTHS: 'true'
```

## 📈 Dashboard

### Métricas Generales
- **Ventas Totales**: Suma de todas las ventas del período
- **Total Facturas**: Cantidad total de facturas emitidas
- **Cantidad Items**: Total de items vendidos
- **Promedio Mensual**: Ventas promedio por mes

### Métricas por Mes
- Ventas del mes (total y sin descuento)
- Número de facturas emitidas
- Ticket promedio
- Monto pendiente de pago
- Porcentaje de pendiente vs total

### Tabla Comparativa
- Vista mensual con todas las métricas
- Expandible para ver detalles adicionales
- Headers fijos para scroll vertical
- Ordenado por mes descendente

## 🔧 Configuración

### Variables de Entorno Requeridas

```bash
# API Laudus
LAUDUS_API_URL=https://api.laudus.cl
LAUDUS_USERNAME=API
LAUDUS_PASSWORD=<secret>
LAUDUS_COMPANY_VAT=<secret>

# MongoDB
MONGODB_URI=<secret>
MONGODB_DATABASE=laudus_data

# Configuración del Script
INVOICES_START_YEAR=2025
INVOICES_START_MONTH=1
INVOICES_END_YEAR=2025
INVOICES_END_MONTH=10
SKIP_EXISTING_MONTHS=false
DELAY_BETWEEN_MONTHS=5  # segundos
```

### GitHub Secrets Requeridos

1. `LAUDUS_PASSWORD`
2. `LAUDUS_COMPANY_VAT`
3. `MONGODB_URI`

## 📅 Rango de Fechas Implementado

- **Inicio**: Enero 2025
- **Fin**: Octubre 2025
- **Total**: 10 meses de datos

## 🔄 Mantenimiento

### Agregar Nuevos Meses

1. Ejecutar workflow manualmente con nuevo rango de fechas
2. O modificar variables y ejecutar script localmente

### Actualizar Datos Existentes

1. Establecer `SKIP_EXISTING_MONTHS=false`
2. Ejecutar workflow para sobrescribir datos

### Verificar Datos en MongoDB

```javascript
// MongoDB Compass o CLI
use laudus_data
db.invoices_by_month.find().sort({month: -1})
db.invoices_by_month.countDocuments()
```

## 🎯 Próximas Mejoras

- [ ] Workflow automático mensual (1ro de cada mes)
- [ ] Gráficos de tendencias y comparativas
- [ ] Filtros por cliente, vendedor, producto
- [ ] Export a Excel/PDF
- [ ] Análisis predictivo de ventas
- [ ] Dashboard de documentos asociados

## 📝 Logs

Los logs se guardan en:
- **Local**: `scripts/logs/YYYY-MM-DD-invoices.log`
- **GitHub Actions**: Artifacts (7 días de retención)

## ⚙️ Timeouts y Delays

- **Timeout por petición**: 30 minutos (1800s)
- **Delay entre meses**: 5 segundos
- **Reintentos**: 3 intentos por mes
- **Timeout workflow**: 2 horas

## 🐛 Troubleshooting

### Error: "Authentication failed"
- Verificar `LAUDUS_PASSWORD` y `LAUDUS_COMPANY_VAT`
- Revisar que el usuario API tenga permisos

### Error: "MongoDB connection failed"
- Verificar `MONGODB_URI`
- Verificar whitelist de IPs en MongoDB Atlas

### Error: "Timeout fetching invoices"
- Aumentar `CONFIG['timeout']` en el script
- Reducir rango de fechas (menos meses por ejecución)

### No aparecen datos en dashboard
- Verificar que la colección `invoices_by_month` tenga datos
- Revisar logs del API route en Next.js
- Verificar formato de fechas en MongoDB

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs en `scripts/logs/`
2. Verificar GitHub Actions output
3. Consultar documentación de Laudus API
