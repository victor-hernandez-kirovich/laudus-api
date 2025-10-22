#!/usr/bin/env python3
"""
Laudus Balance Sheet Manual Fetcher
For manual data loading with specific date and endpoints
"""

import os
import sys
import json
import logging
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
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
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
            logger.info("Autenticando con Laudus API...")
            
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
            
            self.token = response.text.strip('"')
            logger.info(f"Token obtenido (primeros 20 chars): {self.token[:20]}...")
            logger.info(f"Token length: {len(self.token)}")
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            
            logger.info("Autenticacion exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error de autenticacion: {e}")
            return False
    
    def fetch_balance_sheet(self, endpoint: Dict, date_to: str) -> Optional[List[Dict]]:
        """Fetch balance sheet data from specified endpoint"""
        try:
            logger.info(f"Obteniendo {endpoint['name']}...")
            logger.info(f"Authorization header present: {'Authorization' in self.session.headers}")
            
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
            
            logger.info(f"{endpoint['name']}: {record_count} registros obtenidos")
            return data
            
        except requests.Timeout:
            logger.error(f"Timeout obteniendo {endpoint['name']} (>{CONFIG['timeout']}s)")
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
    """Main execution function"""
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
    
    # Track results
    results = []
    
    # Process each endpoint
    for endpoint in selected_endpoints:
        # Fetch data
        data = api_client.fetch_balance_sheet(endpoint, target_date)
        
        if data is not None:
            # Save to MongoDB
            success = mongo_client.save_data(
                endpoint['collection'],
                data,
                endpoint['name'],
                target_date
            )
            
            results.append({
                'endpoint': endpoint['name'],
                'success': success,
                'records': len(data) if success else 0
            })
        else:
            results.append({
                'endpoint': endpoint['name'],
                'success': False,
                'records': 0
            })
        
        logger.info("")
    
    # Final summary
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
