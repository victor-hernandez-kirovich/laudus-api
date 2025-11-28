#!/usr/bin/env python3
"""
One-time migration script to add loadSource field to existing documents
All documents without loadSource will be marked as 'automatic' (assumed from daily automation)
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'laudus_data')

COLLECTIONS = ['balance_8columns']

def main():
    print("=" * 60)
    print("  MIGRATION: Add loadSource field to existing documents")
    print("=" * 60)
    print()
    
    if not MONGODB_URI:
        print("❌ Error: MONGODB_URI environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
        print()
        
        total_updated = 0
        
        # Update each collection
        for collection_name in COLLECTIONS:
            print(f"📊 Processing collection: {collection_name}")
            collection = db[collection_name]
            
            # Find documents without loadSource field
            query = {'loadSource': {'$exists': False}}
            count = collection.count_documents(query)
            
            if count == 0:
                print(f"   ℹ️  No documents to update")
            else:
                print(f"   📝 Found {count} documents without loadSource")
                
                # Update all documents to add loadSource: 'automatic'
                result = collection.update_many(
                    query,
                    {'$set': {'loadSource': 'automatic'}}
                )
                
                print(f"   ✅ Updated {result.modified_count} documents")
                total_updated += result.modified_count
            
            print()
        
        print("=" * 60)
        print(f"  ✅ Migration completed!")
        print(f"  Total documents updated: {total_updated}")
        print("=" * 60)
        
        client.close()
        
    except PyMongoError as e:
        print(f"❌ MongoDB error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
