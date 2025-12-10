#!/usr/bin/env python3
"""
Laudus Invoices Monthly Fetcher
For manual data loading with specific year and month
Endpoint: /reports/sales/invoices/byMonth
"""

import os
import sys
import json
import logging
import time
import calendar
from datetime import datetime, timezone
from typing import Dict, List, Optional
import argparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
    'timeout': 300,  # 5 minutes
    'retry_delay': 60,  # 1 minute between retries
    'max_retries': 10,  # Maximum retry attempts
}

# Endpoint configuration
ENDPOINT = {
    'name': 'InvoicesByMonth',
    'path': '/reports/sales/invoices/byMonth',
    'collection': 'invoices_by_month'
}


class LaudusAPIClient:
    """Client for Laudus API interactions"""
    
    def __init__(self):
        self.base_url = CONFIG['api_url']
        self.token: Optional[str] = None
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=2,
            backoff_factor=10,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def authenticate(self) -> bool:
        """Get JWT token from Laudus API"""
        try:
            logger.info(f"Autenticando con Laudus {CONFIG['api_url']}...")
            
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
            
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            logger.info("Autenticacion exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error de autenticacion: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:200]}")
            return False
    
    def fetch_invoices_monthly(self, date_from: str, date_to: str) -> Optional[List[Dict]]:
        """Fetch invoices by month data"""
        try:
            params = {
                'dateFrom': date_from,
                'dateTo': date_to
            }
            
            url = f"{self.base_url}{ENDPOINT['path']}"
            logger.debug(f"URL: {url}")
            logger.debug(f"Params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            record_count = len(data) if isinstance(data, list) else 1
            
            logger.info(f"{ENDPOINT['name']}: {record_count} registros obtenidos")
            return data if isinstance(data, list) else [data]
            
        except requests.Timeout:
            logger.error(f"Timeout obteniendo {ENDPOINT['name']} (>{CONFIG['timeout']}s)")
            return None
        except requests.HTTPError as e:
            logger.error(f"HTTP Error obteniendo {ENDPOINT['name']}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Status: {e.response.status_code}")
                logger.error(f"   Response: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo {ENDPOINT['name']}: {e}")
            return None


MONTH_NAMES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}


class MongoDBClient:
    """Client for MongoDB Atlas interactions"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to MongoDB Atlas"""
        try:
            logger.info("Conectando a MongoDB Atlas...")
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            
            self.client.admin.command('ping')
            
            self.connected = True
            logger.info("Conexion a MongoDB exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error de conexion a MongoDB: {e}")
            return False
    
    def save_data(self, collection_name: str, data: List[Dict], period: str, year: int, month: int) -> bool:
        """Save invoices data to MongoDB in the expected format"""
        try:
            if not self.connected:
                raise Exception("No conectado a MongoDB")
            
            collection = self.db[collection_name]
            
            # Get the first record from the data (should be only one for the month)
            if not data or len(data) == 0:
                logger.warning("No hay datos para guardar")
                return False
            
            raw_data = data[0] if len(data) == 1 else data
            invoice_data = data[0] if isinstance(data, list) and len(data) > 0 else data
            
            # Build document in the expected format (same as original GitHub Actions workflow)
            document = {
                'month': period,  # YYYY-MM format
                'year': year,
                'monthNumber': month,
                'monthName': MONTH_NAMES.get(month, ''),
                # Extract fields from invoice data
                'total': invoice_data.get('total', 0),
                'returns': invoice_data.get('returns', 0),
                'returnsPercentage': invoice_data.get('returnsPercentage', 0),
                'net': invoice_data.get('net', 0),
                'netChangeYoYPercentage': invoice_data.get('netChangeYoYPercentage', 0),
                'margin': invoice_data.get('margin', 0),
                'marginChangeYoYPercentage': invoice_data.get('marginChangeYoYPercentage', 0),
                'discounts': invoice_data.get('discounts', 0),
                'discountsPercentage': invoice_data.get('discountsPercentage', 0),
                'quantity': invoice_data.get('quantity', 0),
                # Metadata
                'rawData': raw_data,
                'insertedAt': datetime.now(timezone.utc),
                'loadSource': 'manual'
            }
            
            # Upsert by month field (replace if exists, insert if not)
            result = collection.replace_one(
                {'month': period},
                document,
                upsert=True
            )
            
            logger.info(f"Guardado en MongoDB: {collection_name} (periodo: {period})")
            logger.info(f"   Total: {document['total']:,.0f} | Net: {document['net']:,.0f} | Margin: {document['margin']:,.2f}")
            return True
                
        except PyMongoError as e:
            logger.error(f"Error guardando en MongoDB: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Conexion a MongoDB cerrada")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Fetch Laudus invoices by month')
    parser.add_argument('--year', required=True, type=int, help='Target year (e.g., 2024)')
    parser.add_argument('--month', required=True, type=int, help='Target month (1-12)')
    
    args = parser.parse_args()
    
    year = args.year
    month = args.month
    
    # Validate month
    if month < 1 or month > 12:
        logger.error("El mes debe estar entre 1 y 12")
        sys.exit(1)
    
    # Calculate date range for the month
    first_day = f"{year}-{month:02d}-01"
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = f"{year}-{month:02d}-{last_day_num:02d}"
    period = f"{year}-{month:02d}"
    
    logger.info("=" * 60)
    logger.info("  CARGA FACTURAS MENSUALES")
    logger.info("=" * 60)
    logger.info(f"Periodo: {period}")
    logger.info(f"Rango: {first_day} a {last_day}")
    logger.info(f"Endpoint: {ENDPOINT['name']}")
    logger.info("")
    
    # Validate configuration
    if not all([CONFIG['password'], CONFIG['company_vat'], CONFIG['mongodb_uri']]):
        logger.error("Faltan variables de entorno requeridas")
        logger.error("Requeridas: LAUDUS_PASSWORD, LAUDUS_COMPANY_VAT, MONGODB_URI")
        sys.exit(1)
    
    # Initialize clients
    api_client = LaudusAPIClient()
    mongo_client = MongoDBClient()
    
    # Authenticate
    if not api_client.authenticate():
        logger.error("Error al autenticar con Laudus API")
        sys.exit(1)
    
    # Connect to MongoDB
    if not mongo_client.connect():
        logger.error("Error al conectar con MongoDB")
        sys.exit(1)
    
    # Track completion status
    completed = False
    result = {'endpoint': ENDPOINT['name'], 'success': False, 'records': 0}
    attempt = 0
    max_attempts = CONFIG['max_retries']
    
    # Main retry loop
    while attempt < max_attempts and not completed:
        attempt += 1
        logger.info(f"--- Intento #{attempt} ---")
        
        # Renew token every 3 attempts
        if attempt > 1 and attempt % 3 == 1:
            logger.info("Renovando token de autenticacion...")
            if not api_client.authenticate():
                logger.error("Error al renovar token")
                time.sleep(CONFIG['retry_delay'])
                continue
        
        # Fetch data
        logger.info(f"Obteniendo {ENDPOINT['name']}...")
        data = api_client.fetch_invoices_monthly(first_day, last_day)
        
        if data is not None:
            # Save to MongoDB
            success = mongo_client.save_data(
                ENDPOINT['collection'],
                data,
                period,
                year,
                month
            )
            
            if success:
                completed = True
                result['success'] = True
                result['records'] = len(data)
                logger.info(f"[OK] {ENDPOINT['name']} completado exitosamente")
                break
            else:
                logger.error(f"[FAIL] Error al guardar en MongoDB")
        else:
            logger.error(f"[FAIL] Error al obtener {ENDPOINT['name']}")
        
        # Wait before next attempt
        if attempt < max_attempts and not completed:
            logger.info(f"Esperando {CONFIG['retry_delay']}s antes de reintentar...")
            time.sleep(CONFIG['retry_delay'])
    
    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  RESUMEN")
    logger.info("=" * 60)
    
    status_icon = "[OK]" if result['success'] else "[FAIL]"
    logger.info(f"{status_icon} {result['endpoint']}: {result['records']} registros")
    logger.info("=" * 60)
    
    # Cleanup
    mongo_client.close()
    
    # Output JSON for Node.js to parse
    print("\n__RESULT_JSON__")
    print(json.dumps({
        'success': result['success'],
        'results': [result],
        'period': period
    }))
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nProceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)
