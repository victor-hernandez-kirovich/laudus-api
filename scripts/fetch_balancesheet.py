#!/usr/bin/env python3
"""
Laudus Balance Sheet Data Fetcher
Migrated from PowerShell automation to Python for GitHub Actions
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-fetch.log")
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
    'timeout': 900,  # 15 minutes
    'retry_delay': 300,  # 5 minutes
    'max_retries': 60,  # 5 hours of retries
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
            logger.info(f"🔐 Authenticating with Laudus {CONFIG['api_url']}...")
            
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
            
            logger.info("✅ Authentication successful")
            logger.debug(f"Token length: {len(self.token)} chars")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:200]}")
            return False
    
    def fetch_balance_sheet(self, endpoint: Dict, date_to: str) -> Optional[List[Dict]]:
        """Fetch balance sheet data from specified endpoint"""
        try:
            logger.info(f"📊 Fetching {endpoint['name']}...")
            
            params = {
                'dateTo': date_to,
                'showAccountsWithZeroBalance': 'true',
                'showOnlyAccountsWithActivity': 'false'
            }
            
            url = f"{self.base_url}{endpoint['path']}"
            logger.info(f"   URL: {url}")
            logger.debug(f"   Params: {params}")
            logger.debug(f"   Has token: {self.token is not None}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            record_count = len(data)
            
            logger.info(f"✅ {endpoint['name']}: {record_count} records retrieved")
            return data
            
        except requests.Timeout:
            logger.error(f"⏱️ Timeout fetching {endpoint['name']} (>{CONFIG['timeout']}s)")
            return None
        except requests.HTTPError as e:
            logger.error(f"❌ HTTP Error fetching {endpoint['name']}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Status: {e.response.status_code}")
                logger.error(f"   Response: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching {endpoint['name']}: {e}")
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
            logger.info("🔌 Connecting to MongoDB Atlas...")
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            
            # Test connection
            self.client.admin.command('ping')
            
            self.connected = True
            logger.info("✅ MongoDB connection successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
    
    def save_data(self, collection_name: str, data: List[Dict], endpoint_name: str, date_str: str) -> bool:
        """Save balance sheet data to MongoDB"""
        try:
            if not self.connected:
                raise Exception("Not connected to MongoDB")
            
            collection = self.db[collection_name]
            
            document = {
                '_id': f"{date_str}-{endpoint_name}",
                'date': date_str,
                'endpointType': endpoint_name,
                'recordCount': len(data),
                'insertedAt': datetime.utcnow(),
                'loadSource': 'automatic',
                'data': data
            }
            
            # Upsert (replace if exists, insert if not)
            result = collection.replace_one(
                {'_id': document['_id']},
                document,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✅ Saved to MongoDB: {collection_name} ({len(data)} records)")
                return True
            else:
                logger.warning(f"⚠️ No changes made to {collection_name}")
                return True
                
        except PyMongoError as e:
            logger.error(f"❌ MongoDB save error: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")


def get_yesterday_date() -> str:
    """Get yesterday's date in YYYY-MM-DD format"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("  LAUDUS BALANCE SHEET AUTOMATION")
    logger.info("=" * 60)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Validate configuration
    if not all([CONFIG['password'], CONFIG['company_vat'], CONFIG['mongodb_uri']]):
        logger.error("❌ Missing required environment variables")
        logger.error("Required: LAUDUS_PASSWORD, LAUDUS_COMPANY_VAT, MONGODB_URI")
        sys.exit(1)
    
    # Initialize clients
    api_client = LaudusAPIClient()
    mongo_client = MongoDBClient()
    
    # Authenticate
    if not api_client.authenticate():
        logger.error("❌ Failed to authenticate with Laudus API")
        sys.exit(1)
    
    # Connect to MongoDB
    if not mongo_client.connect():
        logger.error("❌ Failed to connect to MongoDB")
        sys.exit(1)
    
    # Get target date
    target_date = get_yesterday_date()
    logger.info(f"📅 Target date: {target_date}")
    logger.info("")
    
    # Track completion status
    completed = {endpoint['name']: False for endpoint in ENDPOINTS}
    attempt = 0
    max_attempts = CONFIG['max_retries']
    
    # Main retry loop
    while attempt < max_attempts and not all(completed.values()):
        attempt += 1
        logger.info(f"--- Attempt #{attempt} ---")
        
        # Renew token every 3 attempts
        if attempt > 1 and attempt % 3 == 1:
            logger.info("🔄 Renewing authentication token...")
            if not api_client.authenticate():
                logger.error("❌ Failed to renew token")
                time.sleep(CONFIG['retry_delay'])
                continue
        
        # Process each endpoint
        for endpoint in ENDPOINTS:
            if completed[endpoint['name']]:
                logger.info(f"⏭️  Skipping {endpoint['name']} (already completed)")
                continue
            
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
                
                if success:
                    completed[endpoint['name']] = True
                    logger.info(f"✅ {endpoint['name']} completed successfully")
                else:
                    logger.error(f"❌ Failed to save {endpoint['name']} to MongoDB")
            else:
                logger.error(f"❌ Failed to fetch {endpoint['name']}")
            
            logger.info("")
        
        # Check if all completed
        if all(completed.values()):
            logger.info("=" * 60)
            logger.info("  ✅ ALL ENDPOINTS COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            break
        
        # Wait before next attempt
        if attempt < max_attempts:
            pending = [name for name, status in completed.items() if not status]
            logger.info(f"⏳ Pending endpoints: {', '.join(pending)}")
            logger.info(f"💤 Waiting {CONFIG['retry_delay']}s before retry...")
            time.sleep(CONFIG['retry_delay'])
    
    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("  FINAL SUMMARY")
    logger.info("=" * 60)
    
    success_count = sum(completed.values())
    total_count = len(completed)
    
    for endpoint_name, status in completed.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {endpoint_name}: {'Completed' if status else 'Failed'}")
    
    logger.info("")
    logger.info(f"Total: {success_count}/{total_count} endpoints completed")
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Cleanup
    mongo_client.close()
    
    # Exit with appropriate code
    sys.exit(0 if success_count == total_count else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)
