#!/usr/bin/env python3
"""
Migration Script: Fix Month Names in MongoDB
Updates monthName field from "2025-01" format to Spanish month names like "Enero"
"""

import os
import sys
import logging
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Month names in Spanish
MONTH_NAMES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre'
}

# Configuration from environment variables
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'laudus_data')

if not MONGODB_URI:
    logger.error("❌ MONGODB_URI environment variable is required")
    sys.exit(1)


def migrate_invoices_monthly():
    """Update monthName in invoices_by_month collection"""
    try:
        logger.info("🔄 Connecting to MongoDB...")
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        collection = db['invoices_by_month']
        
        logger.info("📋 Migrating invoices_by_month collection...")
        
        # Get all documents
        documents = collection.find({})
        updated_count = 0
        
        for doc in documents:
            month_number = doc.get('monthNumber')
            if month_number and month_number in MONTH_NAMES:
                new_month_name = MONTH_NAMES[month_number]
                
                # Update the document
                result = collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': {'monthName': new_month_name}}
                )
                
                if result.modified_count > 0:
                    logger.info(f"  ✅ Updated {doc['month']}: {new_month_name}")
                    updated_count += 1
        
        logger.info(f"✅ Updated {updated_count} documents in invoices_by_month")
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error migrating invoices_by_month: {e}")
        return False


def migrate_invoices_by_branch():
    """Update monthName in invoices_by_branch collection"""
    try:
        logger.info("🔄 Connecting to MongoDB...")
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        collection = db['invoices_by_branch']
        
        logger.info("📋 Migrating invoices_by_branch collection...")
        
        # Get all documents
        documents = collection.find({})
        updated_count = 0
        
        for doc in documents:
            month_number = doc.get('monthNumber')
            if month_number and month_number in MONTH_NAMES:
                new_month_name = MONTH_NAMES[month_number]
                
                # Update the document
                result = collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': {'monthName': new_month_name}}
                )
                
                if result.modified_count > 0:
                    logger.info(f"  ✅ Updated {doc['month']}: {new_month_name}")
                    updated_count += 1
        
        logger.info(f"✅ Updated {updated_count} documents in invoices_by_branch")
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error migrating invoices_by_branch: {e}")
        return False


def main():
    """Run all migrations"""
    logger.info("🚀 Starting migration: Fix Month Names")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    success = True
    
    # Migrate invoices_by_month
    if not migrate_invoices_monthly():
        success = False
    
    logger.info("")
    
    # Migrate invoices_by_branch
    if not migrate_invoices_by_branch():
        success = False
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Migration completed successfully!")
    else:
        logger.error("❌ Migration completed with errors")
        sys.exit(1)


if __name__ == '__main__':
    main()
