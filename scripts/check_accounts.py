from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['laudus_data']

# Obtener último balance
docs = list(db.balance_8columns.find({}).sort('date', -1).limit(1))

if docs:
    print('\n=== ÚLTIMAS CUENTAS DEL BALANCE ===\n')
    doc = docs[0]
    print(f"Fecha: {doc.get('date', 'N/A')}\n")
    
    if 'data' in doc:
        # Filtrar solo cuentas que comienzan con 11 (Activo Corriente)
        for item in doc['data'][:30]:
            acc_num = item.get('accountNumber', '')
            acc_name = item.get('accountName', '')
            assets = item.get('assets', 0)
            
            if str(acc_num).startswith('11'):
                print(f"{acc_num:15} | {acc_name:40} | {assets:>15,.2f}")
else:
    print("No se encontraron balances")
