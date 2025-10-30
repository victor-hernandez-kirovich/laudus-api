# Sistema de Facturas por Sucursal - Laudus Dashboard

## Descripción
Sistema automatizado para extraer y visualizar datos de facturas agregados por sucursal desde el ERP Laudus.

## Arquitectura

### Componentes
1. **Script Python**: `scripts/fetch_invoices_by_branch.py`
   - Extrae datos del endpoint `/reports/sales/invoices/byBranch`
   - Autentica con Laudus API
   - Guarda en MongoDB colección `invoices_by_branch`
   - Manejo de errores y reintentos

2. **GitHub Actions**: `.github/workflows/laudus-invoices-by-branch.yml`
   - Workflow manual (workflow_dispatch)
   - Parámetros configurables: fecha inicio y fin
   - Ejecuta el script Python en Ubuntu
   - Sube logs como artifacts

3. **API Route**: `app/api/data/invoices/branch/route.ts`
   - Endpoint GET: `/api/data/invoices/branch`
   - Query opcional: `?dateRange=2025-01-01_2025-10-31`
   - Retorna datos desde MongoDB

## Estructura de Datos

### MongoDB Collection: `invoices_by_branch`
```javascript
{
  dateRange: "2025-01-01_2025-10-31",
  startDate: "2025-01-01",
  endDate: "2025-10-31",
  branches: [
    {
      branch: "SUCURSAL MATRIZ",
      net: 125000000,
      netPercentage: 45.5,
      margin: 25000000,
      marginPercentage: 20.0,
      discounts: 5000000,
      discountsPercentage: 4.0
    },
    // ... más sucursales
  ],
  totalNet: 275000000,
  totalMargin: 55000000,
  totalDiscounts: 11000000,
  avgMarginPercentage: 20.0,
  avgDiscountPercentage: 4.0,
  branchCount: 15,
  insertedAt: ISODate("2025-01-15T10:30:00.000Z")
}
```

### Response del API de Laudus
```json
[
  {
    "branch": "SUCURSAL MATRIZ",
    "net": 125000000,
    "netPercentage": 45.5,
    "margin": 25000000,
    "marginPercentage": 20.0,
    "discounts": 5000000,
    "discountsPercentage": 4.0
  }
]
```

## Uso

### 1. Ejecutar GitHub Actions Workflow
1. Ve a: https://github.com/victor-hernandez-kirovich/laudus-api/actions
2. Selecciona "Laudus Invoices by Branch - Fetch Data"
3. Click "Run workflow"
4. Configura parámetros:
   - `start_date`: Fecha inicio (ej: 2025-01-01)
   - `end_date`: Fecha fin (ej: 2025-10-31)
5. Click "Run workflow"

### 2. Ejecutar Manualmente (Local)

```bash
cd laudus-api/scripts

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
$env:LAUDUS_PASSWORD = "8@HcHDzUgHweD*A"
$env:LAUDUS_COMPANY_VAT = "76914386-5"
$env:MONGODB_URI = "mongodb+srv://kirovich_dev:%408%40HcHDzUgHweD%2AA@kirovich.oedv2gq.mongodb.net/"
$env:BRANCH_START_DATE = "2025-01-01"
$env:BRANCH_END_DATE = "2025-10-31"

# Ejecutar script
python fetch_invoices_by_branch.py
```

### 3. Ver Dashboard
- URL: http://localhost:3000/dashboard/invoices/branch
- Muestra datos de la fecha más reciente en MongoDB

## Características del Dashboard

### Tarjetas Resumidas (4)
1. **Total Neto**: Suma de ventas netas de todas las sucursales
2. **Total Margen**: Suma de márgenes con promedio porcentual
3. **Total Descuentos**: Suma de descuentos con promedio porcentual
4. **Sucursales**: Cantidad total de sucursales

### Tabla de Sucursales
- Ordenada por ventas netas (descendente)
- Columnas: Sucursal, Ventas Netas, % Participación, Margen, % Margen, Descuentos, % Descuento
- Detalles expandibles al hacer click
- Códigos de color para % Margen:
  - Verde: ≥ 20%
  - Amarillo: 10% - 19.9%
  - Rojo: < 10%

### Top Rankings (2 paneles)
1. **Top 5 por Ventas**: Sucursales con mayores ventas netas
2. **Top 5 por Margen %**: Sucursales con mayor porcentaje de margen

## Configuración

### Variables de Entorno (GitHub Secrets)
```bash
LAUDUS_PASSWORD=8@HcHDzUgHweD*A
LAUDUS_COMPANY_VAT=76914386-5
MONGODB_URI=mongodb+srv://kirovich_dev:%408%40HcHDzUgHweD%2AA@kirovich.oedv2gq.mongodb.net/
```

### Configuración del Script
```python
CONFIG = {
    'api_url': 'https://api.laudus.cl',
    'username': 'API',
    'mongodb_database': 'laudus_data',
    'timeout': 1800,  # 30 minutos
    'max_retries': 3
}
```

## API Endpoints

### Laudus ERP API
```
GET https://api.laudus.cl/reports/sales/invoices/byBranch
Query Params:
  - dateFrom: YYYY-MM-DD
  - dateTo: YYYY-MM-DD
Headers:
  - Authorization: Bearer {token}
```

### Dashboard API
```
GET http://localhost:3000/api/data/invoices/branch
Query Params (opcional):
  - dateRange: YYYY-MM-DD_YYYY-MM-DD
Response:
  {
    success: true,
    count: 1,
    data: [{ dateRange, branches, ... }]
  }
```

## Logs
Los logs se guardan en:
- Local: `scripts/logs/YYYY-MM-DD-invoices-branch.log`
- GitHub Actions: Artifacts descargables por 30 días

## Troubleshooting

### Error de Autenticación
```bash
# Verificar credenciales
echo $env:LAUDUS_PASSWORD
echo $env:LAUDUS_COMPANY_VAT
```

### Error de MongoDB
```bash
# Verificar conexión
echo $env:MONGODB_URI
# Debe contener password URL-encoded: %408%40HcHDzUgHweD%2AA
```

### Sin Datos en Dashboard
1. Verificar que el workflow se ejecutó exitosamente
2. Verificar datos en MongoDB:
   ```javascript
   use laudus_data
   db.invoices_by_branch.find().pretty()
   ```
3. Verificar logs del script
4. Verificar que las fechas están correctas

### Timeout del Script
- El timeout por defecto es 30 minutos
- Si es necesario, aumentar en el workflow:
  ```yaml
  timeout-minutes: 180  # 3 horas
  ```

## Diferencias con Facturas Mensuales

| Característica | Mensuales | Por Sucursal |
|----------------|-----------|--------------|
| Endpoint | `/byMonth` | `/byBranch` |
| Agregación | Por mes | Por sucursal |
| Período | Múltiples meses | Rango único |
| Colección | `invoices_by_month` | `invoices_by_branch` |
| Documentos | 1 por mes | 1 por período |
| YoY Comparison | ✅ | ❌ |
| Multi-branch | ❌ | ✅ |

## Próximos Pasos
- [ ] Ejecutar workflow inicial con datos 2025-01-01 a 2025-10-31
- [ ] Agregar filtros por fecha en el dashboard
- [ ] Implementar gráficos comparativos
- [ ] Agregar exportación a Excel
- [ ] Implementar facturas diarias (futuro)

## Notas Importantes
- Un único documento por rango de fechas en MongoDB
- El array `branches` contiene todas las sucursales del período
- Los porcentajes de participación suman 100%
- El dashboard siempre muestra el período más reciente
- Se puede ejecutar el workflow múltiples veces con diferentes fechas
