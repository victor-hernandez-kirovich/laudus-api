#!/usr/bin/env python3
"""
Laudus Invoices By Branch Fetcher
For manual data loading with specific year and month
Endpoint: /reports/sales/invoices/byBranch
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
    'name': 'InvoicesByBranch',
    'path': '/reports/sales/invoices/byBranch',
    'collection': 'invoices_by_branch'
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
    
    def fetch_invoices_by_branch(self, date_from: str, date_to: str) -> Optional[List[Dict]]:
        """Fetch invoices by branch data"""
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
    
    def save_data(self, collection_name: str, data: List[Dict], period: str, year: int, month: int, first_day: str, last_day: str) -> bool:
        """Save invoices by branch data to MongoDB - one document per month with branches array"""
        try:
            if not self.connected:
                raise Exception("No conectado a MongoDB")
            
            collection = self.db[collection_name]
            
            if not data or len(data) == 0:
                logger.warning("No hay datos para guardar")
                return False
            
            # Build branches array from data
            branches = []
            total_net = 0
            total_margin = 0
            total_discounts = 0
            
            for branch_data in data:
                branch_name = branch_data.get('branchName') or branch_data.get('branch', 'Sin Sucursal')
                net = branch_data.get('net', 0)
                margin = branch_data.get('margin', 0)
                discounts = branch_data.get('discounts', 0)
                
                total_net += net
                total_margin += margin
                total_discounts += discounts
                
                branches.append({
                    'branch': branch_name,
                    'net': net,
                    'netPercentage': branch_data.get('netPercentage', 0),
                    'margin': margin,
                    'marginPercentage': branch_data.get('marginPercentage', 0),
                    'discounts': discounts,
                    'discountsPercentage': branch_data.get('discountsPercentage', 0)
                })
            
            # Calculate averages
            branch_count = len(branches)
            avg_discount_percentage = sum(b.get('discountsPercentage', 0) for b in branches) / branch_count if branch_count > 0 else 0
            avg_margin_percentage = sum(b.get('marginPercentage', 0) for b in branches) / branch_count if branch_count > 0 else 0
            
            # Build document in expected format
            document = {
                'month': period,  # YYYY-MM format
                'avgDiscountPercentage': avg_discount_percentage,
                'avgMarginPercentage': avg_margin_percentage,
                'branchCount': branch_count,
                'branches': branches,
                'endDate': last_day,
                'insertedAt': datetime.now(timezone.utc),
                'monthName': MONTH_NAMES.get(month, ''),
                'monthNumber': month,
                'startDate': first_day,
                'totalDiscounts': total_discounts,
                'totalMargin': total_margin,
                'totalNet': total_net,
                'year': year
            }
            
            # Upsert by month field (replace if exists, insert if not)
            result = collection.replace_one(
                {'month': period},
                document,
                upsert=True
            )
            
            logger.info(f"Guardado en MongoDB: {collection_name} ({branch_count} sucursales para {period})")
            logger.info(f"   Total Net: {total_net:,.0f} | Total Margin: {total_margin:,.2f}")
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
    parser = argparse.ArgumentParser(description='Fetch Laudus invoices by branch')
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
    logger.info("  CARGA FACTURAS POR SUCURSAL")
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
        data = api_client.fetch_invoices_by_branch(first_day, last_day)
        
        if data is not None:
            # Save to MongoDB
            success = mongo_client.save_data(
                ENDPOINT['collection'],
                data,
                period,
                year,
                month,
                first_day,
                last_day
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
