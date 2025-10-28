#!/usr/bin/env python3
"""
Laudus Balance Sheet Daily Backfill Script
Para GitHub Actions - Procesa lote de fechas faltantes automáticamente

Configuración desde variables de entorno:
- BACKFILL_START_DATE: Fecha inicio (YYYY-MM-DD)
- BACKFILL_END_DATE: Fecha fin (YYYY-MM-DD)
- MAX_DATES_PER_RUN: Máximo de fechas a procesar por ejecución
- TIMEOUT_SECONDS: Timeout por endpoint (default: 1800s = 30min)
- DELAY_BETWEEN_ENDPOINTS: Pausa entre endpoints (default: 300s = 5min)
- DELAY_BETWEEN_DATES: Pausa entre fechas (default: 120s = 2min)
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-backfill-auto.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
CONFIG = {
    'api_url': os.getenv('LAUDUS_API_URL', 'https://api.laudus.cl'),
    'username': os.getenv('LAUDUS_USERNAME', 'API'),
    'password': os.getenv('LAUDUS_PASSWORD'),
    'company_vat': os.getenv('LAUDUS_COMPANY_VAT'),
    'mongodb_uri': os.getenv('MONGODB_URI'),
    'mongodb_database': os.getenv('MONGODB_DATABASE', 'laudus_data'),
    'timeout': int(os.getenv('TIMEOUT_SECONDS', '1800')),  # 30 minutes default
    'retry_delay': 300,  # 5 minutes between retries
    'max_retries': 3,
    'delay_between_endpoints': int(os.getenv('DELAY_BETWEEN_ENDPOINTS', '300')),  # 5 min
    'delay_between_dates': int(os.getenv('DELAY_BETWEEN_DATES', '120')),  # 2 min
}

# Backfill configuration
BACKFILL_CONFIG = {
    'start_date': os.getenv('BACKFILL_START_DATE', '2025-07-01'),
    'end_date': os.getenv('BACKFILL_END_DATE', '2025-09-30'),
    'max_dates_per_run': int(os.getenv('MAX_DATES_PER_RUN', '7')),
}

# Endpoints configuration
ENDPOINTS = [
    {
        'name': 'totals',
        'path': '/accounting/balanceSheet/totals',
        'collection': 'balance_totals'
    },
    {
        'name': 'standard',
        'path': '/accounting/balanceSheet/standard',
        'collection': 'balance_standard'
    },
    {
        'name': '8Columns',
        'path': '/accounting/balanceSheet/8Columns',
        'collection': 'balance_8columns'
    }
]


class LaudusAPIClient:
    """Client for Laudus API interactions"""
    
    def __init__(self):
        self.base_url = CONFIG['api_url']
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def authenticate(self) -> bool:
        """Get JWT token from Laudus API"""
        try:
            logger.info(f"🔐 Autenticando con Laudus API...")
            
            payload = {
                'userName': CONFIG['username'],
                'password': CONFIG['password'],
                'companyVATId': CONFIG['company_vat']
            }
            
            response = self.session.post(
                f"{self.base_url}/security/login",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            # Extract token
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
            
            # Update session headers
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            logger.info("✅ Autenticación exitosa")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error de autenticación: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status: {e.response.status_code}")
                logger.error(f"Response: {e.response.text[:200]}")
            return False
    
    def fetch_balance_sheet(self, endpoint: Dict, date_to: str) -> Optional[List[Dict]]:
        """Fetch balance sheet data from specified endpoint"""
        try:
            params = {
                'dateTo': date_to,
                'showAccountsWithZeroBalance': 'true',
                'showOnlyAccountsWithActivity': 'false'
            }
            
            url = f"{self.base_url}{endpoint['path']}"
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            record_count = len(data)
            
            logger.info(f"   ✅ {endpoint['name']}: {record_count} registros obtenidos")
            return data
            
        except requests.Timeout:
            logger.error(f"   ⏱️ Timeout en {endpoint['name']} (>{CONFIG['timeout']}s)")
            return None
        except requests.HTTPError as e:
            logger.error(f"   ❌ HTTP Error en {endpoint['name']}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"      Status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error en {endpoint['name']}: {e}")
            return None


class MongoDBClient:
    """Client for MongoDB Atlas interactions"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to MongoDB Atlas"""
        try:
            logger.info("🔌 Conectando a MongoDB Atlas...")
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            
            # Test connection
            self.client.admin.command('ping')
            
            self.connected = True
            logger.info("✅ Conexión a MongoDB exitosa")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error de conexión a MongoDB: {e}")
            return False
    
    def check_date_exists(self, date_str: str) -> Tuple[bool, List[str]]:
        """
        Check if all endpoints for a given date exist in MongoDB
        Returns: (all_exist, missing_endpoints)
        """
        try:
            missing = []
            
            for endpoint in ENDPOINTS:
                collection = self.db[endpoint['collection']]
                doc_id = f"{date_str}-{endpoint['name']}"
                
                exists = collection.find_one({'_id': doc_id}) is not None
                
                if not exists:
                    missing.append(endpoint['name'])
            
            all_exist = len(missing) == 0
            return all_exist, missing
            
        except Exception as e:
            logger.error(f"❌ Error verificando fecha {date_str}: {e}")
            return False, [ep['name'] for ep in ENDPOINTS]
    
    def save_data(self, collection_name: str, data: List[Dict], endpoint_name: str, date_str: str) -> bool:
        """Save balance sheet data to MongoDB"""
        try:
            if not self.connected:
                raise Exception("No conectado a MongoDB")
            
            collection = self.db[collection_name]
            
            document = {
                '_id': f"{date_str}-{endpoint_name}",
                'date': date_str,
                'endpointType': endpoint_name,
                'recordCount': len(data),
                'insertedAt': datetime.utcnow(),
                'loadSource': 'backfill-auto-github',
                'data': data
            }
            
            # Upsert
            result = collection.replace_one(
                {'_id': document['_id']},
                document,
                upsert=True
            )
            
            logger.info(f"   ✅ {endpoint_name} guardado ({len(data)} registros)")
            return True
                
        except PyMongoError as e:
            logger.error(f"   ❌ Error guardando en MongoDB: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 Conexión a MongoDB cerrada")


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """Generate list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates


def get_missing_dates(mongo_client: MongoDBClient, start_date: str, end_date: str) -> List[str]:
    """Get list of dates that are incomplete (have missing endpoints)"""
    all_dates = generate_date_range(start_date, end_date)
    missing_dates = []
    
    for date_str in all_dates:
        all_exist, _ = mongo_client.check_date_exists(date_str)
        if not all_exist:
            missing_dates.append(date_str)
    
    return missing_dates


def process_date(api_client: LaudusAPIClient, mongo_client: MongoDBClient, 
                 date_str: str) -> bool:
    """Process all endpoints for a single date"""
    logger.info(f"📅 Procesando fecha: {date_str}")
    
    # Check if already exists
    all_exist, missing_endpoints = mongo_client.check_date_exists(date_str)
    
    if all_exist:
        logger.info(f"   ⏭️  Ya existe completa en MongoDB, omitiendo")
        return True
    
    if missing_endpoints:
        logger.info(f"   🔄 Endpoints faltantes: {', '.join(missing_endpoints)}")
    
    # Process each endpoint
    success_count = 0
    
    for endpoint in ENDPOINTS:
        # Skip if already exists
        if endpoint['name'] not in missing_endpoints:
            logger.info(f"   ⏭️  {endpoint['name']} ya existe, omitiendo")
            success_count += 1
            continue
        
        # Retry logic
        for attempt in range(1, CONFIG['max_retries'] + 1):
            logger.info(f"   🔄 {endpoint['name']} (intento {attempt}/{CONFIG['max_retries']})")
            
            # Fetch data
            data = api_client.fetch_balance_sheet(endpoint, date_str)
            
            if data is not None:
                # Save to MongoDB
                success = mongo_client.save_data(
                    endpoint['collection'],
                    data,
                    endpoint['name'],
                    date_str
                )
                
                if success:
                    success_count += 1
                    break
                else:
                    logger.error(f"   ❌ Error guardando {endpoint['name']}")
            else:
                logger.error(f"   ❌ Error obteniendo {endpoint['name']}")
            
            # Wait before retry
            if attempt < CONFIG['max_retries']:
                logger.info(f"   ⏳ Esperando {CONFIG['retry_delay']}s antes de reintentar...")
                time.sleep(CONFIG['retry_delay'])
        
        # Wait between endpoints
        if endpoint != ENDPOINTS[-1]:  # Not the last endpoint
            logger.info(f"   ⏳ Esperando {CONFIG['delay_between_endpoints']}s...")
            time.sleep(CONFIG['delay_between_endpoints'])
    
    # All endpoints processed successfully?
    all_success = success_count == len(ENDPOINTS)
    
    if all_success:
        logger.info(f"✅ Fecha {date_str} completada ({success_count}/{len(ENDPOINTS)} endpoints)")
    else:
        logger.warning(f"⚠️  Fecha {date_str} parcialmente completada ({success_count}/{len(ENDPOINTS)} endpoints)")
    
    return all_success


def main():
    """Main execution function"""
    logger.info("=" * 70)
    logger.info("  LAUDUS BACKFILL AUTO - GITHUB ACTIONS")
    logger.info("  Procesamiento por lotes: Jul-Sep 2025")
    logger.info("=" * 70)
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Rango: {BACKFILL_CONFIG['start_date']} a {BACKFILL_CONFIG['end_date']}")
    logger.info(f"Máximo por ejecución: {BACKFILL_CONFIG['max_dates_per_run']} fechas")
    logger.info(f"Timeout por endpoint: {CONFIG['timeout']}s ({CONFIG['timeout']//60} min)")
    logger.info("")
    
    # Validate configuration
    if not all([CONFIG['password'], CONFIG['company_vat'], CONFIG['mongodb_uri']]):
        logger.error("❌ Faltan variables de entorno requeridas")
        logger.error("Requeridas: LAUDUS_PASSWORD, LAUDUS_COMPANY_VAT, MONGODB_URI")
        sys.exit(1)
    
    # Initialize clients
    api_client = LaudusAPIClient()
    mongo_client = MongoDBClient()
    
    # Authenticate
    if not api_client.authenticate():
        logger.error("❌ Error al autenticar con Laudus API")
        sys.exit(1)
    
    # Connect to MongoDB
    if not mongo_client.connect():
        logger.error("❌ Error al conectar con MongoDB")
        sys.exit(1)
    
    # Get missing dates
    logger.info("🔍 Buscando fechas pendientes...")
    missing_dates = get_missing_dates(
        mongo_client,
        BACKFILL_CONFIG['start_date'],
        BACKFILL_CONFIG['end_date']
    )
    
    if not missing_dates:
        logger.info("")
        logger.info("=" * 70)
        logger.info("  🎉 ¡BACKFILL COMPLETO!")
        logger.info("=" * 70)
        logger.info("✅ Todas las fechas están completas en MongoDB")
        logger.info(f"   Rango: {BACKFILL_CONFIG['start_date']} a {BACKFILL_CONFIG['end_date']}")
        logger.info("📌 Este workflow puede ser DESACTIVADO")
        logger.info("=" * 70)
        mongo_client.close()
        sys.exit(0)
    
    total_pending = len(missing_dates)
    logger.info(f"📊 Fechas pendientes: {total_pending}")
    logger.info(f"   Primera: {missing_dates[0]}")
    logger.info(f"   Última: {missing_dates[-1]}")
    
    # Process batch (limited by max_dates_per_run)
    batch_size = min(BACKFILL_CONFIG['max_dates_per_run'], total_pending)
    dates_to_process = missing_dates[:batch_size]
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  📅 PROCESANDO LOTE: {len(dates_to_process)} FECHAS")
    logger.info("=" * 70)
    logger.info(f"Desde: {dates_to_process[0]}")
    logger.info(f"Hasta: {dates_to_process[-1]}")
    logger.info("")
    
    # Track progress
    processed = 0
    successful = 0
    failed = 0
    
    # Process each date
    for i, date_str in enumerate(dates_to_process, 1):
        logger.info(f"--- Fecha {i}/{len(dates_to_process)} ---")
        
        # Renew token every 5 dates
        if i > 1 and i % 5 == 1:
            logger.info("🔄 Renovando token de autenticación...")
            if not api_client.authenticate():
                logger.error("❌ Error al renovar token")
                continue
        
        # Process date
        success = process_date(api_client, mongo_client, date_str)
        
        processed += 1
        if success:
            successful += 1
        else:
            failed += 1
        
        logger.info("")
        
        # Wait before next date (except last one)
        if i < len(dates_to_process):
            logger.info(f"⏳ Esperando {CONFIG['delay_between_dates']}s antes de la siguiente fecha...")
            time.sleep(CONFIG['delay_between_dates'])
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  RESUMEN DE LOTE")
    logger.info("=" * 70)
    logger.info(f"✅ Procesadas exitosamente: {successful}/{processed} fechas")
    if failed > 0:
        logger.info(f"❌ Fallidas o parciales: {failed}/{processed} fechas")
    
    remaining = total_pending - processed
    if remaining > 0:
        logger.info("")
        logger.info(f"📊 Fechas restantes totales: {remaining}")
        logger.info(f"   Próxima fecha: {missing_dates[processed]}")
        logger.info("")
        logger.info("🔄 La próxima ejecución continuará automáticamente mañana")
    else:
        logger.info("")
        logger.info("🎉 ¡Última fecha pendiente procesada!")
        logger.info("📌 Próxima ejecución verificará si hay nuevos pendientes")
    
    logger.info("")
    logger.info(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    # Cleanup
    mongo_client.close()
    
    # Exit with success (even if some dates failed, we made progress)
    sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Proceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"❌ Error inesperado: {e}")
        sys.exit(1)
