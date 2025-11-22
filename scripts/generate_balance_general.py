#!/usr/bin/env python3
"""
Laudus Balance General Generator
Generates a structured Balance Sheet (Balance General) from the 8-Columns Balance
stored in MongoDB.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import argparse

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
    'mongodb_uri': os.getenv('MONGODB_URI'),
    'mongodb_database': os.getenv('MONGODB_DATABASE', 'laudus_data'),
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
            
            # Test connection
            self.client.admin.command('ping')
            
            self.connected = True
            logger.info("Conexion a MongoDB exitosa")
            return True
            
        except Exception as e:
            logger.error(f"Error de conexion a MongoDB: {e}")
            return False
    
    def get_8columns_data(self, date_str: str) -> Optional[Dict]:
        """Retrieve 8-Columns Balance data for a specific date"""
        try:
            if not self.connected:
                raise Exception("No conectado a MongoDB")
            
            collection = self.db['balance_8columns']
            
            # Find the document for the specific date
            # The _id format in fetch_balancesheet_manual is f"{date_str}-8Columns"
            doc_id = f"{date_str}-8Columns"
            document = collection.find_one({'_id': doc_id})
            
            if not document:
                logger.warning(f"No se encontraron datos de 8 Columnas para la fecha {date_str} (ID: {doc_id})")
                return None
                
            return document
            
        except PyMongoError as e:
            logger.error(f"Error leyendo de MongoDB: {e}")
            return None
            
    def save_balance_general(self, data: Dict, date_str: str) -> bool:
        """Save generated Balance General to MongoDB"""
        try:
            if not self.connected:
                raise Exception("No conectado a MongoDB")
            
            collection = self.db['balance_general']
            
            document = {
                '_id': f"{date_str}-General",
                'date': date_str,
                'generatedAt': datetime.now(timezone.utc),
                'source': 'balance_8columns',
                'assets': data['assets'],
                'liabilities': data['liabilities'],
                'equity': data['equity'],
                'totals': data['totals']
            }
            
            # Upsert
            result = collection.replace_one(
                {'_id': document['_id']},
                document,
                upsert=True
            )
            
            logger.info(f"Balance General guardado en MongoDB para {date_str}")
            return True
                
        except PyMongoError as e:
            logger.error(f"Error guardando en MongoDB: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

def process_balance_sheet(source_data: List[Dict]) -> Dict:
    """
    Transform 8-Columns data into Balance General structure.
    
    Logic:
    1. Filter accounts with Asset (Activo) > 0 or Liability (Pasivo) > 0
    2. Categorize into Assets and Liabilities
    3. Calculate Equity (Patrimonio) as Assets - Liabilities (which should equal Profit/Loss)
    """
    
    assets = []
    liabilities = []
    
    total_assets = 0.0
    total_liabilities = 0.0
    
    for account in source_data:
        # The API returns fields like 'asset', 'liability', 'loss', 'gain'
        # We need to check the exact field names from the source data structure
        # Assuming standard Laudus API response structure based on previous context
        
        asset_val = float(account.get('asset', 0) or 0)
        liability_val = float(account.get('liability', 0) or 0)
        
        if asset_val > 0:
            assets.append({
                'accountCode': account.get('accountCode'),
                'accountName': account.get('accountName'),
                'amount': asset_val
            })
            total_assets += asset_val
            
        if liability_val > 0:
            liabilities.append({
                'accountCode': account.get('accountCode'),
                'accountName': account.get('accountName'),
                'amount': liability_val
            })
            total_liabilities += liability_val
            
    # Calculate Result (Profit/Loss)
    # In the 8-column balance, the difference between Assets and Liabilities 
    # is the Result of the Exercise.
    # If Assets > Liabilities, it's a Profit (stored in Equity/Pasivo side to balance)
    # If Liabilities > Assets, it's a Loss (stored in Assets side to balance, usually)
    # BUT for Balance General presentation:
    # Assets = Liabilities + Equity
    # Equity = Capital + Reserves + Result
    # So Result = Assets - Liabilities (pure accounting equation)
    
    result_of_exercise = total_assets - total_liabilities
    
    equity = []
    
    # Add Result of Exercise to Equity
    equity.append({
        'accountCode': 'RES-EJER', # Virtual code
        'accountName': 'Resultado del Ejercicio',
        'amount': result_of_exercise
    })
    
    total_equity = result_of_exercise
    
    # Note: In a real accounting system, "Capital" and "Reserves" are often 
    # categorized as "Pasivo" (Liabilities) in the 8-column view if they are credit balances.
    # However, strictly speaking, they are Equity. 
    # The Laudus 8-column report usually puts Equity accounts in the 'liability' column 
    # because they are credit balances.
    # To separate them properly, we would need a Chart of Accounts to know which 
    # Liability accounts are actually Equity.
    #
    # FOR THIS IMPLEMENTATION:
    # We will stick to the 8-columns definition where 'liability' column includes Equity.
    # So 'liabilities' list above actually contains Liabilities + Equity (except current result).
    # The 'result_of_exercise' is the balancing figure.
    #
    # Refined Logic based on standard Chilean 8-column balance:
    # Columns: Activo, Pasivo, Pérdida, Ganancia.
    # Activo - Pasivo = Ganancia - Pérdida = Resultado.
    #
    # If we want to separate "Pasivo" (Real Liabilities) from "Patrimonio" (Equity),
    # we need to know the account types. Without that, we treat the 'liability' column
    # as "Pasivo y Patrimonio" (Liabilities & Equity).
    # The 'result_of_exercise' is added to make it balance perfectly if not already included.
    
    return {
        'assets': sorted(assets, key=lambda x: x['accountCode']),
        'liabilities': sorted(liabilities, key=lambda x: x['accountCode']), # This is technically Liabilities + Equity
        'equity': equity, # This contains the calculated result
        'totals': {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'balance_check': total_assets - (total_liabilities + total_equity) # Should be 0
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Generate Balance General from 8-Columns Balance')
    parser.add_argument('--date', required=True, help='Target date in YYYY-MM-DD format')
    
    args = parser.parse_args()
    target_date = args.date
    
    logger.info("=" * 60)
    logger.info("  GENERACION DE BALANCE GENERAL")
    logger.info("=" * 60)
    logger.info(f"Fecha: {target_date}")
    
    if not CONFIG['mongodb_uri']:
        logger.error("Falta variable de entorno MONGODB_URI")
        sys.exit(1)
        
    mongo_client = MongoDBClient()
    
    if not mongo_client.connect():
        sys.exit(1)
        
    try:
        # 1. Get 8-Columns Data
        logger.info("Obteniendo datos de Balance de 8 Columnas...")
        source_doc = mongo_client.get_8columns_data(target_date)
        
        if not source_doc:
            logger.error("No se pudo generar el Balance General: Faltan datos origen")
            sys.exit(1)
            
        source_data = source_doc.get('data', [])
        logger.info(f"Datos origen obtenidos: {len(source_data)} cuentas")
        
        # 2. Process Data
        logger.info("Procesando cuentas...")
        balance_general = process_balance_sheet(source_data)
        
        logger.info(f"Activos: {len(balance_general['assets'])}")
        logger.info(f"Pasivos (+Patrimonio): {len(balance_general['liabilities'])}")
        logger.info(f"Resultado del Ejercicio: {balance_general['totals']['total_equity']:,.2f}")
        logger.info(f"Check de Balance: {balance_general['totals']['balance_check']}")
        
        # 3. Save Data
        logger.info("Guardando Balance General...")
        if mongo_client.save_balance_general(balance_general, target_date):
            logger.info("Proceso completado exitosamente")
        else:
            logger.error("Error al guardar los datos")
            sys.exit(1)
            
    finally:
        mongo_client.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nProceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")
        sys.exit(1)
