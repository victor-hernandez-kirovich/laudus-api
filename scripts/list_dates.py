
import os
from pymongo import MongoClient

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri)
db = client[os.getenv('MONGODB_DATABASE', 'laudus_data')]
collection = db['balance_8columns']

dates = collection.distinct('date')
print("Available dates:", dates)
