#!/usr/bin/env python3
"""
Laudus Balance Sheet Manual Fetcher
For manual data loading with specific date and endpoints
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
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
    'timeout': 900,  # 15 minutes
    'retry_delay': 300,  # 5 minutes between retries
    'endpoint_delay': 120,  # 2 minutes between endpoints
    'max_retries': 20,  # Maximum retry attempts per endpoint
}

# Endpoints configuration
ENDPOINTS = {
    'totals': {
        'name': 'totals',
        'path': '/accounting/balanceSheet/totals',
        'collection': 'balance_totals'
    },
    'standard': {
        'name': 'standard',
        'path': '/accounting/balanceSheet/standard',
        'collection': 'balance_standard'
    },
    '8columns': {
        'name': '8Columns',
        'path': '/accounting/balanceSheet/8Columns',
        'collection': 'balance_8columns'
    }
}


class LaudusAPIClient:
    """Client for Laudus API interactions"""
    
    def __init__(self):
        self.base_url = CONFIG['api_url']
        self.token: Optional[str] = None
        self.session = requests.Session()
        
        # Configure retry strategy with longer delays
        retry_strategy = Retry(
            total=2,  # Reduced from 3 - we have application-level retries
            backoff_factor=10,  # Increased from 1 - wait 10, 20 seconds
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
            
            # Extract token properly - response could be JSON or plain text
            try:
                # Try JSON first
                token_data = response.json()
                if isinstance(token_data, dict) and 'token' in token_data:
                    self.token = token_data['token']
                elif isinstance(token_data, str):
                    self.token = token_data
                else:
                    self.token = str(token_data)
            except:
                # Fallback to text response
                self.token = response.text.strip().strip('"').strip("'")
            
            # Update session headers with token
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            logger.info("Autenticacion exitosa")
            logger.debug(f"Token length: {len(self.token)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Error de autenticacion: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:200]}")
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
            logger.debug(f"URL: {url}")
            logger.debug(f"Params: {params}")
            logger.debug(f"Has token: {self.token is not None}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            record_count = len(data)
            
            logger.info(f"{endpoint['name']}: {record_count} registros obtenidos")
            return data
            
        except requests.Timeout:
            logger.error(f"Timeout obteniendo {endpoint['name']} (>{CONFIG['timeout']}s)")
            return None
        except requests.HTTPError as e:
            logger.error(f"HTTP Error obteniendo {endpoint['name']}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Status: {e.response.status_code}")
                logger.error(f"   Response: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo {endpoint['name']}: {e}")
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
            logger.info("Conectando a MongoDB Atlas...")
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            
            # Test connection
            self.client.admin.command('ping')
            
            self.connected = True
            logger.info("Conexion a MongoDB exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error de conexion a MongoDB: {e}")
            return False
    
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
                'loadSource': 'manual',
                'data': data
            }
            
            # Upsert (replace if exists, insert if not)
            result = collection.replace_one(
                {'_id': document['_id']},
                document,
                upsert=True
            )
            
            logger.info(f"Guardado en MongoDB: {collection_name} ({len(data)} registros)")
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
    """Main execution function with intelligent retry logic"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fetch Laudus balance sheet data manually')
    parser.add_argument('--date', required=True, help='Target date in YYYY-MM-DD format')
    parser.add_argument('--endpoints', nargs='+', required=True, 
                       choices=['totals', 'standard', '8columns'],
                       help='Endpoints to fetch (totals, standard, 8columns)')
    
    args = parser.parse_args()
    
    target_date = args.date
    selected_endpoints = [ENDPOINTS[ep] for ep in args.endpoints]
    
    logger.info("=" * 60)
    logger.info("  CARGA MANUAL DE BALANCE SHEET")
    logger.info("=" * 60)
    logger.info(f"Fecha: {target_date}")
    logger.info(f"Endpoints: {', '.join([ep['name'] for ep in selected_endpoints])}")
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
    
    # Track completion status for each endpoint
    completed = {endpoint['name']: False for endpoint in selected_endpoints}
    results = []
    attempt = 0
    max_attempts = CONFIG['max_retries']
    
    # Main retry loop
    while attempt < max_attempts and not all(completed.values()):
        attempt += 1
        logger.info(f"--- Intento #{attempt} ---")
        
        # Renew token every 3 attempts
        if attempt > 1 and attempt % 3 == 1:
            logger.info("Renovando token de autenticacion...")
            if not api_client.authenticate():
                logger.error("Error al renovar token")
                time.sleep(CONFIG['retry_delay'])
                continue
        
        # Process each endpoint
        for i, endpoint in enumerate(selected_endpoints):
            if completed[endpoint['name']]:
                logger.info(f"Omitiendo {endpoint['name']} (ya completado)")
                continue
            
            # Add delay between endpoints (except first one in first attempt)
            if attempt == 1 and i > 0:
                logger.info(f"Esperando {CONFIG['endpoint_delay']}s antes del siguiente endpoint...")
                time.sleep(CONFIG['endpoint_delay'])
            
            # Fetch data
            logger.info(f"Obteniendo {endpoint['name']}...")
            data = api_client.fetch_balance_sheet(endpoint, target_date)
            
            if data is not None:
                # Save to MongoDB
                success = mongo_client.save_data(
                    endpoint['collection'],
                    data,
                    endpoint['name'],
                    target_date
                )
                
                if success:
                    completed[endpoint['name']] = True
                    logger.info(f"[OK] {endpoint['name']} completado exitosamente")
                    
                    # Update or add result
                    result_exists = False
                    for r in results:
                        if r['endpoint'] == endpoint['name']:
                            r['success'] = True
                            r['records'] = len(data)
                            result_exists = True
                            break
                    
                    if not result_exists:
                        results.append({
                            'endpoint': endpoint['name'],
                            'success': True,
                            'records': len(data)
                        })
                else:
                    logger.error(f"[FAIL] Error al guardar {endpoint['name']} en MongoDB")
            else:
                logger.error(f"[FAIL] Error al obtener {endpoint['name']}")
            
            logger.info("")
        
        # Check if all completed
        if all(completed.values()):
            logger.info("=" * 60)
            logger.info("  [OK] TODOS LOS ENDPOINTS COMPLETADOS")
            logger.info("=" * 60)
            break
        
        # Wait before next attempt
        if attempt < max_attempts:
            pending = [name for name, status in completed.items() if not status]
            logger.info(f"Pendientes: {', '.join(pending)}")
            logger.info(f"Esperando {CONFIG['retry_delay']}s antes de reintentar...")
            time.sleep(CONFIG['retry_delay'])
    
    # Add failed endpoints to results
    for endpoint in selected_endpoints:
        if not completed[endpoint['name']]:
            result_exists = False
            for r in results:
                if r['endpoint'] == endpoint['name']:
                    result_exists = True
                    break
            
            if not result_exists:
                results.append({
                    'endpoint': endpoint['name'],
                    'success': False,
                    'records': 0
                })
    
    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  RESUMEN")
    logger.info("=" * 60)
    
    for result in results:
        status_icon = "[OK]" if result['success'] else "[FAIL]"
        logger.info(f"{status_icon} {result['endpoint']}: {result['records']} registros")
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    logger.info("")
    logger.info(f"Total: {success_count}/{total_count} endpoints completados")
    logger.info("=" * 60)
    
    # Cleanup
    mongo_client.close()
    
    # Output JSON for Node.js to parse
    print("\n__RESULT_JSON__")
    print(json.dumps({
        'success': success_count == total_count,
        'results': results
    }))
    
    # Exit with appropriate code
    sys.exit(0 if success_count == total_count else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nProceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)
