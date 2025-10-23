# 🔐 Guía Paso a Paso: Configurar Secretos de GitHub

## ⚠️ Sobre los Warnings en VS Code

Los warnings que ves en los archivos `.yml` son **NORMALES y ESPERADOS**. VS Code te avisa que los secretos no están configurados en GitHub todavía.

```yaml
Context access might be invalid: LAUDUS_API_URL ❌
Context access might be invalid: LAUDUS_USERNAME ❌
Context access might be invalid: LAUDUS_PASSWORD ❌
Context access might be invalid: LAUDUS_COMPANY_VAT ❌
Context access might be invalid: MONGODB_URI ❌
Context access might be invalid: MONGODB_DATABASE ❌
```

**Estos warnings desaparecerán automáticamente después de configurar los secretos en GitHub.**

---

## 📋 Pasos para Configurar los Secretos

### PASO 1: Abre tu Repositorio en GitHub

1. Ve a: https://github.com/victor-hernandez-kirovich/laudus-api
2. Asegúrate de estar en la rama `main`

### PASO 2: Accede a la Configuración de Secretos

1. Click en **⚙️ Settings** (en la barra superior del repositorio)
2. En el menú lateral izquierdo, busca la sección **Security**
3. Click en **Secrets and variables**
4. Click en **Actions**

### PASO 3: Agregar Cada Secreto

Deberás hacer esto **6 veces** (uno para cada secreto):

#### 3.1 Click en el botón verde **"New repository secret"**

#### 3.2 Configura cada secreto según esta tabla:

| # | Name | Value | Dónde Obtenerlo |
|---|------|-------|----------------|
| 1️⃣ | `LAUDUS_API_URL` | `https://api.laudus.cl` | URL de la API de Laudus |
| 2️⃣ | `LAUDUS_USERNAME` | `API` | Usuario de la API (normalmente "API") |
| 3️⃣ | `LAUDUS_PASSWORD` | `[tu-password]` | Contraseña de acceso a Laudus |
| 4️⃣ | `LAUDUS_COMPANY_VAT` | `[tu-rut-sin-puntos]` | RUT de la empresa (ej: 775488344) |
| 5️⃣ | `MONGODB_URI` | `mongodb+srv://...` | Connection string de MongoDB Atlas |
| 6️⃣ | `MONGODB_DATABASE` | `laudus_data` | Nombre de tu base de datos |

#### 3.3 Para cada secreto:
- Escribe el **Name** exactamente como se muestra (case-sensitive)
- Pega el **Value** correspondiente
- Click en **"Add secret"**

---

## 🔍 Valores Específicos para Tu Proyecto

### 1️⃣ LAUDUS_API_URL
```
https://api.laudus.cl
```
✅ **Sin "/" al final**

### 2️⃣ LAUDUS_USERNAME
```
API
```
✅ **Tal como está en tu .env.example**

### 3️⃣ LAUDUS_PASSWORD
```
[Usa el valor real de tu archivo .env local]
```
⚠️ **NO uses "api123" si es solo un ejemplo**

### 4️⃣ LAUDUS_COMPANY_VAT
```
[Tu RUT sin guiones ni puntos]
```
📝 Si en tu .env tienes `77548834-4`, usa: `775488344`

### 5️⃣ MONGODB_URI
```
mongodb+srv://[usuario]:[password]@[cluster].mongodb.net/?retryWrites=true&w=majority
```
📍 **Obtenerlo desde MongoDB Atlas:**
1. Ve a tu cluster en MongoDB Atlas
2. Click en "Connect"
3. Click en "Connect your application"
4. Copia el connection string
5. Reemplaza `<password>` con tu password real

### 6️⃣ MONGODB_DATABASE
```
laudus_data
```
✅ **Nombre de tu base de datos**

---

## ✅ Verificar que los Secretos Están Configurados

Después de agregar todos los secretos:

1. Ve a: **Settings** → **Secrets and variables** → **Actions**
2. Deberías ver una lista de 6 secretos:
   ```
   LAUDUS_API_URL
   LAUDUS_COMPANY_VAT
   LAUDUS_PASSWORD
   LAUDUS_USERNAME
   MONGODB_DATABASE
   MONGODB_URI
   ```

3. ✅ **Los valores NO se mostrarán** (por seguridad)
4. ✅ Verás la fecha de creación/actualización

---

## 🧪 Probar el Workflow

Una vez configurados los secretos:

### Opción A: Esperar a la ejecución automática
- El workflow se ejecuta diariamente a las **11:30 PM** hora Chile

### Opción B: Ejecutar manualmente (Recomendado)
1. Ve a la pestaña **Actions**
2. Selecciona **"Laudus Balance Sheet Daily Automation"**
3. Click en **"Run workflow"** (botón a la derecha)
4. Click en el botón verde **"Run workflow"**
5. Espera unos segundos y actualiza la página
6. Click en el workflow que se está ejecutando para ver los logs

---

## 🎯 Qué Esperar en los Logs

### ✅ Si todo está bien configurado:
```
🔐 Authenticating with Laudus https://api.laudus.cl...
✅ Authentication successful
Token length: 500+ chars
🔌 Connecting to MongoDB Atlas...
✅ MongoDB connection successful
📅 Target date: 2025-10-22
📊 Fetching totals...
✅ totals: XXX records retrieved
✅ Saved to MongoDB: balance_totals (XXX records)
...
✅ ALL ENDPOINTS COMPLETED SUCCESSFULLY!
```

### ❌ Si algo está mal:
```
❌ Authentication failed: 401 Client Error: Unauthorized
```
→ Verifica `LAUDUS_PASSWORD` y `LAUDUS_COMPANY_VAT`

```
❌ MongoDB connection failed
```
→ Verifica `MONGODB_URI` y las IPs permitidas en MongoDB Atlas

---

## 🔧 MongoDB Atlas: Configurar IPs Permitidas

Para que GitHub Actions pueda conectarse a MongoDB:

1. Ve a MongoDB Atlas
2. Click en **Network Access** (menú lateral)
3. Click en **"+ ADD IP ADDRESS"**
4. Selecciona **"ALLOW ACCESS FROM ANYWHERE"** (0.0.0.0/0)
5. Click en **"Confirm"**

⚠️ **Nota de seguridad**: Esto permite conexiones desde cualquier IP. Alternativamente, puedes configurar las IPs específicas de GitHub Actions.

---

## 📊 Los Warnings en VS Code

### Antes de configurar secretos:
```yaml
LAUDUS_API_URL: ${{ secrets.LAUDUS_API_URL }}  ⚠️ Warning
```

### Después de configurar secretos:
```yaml
LAUDUS_API_URL: ${{ secrets.LAUDUS_API_URL }}  ✅ Sin warning
```

**Los warnings desaparecen cuando:**
- Los secretos están configurados en GitHub
- VS Code puede verificar su existencia
- Puede tomar unos minutos después de configurarlos

---

## 🆘 ¿Necesitas Ayuda?

Si después de seguir esta guía sigues teniendo problemas:

1. ✅ Verifica que los 6 secretos estén en GitHub
2. ✅ Verifica que los nombres sean exactos (case-sensitive)
3. ✅ Revisa los logs del workflow para errores específicos
4. ✅ Verifica las IPs permitidas en MongoDB Atlas
5. ✅ Asegúrate de que las credenciales de Laudus sean correctas

---

**Última actualización**: 23 de Octubre, 2025
