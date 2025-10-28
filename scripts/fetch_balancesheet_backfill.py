#!/usr/bin/env python3
"""
Laudus Balance Sheet Backfill Script
Para Render.com - Procesa datos históricos automáticamente (Enero-Septiembre 2025)

Este script procesa un mes completo por ejecución.
Se ejecuta diariamente hasta completar todos los meses pendientes.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from calendar import monthrange

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
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
    'timeout': 900,  # 15 minutes
    'retry_delay': 300,  # 5 minutes
    'max_retries': 3,
    'delay_between_dates': 60,  # 1 minute between dates
    'delay_between_endpoints': 120,  # 2 minutes between endpoints
}

# Backfill configuration
BACKFILL_CONFIG = {
    'start_date': os.getenv('BACKFILL_START_DATE', '2025-01-01'),
    'end_date': os.getenv('BACKFILL_END_DATE', '2025-09-30'),
    'mode': os.getenv('BACKFILL_MODE', 'monthly'),  # 'monthly' or 'daily'
    'max_dates_per_run': int(os.getenv('MAX_DATES_PER_RUN', '31')),
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
                'loadSource': 'backfill-render',
                'data': data
            }
            
            # Upsert
            result = collection.replace_one(
                {'_id': document['_id']},
                document,
                upsert=True
            )
            
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


def get_month_dates(year_month: str) -> List[str]:
    """Get all dates in a given month (YYYY-MM format)"""
    year, month = map(int, year_month.split('-'))
    num_days = monthrange(year, month)[1]
    
    dates = []
    for day in range(1, num_days + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        dates.append(date_str)
    
    return dates


def get_missing_months(mongo_client: MongoDBClient, start_date: str, end_date: str) -> List[str]:
    """
    Get list of months that are incomplete (have missing dates)
    Returns list like: ['2025-01', '2025-02', ...]
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    months = []
    current = start.replace(day=1)
    
    while current <= end:
        year_month = current.strftime('%Y-%m')
        months.append(year_month)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Check which months have missing dates
    missing_months = []
    
    for year_month in months:
        month_dates = get_month_dates(year_month)
        
        # Filter dates within the backfill range
        valid_dates = [d for d in month_dates 
                      if start_date <= d <= end_date]
        
        # Check if any date is missing
        has_missing = False
        for date_str in valid_dates:
            all_exist, _ = mongo_client.check_date_exists(date_str)
            if not all_exist:
                has_missing = True
                break
        
        if has_missing:
            missing_months.append(year_month)
    
    return missing_months


def process_date(api_client: LaudusAPIClient, mongo_client: MongoDBClient, 
                 date_str: str) -> bool:
    """Process all endpoints for a single date"""
    logger.info(f"📅 Procesando fecha: {date_str}")
    
    # Check if already exists
    all_exist, missing_endpoints = mongo_client.check_date_exists(date_str)
    
    if all_exist:
        logger.info(f"   ⏭️  Ya existe en MongoDB, omitiendo")
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
                    logger.info(f"   ✅ {endpoint['name']} guardado ({len(data)} registros)")
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
    logger.info("  LAUDUS BACKFILL - RENDER.COM")
    logger.info("  Procesamiento Histórico: Enero-Septiembre 2025")
    logger.info("=" * 70)
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Rango: {BACKFILL_CONFIG['start_date']} a {BACKFILL_CONFIG['end_date']}")
    logger.info(f"Modo: {BACKFILL_CONFIG['mode']}")
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
    
    # Get missing months
    logger.info("🔍 Buscando meses pendientes...")
    missing_months = get_missing_months(
        mongo_client,
        BACKFILL_CONFIG['start_date'],
        BACKFILL_CONFIG['end_date']
    )
    
    if not missing_months:
        logger.info("")
        logger.info("=" * 70)
        logger.info("  🎉 ¡BACKFILL COMPLETO!")
        logger.info("=" * 70)
        logger.info("✅ Todos los meses están completos en MongoDB")
        logger.info("📌 Puedes PAUSAR o ELIMINAR este Cron Job en Render.com")
        logger.info("=" * 70)
        mongo_client.close()
        sys.exit(0)
    
    logger.info(f"📊 Meses pendientes: {len(missing_months)}")
    logger.info(f"   {', '.join(missing_months)}")
    logger.info("")
    
    # Process first pending month
    target_month = missing_months[0]
    logger.info("=" * 70)
    logger.info(f"  📅 PROCESANDO MES: {target_month}")
    logger.info("=" * 70)
    logger.info("")
    
    # Get all dates in the month
    month_dates = get_month_dates(target_month)
    
    # Filter dates within backfill range
    start_date = BACKFILL_CONFIG['start_date']
    end_date = BACKFILL_CONFIG['end_date']
    valid_dates = [d for d in month_dates if start_date <= d <= end_date]
    
    logger.info(f"📆 Fechas a procesar: {len(valid_dates)}")
    logger.info(f"   Desde: {valid_dates[0]}")
    logger.info(f"   Hasta: {valid_dates[-1]}")
    logger.info("")
    
    # Track progress
    processed = 0
    successful = 0
    failed = 0
    
    # Process each date
    for i, date_str in enumerate(valid_dates, 1):
        logger.info(f"--- Fecha {i}/{len(valid_dates)} ---")
        
        # Renew token every 10 dates
        if i > 1 and i % 10 == 1:
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
        if i < len(valid_dates):
            logger.info(f"⏳ Esperando {CONFIG['delay_between_dates']}s antes de la siguiente fecha...")
            time.sleep(CONFIG['delay_between_dates'])
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  RESUMEN - MES {target_month}")
    logger.info("=" * 70)
    logger.info(f"✅ Procesadas exitosamente: {successful}/{processed} fechas")
    if failed > 0:
        logger.info(f"❌ Fallidas: {failed}/{processed} fechas")
    logger.info("")
    
    remaining_months = len(missing_months) - 1
    if remaining_months > 0:
        logger.info(f"📊 Meses restantes: {remaining_months}")
        logger.info(f"   {', '.join(missing_months[1:])}")
        logger.info("")
        logger.info("🔄 El próximo mes se procesará en la siguiente ejecución diaria")
    else:
        logger.info("🎉 ¡Este era el último mes pendiente!")
        logger.info("📌 En la próxima ejecución se confirmará que todo está completo")
    
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
