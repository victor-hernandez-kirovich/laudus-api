# GitHub Secrets Setup Guide

Para que los workflows de GitHub Actions funcionen correctamente, necesitas configurar los siguientes secretos en tu repositorio.

## ⚙️ Cómo configurar secretos en GitHub

1. Ve a tu repositorio en GitHub
2. Click en **Settings** (Configuración)
3. En el menú lateral, click en **Secrets and variables** → **Actions**
4. Click en **New repository secret**
5. Agrega cada uno de los secretos listados abajo

## 🔐 Secretos Requeridos

### LAUDUS_API_URL
- **Descripción**: URL base de la API de Laudus
- **Valor ejemplo**: `https://api.laudus.cl`
- **Nota**: No incluir slash final

### LAUDUS_USERNAME
- **Descripción**: Usuario para autenticación en Laudus
- **Valor por defecto**: `API`
- **Nota**: Confirma con tu administrador de Laudus

### LAUDUS_PASSWORD
- **Descripción**: Contraseña del usuario de la API
- **Valor**: Tu contraseña de la API de Laudus
- **⚠️ CRÍTICO**: Nunca subas este valor al código

### LAUDUS_COMPANY_VAT
- **Descripción**: RUT de la empresa sin puntos ni guiones
- **Valor ejemplo**: `123456789`
- **Formato**: Solo números, sin formato

### MONGODB_URI
- **Descripción**: Connection string de MongoDB Atlas
- **Valor ejemplo**: `mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority`
- **Formato**: Debe incluir credenciales y opciones de conexión
- **⚠️ CRÍTICO**: Nunca subas este valor al código

### MONGODB_DATABASE
- **Descripción**: Nombre de la base de datos en MongoDB
- **Valor ejemplo**: `laudus_data`
- **Nota**: Debe coincidir con tu configuración de MongoDB

## ✅ Verificación

Después de configurar todos los secretos:

1. Ve a la pestaña **Actions** en tu repositorio
2. Ejecuta manualmente el workflow `Laudus Balance Sheet Daily Automation`
3. Verifica que no haya errores de "Context access might be invalid"

## 🐛 Solución de Problemas

### Error 401 Unauthorized
- Verifica que `LAUDUS_PASSWORD` y `LAUDUS_COMPANY_VAT` sean correctos
- Confirma que el usuario tenga permisos para acceder a la API

### Error de conexión a MongoDB
- Verifica que `MONGODB_URI` sea válido
- Confirma que las IPs de GitHub Actions estén en la whitelist de MongoDB Atlas
- **IMPORTANTE**: En MongoDB Atlas, agrega `0.0.0.0/0` a las IPs permitidas para GitHub Actions

### Los secretos no se leen
- Asegúrate de que los nombres estén escritos exactamente como se especifica
- Los secretos distinguen entre mayúsculas y minúsculas
- Después de agregar/modificar secretos, vuelve a ejecutar el workflow

## 📝 Notas Adicionales

- Los secretos están encriptados y no son visibles después de crearlos
- Solo puedes actualizar o eliminar secretos, no verlos
- Los secretos están disponibles para todos los workflows del repositorio
- En los logs de GitHub Actions, los secretos se muestran como `***`
