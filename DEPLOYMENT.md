# 🚀 Guía Rápida de Deployment

## ✅ Estado Actual del Proyecto

El proyecto está **100% listo** para usar y deploy, pero actualmente **sin permisos** de la API de Laudus.

---

## 📋 Checklist Pre-Deployment

### 1. ✅ Estructura Creada
- [x] Código organizado en módulos
- [x] Balance Sheet (3 formatos)
- [x] Módulo de Ventas
- [x] Funciones Serverless para Vercel
- [x] Ejemplos de uso
- [x] Configuración

### 2. ⏳ Pendientes (Requieren permisos)
- [ ] Solicitar permisos al administrador de Laudus
- [ ] Probar endpoints con permisos activos
- [ ] Verificar respuestas de la API
- [ ] Deploy a Vercel

---

## 🔐 PASO 1: Solicitar Permisos

### Mensaje para el Administrador:

```
Asunto: Solicitud de Permisos API Laudus - Balance Sheet

Hola,

Necesito permisos para el usuario API para acceder a los siguientes endpoints:

Usuario: API
RUT Empresa: 77548834-4

Endpoints requeridos:
✅ GET /accounting/balanceSheet/totals
✅ GET /accounting/balanceSheet/standard
✅ GET /accounting/balanceSheet/8Columns

Nivel de acceso: Solo Lectura (Read Only)
Propósito: Extracción de datos para visualizaciones

Actualmente recibo error "401 Unauthorized" en estos endpoints.

Gracias,
[Tu Nombre]
```

---

## 🧪 PASO 2: Probar Localmente (Una vez con permisos)

### Opción A: Ejecutar Ejemplos

```bash
# Instalar dependencias (si aún no lo hiciste)
npm install

# Probar Balance Sheet - Totales
npm run dev

# Probar Balance Sheet - Standard
npm run dev:balance-standard

# Probar Balance Sheet - 8 Columnas
npm run dev:balance-8columns
```

### Opción B: Usar el Código Directamente

```javascript
import { LaudusAPI } from './src/index.js';

const laudus = new LaudusAPI();
await laudus.login();

const balance = await laudus.balanceSheet.getTotals({
    dateTo: '2025-10-19'
});

console.log(balance);
```

---

## 🌐 PASO 3: Deploy a Vercel

### Opción A: Deploy desde CLI

```bash
# 1. Instalar Vercel CLI (si no lo tienes)
npm i -g vercel

# 2. Login en Vercel
vercel login

# 3. Deploy en preview (primera vez)
vercel

# 4. Deploy en producción
vercel --prod
```

### Opción B: Deploy desde GitHub

1. **Sube tu código a GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Laudus API Integration"
   git remote add origin https://github.com/tu-usuario/laudus-api.git
   git push -u origin main
   ```

2. **Conecta con Vercel**
   - Ve a [vercel.com](https://vercel.com)
   - Click en "Import Project"
   - Selecciona tu repositorio de GitHub
   - Vercel detectará automáticamente la configuración

3. **Configura Variables de Entorno**
   
   En el dashboard de Vercel → Settings → Environment Variables:
   
   ```
   LAUDUS_API_URL = https://api.laudus.cl
   LAUDUS_USERNAME = API
   LAUDUS_PASSWORD = api123
   LAUDUS_COMPANY_VAT_ID = 77548834-4
   ```

4. **Deploy**
   - Vercel deployará automáticamente
   - Obtendrás una URL como: `https://laudus-api-tu-usuario.vercel.app`

---

## 📡 PASO 4: Probar Endpoints en Producción

Una vez deployado, tus endpoints estarán en:

```
https://tu-proyecto.vercel.app/api/accounting/balance-sheet/totals?dateTo=2025-10-19

https://tu-proyecto.vercel.app/api/accounting/balance-sheet/standard?dateTo=2025-10-19

https://tu-proyecto.vercel.app/api/accounting/balance-sheet/8-columns?dateTo=2025-10-19
```

### Probar con cURL:

```bash
curl "https://tu-proyecto.vercel.app/api/accounting/balance-sheet/totals?dateTo=2025-10-19"
```

### Probar desde Browser:

Simplemente abre la URL en tu navegador.

### Probar desde Postman:

```
GET https://tu-proyecto.vercel.app/api/accounting/balance-sheet/totals

Params:
- dateTo: 2025-10-19
- showAccountsWithZeroBalance: false
- showOnlyAccountsWithActivity: true
```

---

## 🎨 PASO 5: Integrar con Frontend

### Ejemplo React/Next.js:

```jsx
import { useState, useEffect } from 'react';

function BalanceDashboard() {
    const [balance, setBalance] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('https://tu-proyecto.vercel.app/api/accounting/balance-sheet/totals?dateTo=2025-10-19')
            .then(res => res.json())
            .then(result => {
                setBalance(result.data);
                setLoading(false);
            })
            .catch(err => console.error(err));
    }, []);

    if (loading) return <div>Cargando...</div>;

    return (
        <div>
            <h1>Balance de Comprobación</h1>
            {balance.map(account => (
                <div key={account.accountNumber}>
                    <strong>{account.accountName}</strong>: 
                    ${account.debitBalance?.toLocaleString()}
                </div>
            ))}
        </div>
    );
}
```

### Ejemplo con Chart.js:

```javascript
// Obtener datos
const response = await fetch('https://tu-proyecto.vercel.app/api/accounting/balance-sheet/totals?dateTo=2025-10-19');
const { data } = await response.json();

// Formatear para gráfico
const chartData = {
    labels: data.map(item => item.accountName),
    datasets: [{
        label: 'Saldo Débito',
        data: data.map(item => item.debitBalance),
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1
    }]
};

// Renderizar con Chart.js
new Chart(ctx, {
    type: 'bar',
    data: chartData
});
```

---

## 🔍 Troubleshooting Post-Deployment

### Error: 500 Internal Server Error

**Causas posibles:**
- Variables de entorno no configuradas en Vercel
- Credenciales incorrectas

**Solución:**
- Verifica variables en Vercel Dashboard
- Revisa logs en Vercel → Deployments → Tu deploy → Function Logs

### Error: 403 Forbidden

**Causa:** Aún no tienes permisos en Laudus

**Solución:** Espera a que el administrador active los permisos

### Error: CORS

**Causa:** Problema de CORS en navegador

**Solución:** Ya está configurado. Si persiste, verifica que la request viene desde un dominio permitido.

---

## 📊 Monitoreo

### Logs en Vercel

1. Ve a tu proyecto en Vercel
2. Click en "Deployments"
3. Selecciona el deployment actual
4. Click en "View Function Logs"
5. Verás todos los console.log de tus funciones

### Analytics

Vercel proporciona analytics automáticos:
- Número de requests
- Tiempo de respuesta
- Errores
- Regiones de acceso

---

## 🎯 Próximos Pasos Sugeridos

Una vez que todo funcione:

1. **Caché de Tokens**
   - Implementar Redis o Vercel KV para cachear tokens
   - Evitar hacer login en cada request

2. **Rate Limiting**
   - Implementar límites de requests
   - Proteger contra abuso

3. **Webhooks**
   - Si Laudus lo soporta, configurar webhooks
   - Recibir actualizaciones en tiempo real

4. **Más Endpoints**
   - Plan de Cuentas
   - Centros de Costo
   - Otros módulos de Laudus

5. **Dashboard**
   - Crear un dashboard web
   - Visualizaciones interactivas
   - Exportar a PDF/Excel

---

## 📞 Contacto

Si tienes problemas:

1. Revisa el README.md principal
2. Consulta los ejemplos en `/examples`
3. Revisa logs en Vercel
4. Contacta al administrador de Laudus para permisos

---

**¡Todo está listo! Solo falta que el administrador active los permisos.** 🚀
