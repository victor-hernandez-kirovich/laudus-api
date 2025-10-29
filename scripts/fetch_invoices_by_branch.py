#!/usr/bin/env python3
"""
Laudus Invoices by Branch Data Fetcher
Fetches sales invoices aggregated by branch for each month and stores them in MongoDB
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from calendar import monthrange
import time

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}-invoices-branch.log")
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
    'timeout': 1800,  # 30 minutes
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
            logger.info(f"Authenticating with Laudus {CONFIG['api_url']}...")
            
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
            
            logger.info("Authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:200]}")
            return False
    
    def fetch_invoices_by_branch(self, date_from: str, date_to: str) -> Optional[list]:
        """Fetch invoices aggregated by branch for a date range"""
        try:
            logger.info(f"Fetching invoices by branch from {date_from} to {date_to}...")
            
            params = {
                'dateFrom': date_from,
                'dateTo': date_to
            }
            
            url = f"{self.base_url}/reports/sales/invoices/byBranch"
            logger.info(f"   URL: {url}")
            logger.debug(f"   Params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=CONFIG['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Data is an array of branch aggregates
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Retrieved data for {len(data)} branches")
                total_net = sum(branch.get('net', 0) for branch in data)
                logger.info(f"   Total Net: ${total_net:,.2f}")
                branch_names = [str(b.get('branch', 'N/A') or 'N/A') for b in data[:5]]
                logger.info(f"   Branches: {', '.join(branch_names)}")
                if len(data) > 5:
                    logger.info(f"   ... and {len(data) - 5} more")
            else:
                logger.warning(f"No data returned for {date_from} to {date_to}")
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching invoices by branch")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching invoices by branch: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
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
            logger.info("Connecting to MongoDB Atlas...")
            
            if not CONFIG['mongodb_uri']:
                logger.error("MONGODB_URI not configured")
                return False
            
            self.client = MongoClient(CONFIG['mongodb_uri'])
            self.db = self.client[CONFIG['mongodb_database']]
            self.collection = self.db['invoices_by_branch']
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("MongoDB connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
    
    def save_invoices(self, year: int, month: int, date_from: str, date_to: str, branches: list) -> bool:
        """Save invoices by branch data to MongoDB for a specific month"""
        try:
            month_key = f"{year}-{month:02d}"
            logger.info(f"Saving invoices by branch for {month_key} to MongoDB...")
            
            # Clean up branch data - ensure branch names are not null
            cleaned_branches = []
            for branch in branches:
                branch_copy = branch.copy()
                if not branch_copy.get('branch'):
                    branch_copy['branch'] = 'Sin Sucursal'
                    logger.warning(f"Branch with null name found, renamed to 'Sin Sucursal'")
                cleaned_branches.append(branch_copy)
            
            # Calculate totals
            total_net = sum(branch.get('net', 0) for branch in cleaned_branches)
            total_margin = sum(branch.get('margin', 0) for branch in cleaned_branches)
            total_discounts = sum(branch.get('discounts', 0) for branch in cleaned_branches)
            avg_margin_pct = sum(branch.get('marginPercentage', 0) for branch in cleaned_branches) / len(cleaned_branches) if cleaned_branches else 0
            avg_discount_pct = sum(branch.get('discountsPercentage', 0) for branch in cleaned_branches) / len(cleaned_branches) if cleaned_branches else 0
            
            # Month name in Spanish
            month_names = {
                1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
            }
            
            document = {
                'month': month_key,
                'year': year,
                'monthNumber': month,
                'monthName': month_names[month],
                'startDate': date_from,
                'endDate': date_to,
                'branches': cleaned_branches,
                'totalNet': total_net,
                'totalMargin': total_margin,
                'totalDiscounts': total_discounts,
                'avgMarginPercentage': avg_margin_pct,
                'avgDiscountPercentage': avg_discount_pct,
                'branchCount': len(cleaned_branches),
                'insertedAt': datetime.utcnow()
            }
            
            # Upsert (update if exists, insert if not)
            result = self.collection.update_one(
                {'month': month_key},
                {'$set': document},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Inserted new document for {month_key}")
            else:
                logger.info(f"Updated existing document for {month_key}")
            
            logger.info(f"   Total Net: ${total_net:,.2f}")
            logger.info(f"   Branch Count: {len(cleaned_branches)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


def main():
    """Main execution function"""
    logger.info("=" * 80)
    logger.info("Laudus Invoices by Branch Fetcher (Monthly)")
    logger.info("=" * 80)
    
    # Validate configuration
    required_vars = ['LAUDUS_PASSWORD', 'LAUDUS_COMPANY_VAT', 'MONGODB_URI']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Get date range from environment
    start_year = int(os.getenv('START_YEAR', '2025'))
    start_month = int(os.getenv('START_MONTH', '1'))
    end_year = int(os.getenv('END_YEAR', '2025'))
    end_month = int(os.getenv('END_MONTH', '10'))
    skip_existing = os.getenv('SKIP_EXISTING', 'false').lower() == 'true'
    
    logger.info(f"Date range: {start_year}-{start_month:02d} to {end_year}-{end_month:02d}")
    logger.info(f"Skip existing: {skip_existing}")
    
    # Initialize clients
    api_client = LaudusAPIClient()
    db_client = MongoDBClient()
    
    # Authenticate with Laudus API
    if not api_client.authenticate():
        logger.error("Failed to authenticate. Exiting.")
        sys.exit(1)
    
    # Connect to MongoDB
    if not db_client.connect():
        logger.error("Failed to connect to MongoDB. Exiting.")
        sys.exit(1)
    
    # Generate list of months to process
    months_to_process = []
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        months_to_process.append((current_year, current_month))
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    
    logger.info(f"Total months to process: {len(months_to_process)}")
    logger.info("")
    
    # Process each month
    successful_months = 0
    failed_months = []
    
    for year, month in months_to_process:
        month_key = f"{year}-{month:02d}"
        
        # Check if already exists and skip if requested
        if skip_existing and db_client.collection.find_one({'month': month_key}):
            logger.info(f"⏭️  Skipping {month_key} (already exists)")
            successful_months += 1
            continue
        
        logger.info("-" * 80)
        logger.info(f"📅 Processing {month_key}")
        logger.info("-" * 80)
        
        # Calculate date range for the month
        last_day = monthrange(year, month)[1]
        date_from = f"{year}-{month:02d}-01"
        date_to = f"{year}-{month:02d}-{last_day:02d}"
        
        # Fetch data with retry logic
        retry_count = 0
        success = False
        data = None
        
        while retry_count < CONFIG['max_retries'] and not success:
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count}/{CONFIG['max_retries']}")
                time.sleep(60)  # Wait 1 minute before retry
            
            # Fetch invoices by branch
            data = api_client.fetch_invoices_by_branch(date_from, date_to)
            
            if data is not None and isinstance(data, list):
                # Save to MongoDB
                if db_client.save_invoices(year, month, date_from, date_to, data):
                    success = True
                    successful_months += 1
                    logger.info(f"✅ Successfully processed {month_key}")
                else:
                    retry_count += 1
            else:
                retry_count += 1
        
        if not success:
            logger.error(f"❌ Failed to process {month_key} after {CONFIG['max_retries']} retries")
            failed_months.append(month_key)
        
        # Delay between months to avoid rate limiting
        if months_to_process[-1] != (year, month):  # Don't delay after last month
            logger.info("Waiting 5 seconds before next month...")
            time.sleep(5)
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total months: {len(months_to_process)}")
    logger.info(f"Successful: {successful_months}")
    logger.info(f"Failed: {len(failed_months)}")
    
    if failed_months:
        logger.error(f"Failed months: {', '.join(failed_months)}")
        db_client.close()
        sys.exit(1)
    
    logger.info("Status: SUCCESS ✅")
    logger.info("=" * 80)
    
    # Cleanup
    db_client.close()
    
    logger.info("All done!")
    sys.exit(0)


if __name__ == "__main__":
    main()
