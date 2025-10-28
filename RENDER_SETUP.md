# 🚀 Configuración de Render.com para Backfill Histórico

Este documento explica cómo configurar Render.com para ejecutar automáticamente el backfill de datos históricos de Laudus (Enero-Septiembre 2025).

## 📋 Tabla de Contenidos

1. [Crear Cuenta en Render](#1-crear-cuenta-en-render)
2. [Conectar Repositorio](#2-conectar-repositorio)
3. [Crear Cron Job](#3-crear-cron-job)
4. [Configurar Variables de Entorno](#4-configurar-variables-de-entorno)
5. [Verificar y Activar](#5-verificar-y-activar)
6. [Monitorear Ejecuciones](#6-monitorear-ejecuciones)
7. [Pausar/Eliminar después](#7-pausareliminar-después)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Crear Cuenta en Render

### Opción A: Con GitHub (Recomendado)

1. Ve a: https://render.com
2. Click en **"Get Started"** o **"Sign Up"**
3. Selecciona **"Sign up with GitHub"**
4. Autoriza a Render para acceder a tus repositorios
5. ✅ Listo

### Opción B: Con Email

1. Ve a: https://render.com
2. Click en **"Get Started"**
3. Ingresa tu email y contraseña
4. Verifica tu email
5. Luego conecta tu cuenta de GitHub (Settings → Account → Connected Accounts)

**💳 ¿Se requiere tarjeta de crédito?**
- ❌ NO, el plan Free no requiere tarjeta
- ✅ Todo es completamente gratis

---

## 2. Conectar Repositorio

1. En el Dashboard de Render, click en **"New +"** (esquina superior derecha)
2. Selecciona **"Cron Job"**
3. Click en **"Connect a repository"**
4. Busca y selecciona: **`victor-hernandez-kirovich/laudus-api`**
5. Click en **"Connect"**

**Si el repositorio no aparece:**
- Click en **"Configure account"** (link azul)
- Esto te lleva a GitHub
- Selecciona los repositorios que quieres que Render pueda ver
- Marca: `laudus-api`
- Guarda cambios
- Regresa a Render y refresca la página

---

## 3. Crear Cron Job

### Paso 3.1: Información Básica

Después de conectar el repo, verás un formulario:

1. **Name**: `laudus-backfill-ene-sep` (o el nombre que prefieras)
2. **Region**: `Oregon (US West)` (recomendado, más cercano a Chile)
3. **Branch**: `main`
4. **Root Directory**: Dejar en blanco o poner `.`

### Paso 3.2: Build & Start Commands

Render debería detectar automáticamente el archivo `render.yaml`. Si no:

**Build Command:**
```bash
pip install --upgrade pip && pip install -r scripts/requirements.txt
```

**Start Command:**
```bash
python scripts/fetch_balancesheet_backfill.py
```

### Paso 3.3: Schedule

1. **Schedule**: `0 2 * * *`
   - Esto es **23:00 hora Chile** (UTC-3)
   - En UTC es 02:00
   
2. O usa la interfaz gráfica:
   - **Frequency**: Daily
   - **Hour**: 02 (UTC)
   - **Minute**: 00

### Paso 3.4: Plan

1. Selecciona: **Free** (debe estar preseleccionado)
2. **Environment**: Python 3

---

## 4. Configurar Variables de Entorno

Esta es la parte más importante. Necesitas configurar las variables secretas.

### Paso 4.1: Ir a Environment Variables

1. En la configuración del Cron Job, busca la sección **"Environment"**
2. Click en **"Add Environment Variable"** o edita las existentes

### Paso 4.2: Configurar Variables Secretas

Agrega las siguientes variables **SECRETAS** (click en el ícono del ojo para ocultarlas):

#### Variable 1: LAUDUS_PASSWORD
```
Key: LAUDUS_PASSWORD
Value: [tu_password_de_laudus]
🔒 Marca como "Secret"
```

#### Variable 2: LAUDUS_COMPANY_VAT
```
Key: LAUDUS_COMPANY_VAT
Value: [tu_rut_empresa]
🔒 Marca como "Secret"
```

#### Variable 3: MONGODB_URI
```
Key: MONGODB_URI
Value: [tu_mongodb_connection_string]
🔒 Marca como "Secret"
Ejemplo: mongodb+srv://usuario:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### Paso 4.3: Variables Públicas (ya están en render.yaml)

Estas deberían aparecer automáticamente desde el `render.yaml`:

```
LAUDUS_API_URL = https://api.laudus.cl
LAUDUS_USERNAME = API
MONGODB_DATABASE = laudus_data
BACKFILL_START_DATE = 2025-01-01
BACKFILL_END_DATE = 2025-09-30
BACKFILL_MODE = monthly
MAX_DATES_PER_RUN = 31
PYTHONUNBUFFERED = 1
```

Si no aparecen, agrégalas manualmente.

---

## 5. Verificar y Activar

### Paso 5.1: Revisar Configuración

Antes de crear el Cron Job, verifica:

✅ Build Command: `pip install --upgrade pip && pip install -r scripts/requirements.txt`
✅ Start Command: `python scripts/fetch_balancesheet_backfill.py`
✅ Schedule: `0 2 * * *` (23:00 CLT)
✅ Plan: Free
✅ Variables secretas configuradas

### Paso 5.2: Crear Cron Job

1. Click en **"Create Cron Job"** (botón al final del formulario)
2. Render comenzará a configurar el servicio
3. Espera unos segundos...

### Paso 5.3: Primera Ejecución (Opcional)

Para probar que todo funciona SIN esperar al horario programado:

1. Ve al Dashboard del Cron Job
2. Click en **"Trigger Run"** (botón manual)
3. Se ejecutará inmediatamente
4. Ve a la pestaña **"Logs"** para ver el progreso en tiempo real

---

## 6. Monitorear Ejecuciones

### Ver Logs en Tiempo Real

1. En el Dashboard del Cron Job
2. Click en la pestaña **"Logs"**
3. Verás la salida del script en vivo

**Logs esperados:**

```
======================================================================
  LAUDUS BACKFILL - RENDER.COM
  Procesamiento Histórico: Enero-Septiembre 2025
======================================================================
Inicio: 2025-10-28 23:00:15
Rango: 2025-01-01 a 2025-09-30
Modo: monthly

🔐 Autenticando con Laudus API...
✅ Autenticación exitosa
🔌 Conectando a MongoDB Atlas...
✅ Conexión a MongoDB exitosa

🔍 Buscando meses pendientes...
📊 Meses pendientes: 9
   2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09

======================================================================
  📅 PROCESANDO MES: 2025-01
======================================================================

📆 Fechas a procesar: 31
   Desde: 2025-01-01
   Hasta: 2025-01-31

--- Fecha 1/31 ---
📅 Procesando fecha: 2025-01-01
   🔄 totals (intento 1/3)
   ✅ totals: 1247 registros obtenidos
   ✅ totals guardado (1247 registros)
   ⏳ Esperando 120s...
   🔄 standard (intento 1/3)
   ✅ standard: 856 registros obtenidos
   ✅ standard guardado (856 registros)
   ...
```

### Ver Historial de Ejecuciones

1. En el Dashboard del Cron Job
2. Pestaña **"Events"**
3. Verás todas las ejecuciones:
   - ✅ Verde: Exitosa
   - ❌ Rojo: Fallida
   - 🔵 Azul: En progreso

### Próximas Ejecuciones Programadas

En el Dashboard verás:
```
Next scheduled run: Oct 29, 2025 at 02:00 UTC (Oct 28, 23:00 CLT)
```

---

## 7. Pausar/Eliminar Después

### Cuando el Backfill esté completo (día 9-10)

Verás en los logs:
```
======================================================================
  🎉 ¡BACKFILL COMPLETO!
======================================================================
✅ Todos los meses están completos en MongoDB
📌 Puedes PAUSAR o ELIMINAR este Cron Job en Render.com
======================================================================
```

### Opción A: Pausar el Cron Job

1. Dashboard del Cron Job
2. Click en **"Settings"** (pestaña)
3. Busca **"Suspend Cron Job"**
4. Click en **"Suspend"**
5. El job queda pausado (no se ejecuta, pero puedes reactivarlo después)

### Opción B: Eliminar el Cron Job

1. Dashboard del Cron Job
2. Click en **"Settings"** (pestaña)
3. Scroll hasta el final
4. Click en **"Delete Cron Job"**
5. Confirma la eliminación
6. ✅ El job desaparece completamente

**💡 Recomendación:**
- **Pausar** si crees que podrías necesitarlo de nuevo
- **Eliminar** si estás seguro que no lo necesitarás más

---

## 8. Troubleshooting

### ❌ Error: "Authentication failed"

**Causa:** Credenciales incorrectas

**Solución:**
1. Ve a **Environment Variables**
2. Verifica que `LAUDUS_PASSWORD` y `LAUDUS_COMPANY_VAT` sean correctos
3. Edita las variables si es necesario
4. Guarda cambios
5. Trigger manual run para probar

---

### ❌ Error: "MongoDB connection failed"

**Causa:** URI de MongoDB incorrecto o red

**Solución:**
1. Verifica que `MONGODB_URI` esté correcto
2. Formato debe ser: `mongodb+srv://usuario:password@cluster.mongodb.net/...`
3. Verifica que tu cluster de MongoDB Atlas:
   - Esté activo
   - Permita conexiones desde **cualquier IP** (`0.0.0.0/0`) o específicamente desde IPs de Render
4. En MongoDB Atlas → Network Access → Add IP Address → Allow Access from Anywhere

---

### ⏱️ Error: "Timeout"

**Causa:** Endpoint de Laudus tarda mucho

**Solución:**
- El script tiene reintentos automáticos (3 intentos por endpoint)
- Espera a que termine la ejecución
- En la siguiente ejecución diaria, continuará desde donde quedó

---

### 🔄 El Cron Job no se ejecuta a la hora programada

**Causa:** Timezone confusión

**Solución:**
1. Verifica el schedule: `0 2 * * *` es **02:00 UTC** = **23:00 CLT** (horario verano Chile)
2. Si estás en horario invierno (UTC-4), ajusta a: `0 3 * * *`
3. Settings → Edit schedule

---

### 📊 ¿Cómo saber qué meses ya están completos?

**Opción 1:** Revisar los logs de la última ejecución

Busca la sección:
```
📊 Meses pendientes: 5
   2025-05, 2025-06, 2025-07, 2025-08, 2025-09
```

**Opción 2:** Consultar MongoDB directamente

Conéctate a MongoDB Atlas y verifica las colecciones:
- `balance_totals`
- `balance_standard`
- `balance_8columns`

Busca documentos con fechas entre `2025-01-01` y `2025-09-30`.

---

### 🚨 El script falla constantemente

**Pasos de diagnóstico:**

1. **Revisar logs completos:**
   - Ve a la pestaña "Logs"
   - Busca mensajes de error específicos

2. **Verificar variables de entorno:**
   - Todas las variables secretas están configuradas
   - No hay typos en los nombres de las variables

3. **Probar conexiones:**
   - MongoDB Atlas está activo y accesible
   - API de Laudus está disponible

4. **Contactar soporte:**
   - Si todo falla, puedes contactar soporte de Render (tienen chat)
   - O revisar el repositorio de GitHub para issues

---

## 📅 Timeline Esperado

```
Día 1 (28-Oct 23:00): Procesa Enero 2025   ✅
Día 2 (29-Oct 23:00): Procesa Febrero 2025 ✅
Día 3 (30-Oct 23:00): Procesa Marzo 2025   ✅
Día 4 (31-Oct 23:00): Procesa Abril 2025   ✅
Día 5 (01-Nov 23:00): Procesa Mayo 2025    ✅
Día 6 (02-Nov 23:00): Procesa Junio 2025   ✅
Día 7 (03-Nov 23:00): Procesa Julio 2025   ✅
Día 8 (04-Nov 23:00): Procesa Agosto 2025  ✅
Día 9 (05-Nov 23:00): Procesa Septiembre 2025 ✅
Día 10 (06-Nov 23:00): Confirma todo completo 🎉
```

**Total: 9-10 días para completar Enero-Septiembre 2025**

---

## ✅ Checklist Final

Antes de activar el Cron Job, verifica:

- [ ] Cuenta en Render.com creada
- [ ] Repositorio `laudus-api` conectado
- [ ] Cron Job creado con nombre claro
- [ ] Schedule configurado: `0 2 * * *`
- [ ] Variable `LAUDUS_PASSWORD` configurada (secreta)
- [ ] Variable `LAUDUS_COMPANY_VAT` configurada (secreta)
- [ ] Variable `MONGODB_URI` configurada (secreta)
- [ ] Variables públicas están correctas
- [ ] Primera ejecución manual probada (opcional)
- [ ] Logs muestran autenticación exitosa
- [ ] Logs muestran conexión a MongoDB exitosa

---

## 🎯 Resultado Final

Al completar esta configuración:

✅ Render ejecutará automáticamente el backfill diariamente a las 23:00 (Chile)
✅ Procesará un mes completo por día
✅ En 9 días tendrás todos los datos de Enero-Septiembre 2025
✅ El script se auto-detecta cuando termina
✅ Puedes pausar/eliminar el Cron Job después

---

## 📞 Soporte

- **Render Docs:** https://render.com/docs/cron-jobs
- **Render Community:** https://community.render.com
- **GitHub Issues:** [Crear issue en el repo]

---

**¡Buena suerte con el backfill!** 🚀
