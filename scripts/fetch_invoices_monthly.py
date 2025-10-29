#!/usr/bin/env python3
"""
Laudus Monthly Invoices Data Fetcher
Fetches sales invoices by month and stores them in MongoDB
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from calendar import monthrange
import time

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-invoices.log")
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
    'timeout': 1800,  # 30 minutes (invoices might have a lot of data)
    'retry_delay': 300,  # 5 minutes
    'max_retries': 3,
}


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
                token_data = response.json()
                if isinstance(token_data, dict) and 'token' in token_data:
                    self.token = token_data['token']
                elif isinstance(token_data, str):
                    self.token = token_data
                else:
                    self.token = str(token_data)
            except:
                self.token = response.text.strip().strip('"').strip("'")
            
            # Update session headers with token
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            logger.info("✅ Authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:200]}")
            return False
    
    def fetch_invoices_by_month(self, year: int, month: int) -> Optional[list]:
        """Fetch aggregated invoices data for a specific month"""
        try:
            # Calculate first and last day of the month
            first_day = f"{year}-{month:02d}-01"
            last_day_num = monthrange(year, month)[1]
            last_day = f"{year}-{month:02d}-{last_day_num:02d}"
            
            logger.info(f"📊 Fetching invoices for {year}-{month:02d} ({first_day} to {last_day})...")
            
            params = {
                'dateFrom': first_day,
                'dateTo': last_day
            }
            
            url = f"{self.base_url}/reports/sales/invoices/byMonth"
            logger.info(f"   URL: {url}")
            logger.debug(f"   Params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Data is an array of monthly aggregates
            if isinstance(data, list) and len(data) > 0:
                month_data = data[0]  # Should be only one month in response
                logger.info(f"✅ Retrieved data for {month_data.get('month', 'N/A')}")
                logger.info(f"   Total: ${month_data.get('total', 0):,.2f}")
                logger.info(f"   Net: ${month_data.get('net', 0):,.2f}")
                logger.info(f"   Margin: {month_data.get('margin', 0):,.2f}%")
                logger.info(f"   Quantity: {month_data.get('quantity', 0)}")
            else:
                logger.warning(f"⚠️  No data returned for {year}-{month:02d}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout fetching invoices for {year}-{month:02d}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching invoices for {year}-{month:02d}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None


class MongoDBClient:
    """Client for MongoDB operations"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            logger.info("🔌 Connecting to MongoDB Atlas...")
            
            if not CONFIG['mongodb_uri']:
                logger.error("❌ MONGODB_URI not configured")
                return False
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            self.collection = self.db['invoices_by_month']
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
    
    def save_invoices(self, year: int, month: int, data: list) -> bool:
        """Save aggregated invoices data to MongoDB"""
        try:
            month_key = f"{year}-{month:02d}"
            logger.info(f"💾 Saving invoices for {month_key} to MongoDB...")
            
            # Data is an array, get first element (should be the only month)
            if not isinstance(data, list) or len(data) == 0:
                logger.error(f"❌ Invalid data format for {month_key}")
                return False
            
            month_data = data[0]
            
            document = {
                'month': month_key,
                'year': year,
                'monthNumber': month,
                'monthName': month_data.get('month', month_key),
                'total': month_data.get('total', 0),
                'returns': month_data.get('returns', 0),
                'returnsPercentage': month_data.get('returnsPercentage', 0),
                'net': month_data.get('net', 0),
                'netChangeYoYPercentage': month_data.get('netChangeYoYPercentage', 0),
                'margin': month_data.get('margin', 0),
                'marginChangeYoYPercentage': month_data.get('marginChangeYoYPercentage', 0),
                'discounts': month_data.get('discounts', 0),
                'discountsPercentage': month_data.get('discountsPercentage', 0),
                'quantity': month_data.get('quantity', 0),
                'insertedAt': datetime.utcnow(),
                'rawData': month_data  # Keep original data
            }
            
            # Upsert (update if exists, insert if not)
            result = self.collection.update_one(
                {'month': month_key},
                {'$set': document},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"✅ Inserted new document for {month_key}")
            else:
                logger.info(f"✅ Updated existing document for {month_key}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving to MongoDB: {e}")
            return False
    
    def get_existing_months(self) -> List[str]:
        """Get list of months already in database"""
        try:
            existing = self.collection.distinct('month')
            return sorted(existing)
        except Exception as e:
            logger.error(f"❌ Error getting existing months: {e}")
            return []
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")


def generate_month_range(start_year: int, start_month: int, end_year: int, end_month: int) -> List[tuple]:
    """Generate list of (year, month) tuples for the range"""
    months = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        months.append((current_year, current_month))
        
        # Move to next month
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    return months


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("🚀 Laudus Monthly Invoices Fetcher")
    logger.info("=" * 80)
    
    # Validate configuration
    required_vars = ['LAUDUS_PASSWORD', 'LAUDUS_COMPANY_VAT', 'MONGODB_URI']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Get date range from environment or use defaults
    # Default: January 2025 to current month
    current_date = datetime.now()
    start_year = int(os.getenv('INVOICES_START_YEAR', '2025'))
    start_month = int(os.getenv('INVOICES_START_MONTH', '1'))
    end_year = int(os.getenv('INVOICES_END_YEAR', str(current_date.year)))
    end_month = int(os.getenv('INVOICES_END_MONTH', str(current_date.month)))
    
    logger.info(f"📅 Date range: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
    
    # Initialize clients
    api_client = LaudusAPIClient()
    db_client = MongoDBClient()
    
    # Authenticate with Laudus API
    if not api_client.authenticate():
        logger.error("❌ Failed to authenticate. Exiting.")
        sys.exit(1)
    
    # Connect to MongoDB
    if not db_client.connect():
        logger.error("❌ Failed to connect to MongoDB. Exiting.")
        sys.exit(1)
    
    # Check existing months
    existing_months = db_client.get_existing_months()
    if existing_months:
        logger.info(f"📊 Found {len(existing_months)} existing months in database")
        logger.info(f"   Existing: {', '.join(existing_months)}")
    
    # Generate month range
    months_to_fetch = generate_month_range(start_year, start_month, end_year, end_month)
    logger.info(f"📋 Total months to process: {len(months_to_fetch)}")
    
    # Process each month
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for idx, (year, month) in enumerate(months_to_fetch, 1):
        month_key = f"{year}-{month:02d}"
        logger.info("")
        logger.info(f"📌 Processing month {idx}/{len(months_to_fetch)}: {month_key}")
        logger.info("-" * 80)
        
        # Check if month should be skipped (option to skip existing)
        skip_existing = os.getenv('SKIP_EXISTING_MONTHS', 'false').lower() == 'true'
        if skip_existing and month_key in existing_months:
            logger.info(f"⏭️  Skipping {month_key} (already exists)")
            skipped_count += 1
            continue
        
        # Retry logic
        retry_count = 0
        success = False
        
        while retry_count < CONFIG['max_retries'] and not success:
            if retry_count > 0:
                logger.info(f"🔄 Retry attempt {retry_count}/{CONFIG['max_retries']} for {month_key}")
                time.sleep(CONFIG['retry_delay'])
            
            # Fetch invoices
            data = api_client.fetch_invoices_by_month(year, month)
            
            if data is not None:
                # Save to MongoDB
                if db_client.save_invoices(year, month, data):
                    success = True
                    success_count += 1
                    logger.info(f"✅ Successfully processed {month_key}")
                else:
                    retry_count += 1
            else:
                retry_count += 1
        
        if not success:
            logger.error(f"❌ Failed to process {month_key} after {CONFIG['max_retries']} retries")
            error_count += 1
        
        # Delay between months to avoid rate limiting
        if idx < len(months_to_fetch):
            delay = int(os.getenv('DELAY_BETWEEN_MONTHS', '5'))
            logger.info(f"⏳ Waiting {delay}s before next month...")
            time.sleep(delay)
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 EXECUTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"⏭️  Skipped: {skipped_count}")
    logger.info(f"❌ Errors: {error_count}")
    logger.info(f"📋 Total processed: {len(months_to_fetch)}")
    logger.info("=" * 80)
    
    # Cleanup
    db_client.close()
    
    # Exit with appropriate code
    if error_count > 0:
        logger.warning("⚠️  Some months failed to process")
        sys.exit(1)
    else:
        logger.info("🎉 All months processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
