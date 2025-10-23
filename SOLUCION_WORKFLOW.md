# 🔧 Solución al Error 401 del Workflow

## 📋 Resumen del Problema

El workflow de GitHub Actions estaba fallando con errores **401 Unauthorized** al intentar acceder a los endpoints de balance sheet de Laudus. Los logs mostraban que la autenticación inicial era exitosa, pero las peticiones subsecuentes fallaban.

## 🔍 Causas Identificadas

1. **Manejo incorrecto del token JWT**: El token de autenticación no se estaba extrayendo correctamente de la respuesta de la API
2. **Headers no persistentes**: Los headers de autenticación no se actualizaban correctamente después de obtener el token
3. **Versión incorrecta de Python**: Los workflows especificaban Python 3.14 que no existe
4. **Secretos de GitHub no configurados**: Advertencias sobre secretos no definidos en el repositorio
5. **Falta de logging detallado**: No había suficiente información de debug para diagnosticar el problema

## ✅ Cambios Realizados

### 1. Actualización de Python en Workflows
- **Archivos modificados**: 
  - `.github/workflows/laudus-daily.yml`
  - `.github/workflows/laudus-manual.yml`
- **Cambio**: Python 3.14 → Python 3.13 (versión estable más reciente)

### 2. Mejora en la Autenticación (ambos scripts)
- **Archivos modificados**:
  - `scripts/fetch_balancesheet.py`
  - `scripts/fetch_balancesheet_manual.py`

**Mejoras implementadas**:
```python
# Antes:
self.token = response.text.strip('"')
self.session.headers.update({'Authorization': f'Bearer {self.token}'})

# Ahora:
# Maneja múltiples formatos de respuesta (JSON, texto plano)
try:
    token_data = response.json()
    if isinstance(token_data, dict) and 'token' in token_data:
        self.token = token_data['token']
    elif isinstance(token_data, str):
        self.token = token_data
    else:
        self.token = str(token_data)
except:
    self.token = response.text.strip().strip('"').strip("'")

# Actualiza todos los headers necesarios
self.session.headers.update({
    'Authorization': f'Bearer {self.token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
})
```

### 3. Mejora en el Manejo de Errores
**Nuevo logging detallado**:
- Muestra la URL completa que se está consultando
- Incluye información sobre los parámetros de la petición
- Verifica que el token esté presente antes de hacer peticiones
- Captura y muestra el status code y respuesta en caso de error HTTP
- Distingue entre errores de timeout, HTTP y generales

### 4. Documentación de Configuración
- **Nuevo archivo**: `.github/SETUP_SECRETS.md`
- Instrucciones detalladas para configurar los 6 secretos requeridos
- Guía de troubleshooting para problemas comunes
- Notas sobre seguridad y mejores prácticas

## 🚀 Acciones Requeridas

### PASO 1: Configurar Secretos en GitHub ⚠️ **CRÍTICO**

Ve a tu repositorio en GitHub y configura estos secretos:

```
Settings → Secrets and variables → Actions → New repository secret
```

**Secretos requeridos**:
1. `LAUDUS_API_URL` - URL de la API (ej: https://api.laudus.cl)
2. `LAUDUS_USERNAME` - Usuario de la API (generalmente "API")
3. `LAUDUS_PASSWORD` - Contraseña de la API ⚠️
4. `LAUDUS_COMPANY_VAT` - RUT sin puntos ni guiones
5. `MONGODB_URI` - Connection string completo de MongoDB Atlas ⚠️
6. `MONGODB_DATABASE` - Nombre de la base de datos

**Ver guía completa**: `.github/SETUP_SECRETS.md`

### PASO 2: Verificar IPs en MongoDB Atlas

Para que GitHub Actions pueda conectarse:
1. Ve a MongoDB Atlas
2. Network Access → Add IP Address
3. Agrega: `0.0.0.0/0` (permite todas las IPs)
   - O configura IPs específicas de GitHub Actions si prefieres más seguridad

### PASO 3: Commit y Push de los Cambios

```powershell
git add .
git commit -m "Fix: Corregir error 401 en workflow de Laudus

- Actualizar Python 3.14 a 3.13
- Mejorar extracción y manejo del token JWT
- Agregar logging detallado para debugging
- Actualizar headers de sesión correctamente
- Agregar documentación de configuración de secretos"
git push origin main
```

### PASO 4: Probar el Workflow Manualmente

1. Ve a tu repositorio en GitHub
2. Actions → "Laudus Balance Sheet Daily Automation"
3. Run workflow → Run workflow (botón verde)
4. Monitorea los logs para verificar que funcione

## 🧪 Verificación de Éxito

El workflow está funcionando correctamente cuando veas en los logs:

```
✅ Authentication successful
✅ MongoDB connection successful
✅ totals: XXX records retrieved
✅ Saved to MongoDB: balance_totals (XXX records)
✅ standard: XXX records retrieved
✅ Saved to MongoDB: balance_standard (XXX records)
✅ 8Columns: XXX records retrieved
✅ Saved to MongoDB: balance_8columns (XXX records)
✅ ALL ENDPOINTS COMPLETED SUCCESSFULLY!
```

## 🐛 Troubleshooting

### Si sigues viendo 401 Unauthorized:

1. **Verifica las credenciales**:
   - Confirma que `LAUDUS_PASSWORD` sea correcto
   - Verifica que `LAUDUS_COMPANY_VAT` sea válido
   - Prueba las credenciales manualmente con Postman o curl

2. **Verifica el formato del token**:
   - Los nuevos logs mostrarán "Token length: X chars"
   - Si es 0 o muy corto, hay un problema con la autenticación

3. **Verifica la URL de la API**:
   - Confirma que `LAUDUS_API_URL` sea correcta
   - No debe tener "/" al final

### Si hay errores de MongoDB:

1. Verifica que `MONGODB_URI` sea válido
2. Confirma que las IPs de GitHub Actions estén permitidas
3. Verifica que `MONGODB_DATABASE` exista o pueda ser creada

### Si los secretos no se leen:

1. Los nombres deben ser EXACTAMENTE como se especifican (case-sensitive)
2. Después de agregar secretos, vuelve a ejecutar el workflow
3. En los logs, los secretos aparecen como `***`

## 📊 Monitoreo Continuo

El workflow está configurado para:
- **Ejecución automática**: Diariamente a las 11:30 PM hora Chile
- **Reintentos**: Hasta 60 intentos con espera de 5 minutos entre cada uno
- **Renovación de token**: Cada 3 intentos
- **Logs persistentes**: Se guardan como artifacts por 30 días

## 📞 Soporte

Si después de seguir estos pasos sigues teniendo problemas:

1. Revisa los logs completos del workflow en GitHub Actions
2. Descarga los artifacts de logs para análisis detallado
3. Verifica que todos los secretos estén configurados correctamente
4. Prueba ejecutar el script localmente con las mismas variables de entorno

---

**Última actualización**: 23 de Octubre, 2025
**Estado**: Pendiente de pruebas después de configurar secretos
