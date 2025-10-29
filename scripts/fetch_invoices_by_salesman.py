#!/usr/bin/env python3
"""
Script para obtener datos de facturas por vendedor desde la API de Laudus
y almacenarlos en MongoDB.

Uso:
    python fetch_invoices_by_salesman.py --start-year 2024 --start-month 1 --end-year 2024 --end-month 12

Variables de entorno requeridas:
    MONGODB_URI: URI de conexión a MongoDB
    MONGODB_DATABASE: Nombre de la base de datos
"""

import requests
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
import calendar
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Configuración de la API Laudus
LAUDUS_API_BASE = os.getenv('LAUDUS_API_URL', 'https://api.laudus.cl')
LAUDUS_USERNAME = os.getenv('LAUDUS_USERNAME', 'API')
LAUDUS_PASSWORD = os.getenv('LAUDUS_PASSWORD', 'api123')
LAUDUS_COMPANY_VAT_ID = os.getenv('LAUDUS_COMPANY_VAT', '77548834-4')

# Diccionario de nombres de meses en español
MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre"
}


class LaudusAPIClient:
    """Cliente para interactuar con la API de Laudus"""
    
    def __init__(self, base_url: str, username: str, password: str, company_vat_id: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.company_vat_id = company_vat_id
        self.session = requests.Session()
        self.token = None
    
    def authenticate(self) -> bool:
        """Autenticar con la API y obtener token JWT"""
        auth_url = f"{self.base_url}/security/login"
        payload = {
            "userName": self.username,
            "password": self.password,
            "companyVATId": self.company_vat_id
        }
        
        try:
            print(f"Autenticando con Laudus API...")
            response = self.session.post(auth_url, json=payload, timeout=30)
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
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
            print("✓ Autenticación exitosa")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error en autenticación: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response status: {e.response.status_code}")
                print(f"  Response text: {e.response.text}")
            return False
    
    def get_invoices_by_salesman(self, date_from: str, date_to: str) -> Optional[List[Dict[str, Any]]]:
        """
        Obtener facturas agrupadas por vendedor
        
        Args:
            date_from: Fecha inicial en formato ISO (YYYY-MM-DD)
            date_to: Fecha final en formato ISO (YYYY-MM-DD)
            
        Returns:
            Lista de diccionarios con datos de vendedores o None si falla
        """
        endpoint = f"{self.base_url}/reports/sales/invoices/bySalesman"
        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }
        
        try:
            print(f"  Consultando facturas por vendedor: {date_from} a {date_to}")
            response = self.session.get(endpoint, params=params, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            print(f"  ✓ Recibidos {len(data)} vendedores")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error al obtener datos: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response status: {e.response.status_code}")
                print(f"  Response text: {e.response.text[:200]}")
            return None


class MongoDBHandler:
    """Manejador para operaciones con MongoDB"""
    
    def __init__(self, uri: str, database: str):
        self.uri = uri
        self.database_name = database
        self.client = None
        self.db = None
    
    def connect(self) -> bool:
        """Conectar a MongoDB"""
        try:
            print(f"Conectando a MongoDB...")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Verificar conexión
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            print(f"✓ Conectado a base de datos: {self.database_name}")
            return True
            
        except ConnectionFailure as e:
            print(f"✗ Error de conexión a MongoDB: {e}")
            return False
    
    def close(self):
        """Cerrar conexión a MongoDB"""
        if self.client:
            self.client.close()
            print("✓ Conexión a MongoDB cerrada")
    
    def save_salesman_invoices(
        self, 
        salesmen_data: List[Dict[str, Any]], 
        year: int, 
        month: int,
        skip_existing: bool = False
    ) -> int:
        """
        Guardar datos de facturas por vendedor en MongoDB
        
        Args:
            salesmen_data: Lista de datos de vendedores
            year: Año
            month: Mes (1-12)
            skip_existing: Si es True, omite documentos existentes
            
        Returns:
            Número de documentos insertados
        """
        collection = self.db['invoices_by_salesman']
        month_str = f"{year}-{month:02d}"
        month_name = MONTH_NAMES.get(month, f"Mes {month}")
        
        # Calcular el neto total para los porcentajes
        total_net = sum(s.get('net', 0) for s in salesmen_data)
        
        inserted_count = 0
        
        for salesman in salesmen_data:
            # Crear copia para no modificar original
            salesman_copy = salesman.copy()
            
            # Manejar vendedor sin asignar (salesmanId o salesmanName null)
            if salesman_copy.get('salesmanId') is None or salesman_copy.get('salesmanName') is None:
                print(f"  ⚠ Vendedor sin asignar encontrado - asignando nombre 'Sin Vendedor Asignado'")
                salesman_copy['salesmanName'] = 'Sin Vendedor Asignado'
                if salesman_copy.get('salesmanId') is None:
                    salesman_copy['salesmanId'] = 0
            
            # Calcular netPercentage si viene en 0
            if salesman_copy.get('netPercentage', 0) == 0 and total_net > 0:
                net_percentage = (salesman_copy.get('net', 0) / total_net) * 100
                salesman_copy['netPercentage'] = net_percentage
            
            # Calcular marginPercentage si viene en 0
            if salesman_copy.get('marginPercentage', 0) == 0 and salesman_copy.get('net', 0) > 0:
                margin_percentage = (salesman_copy.get('margin', 0) / salesman_copy.get('net', 1)) * 100
                salesman_copy['marginPercentage'] = margin_percentage
            
            # Agregar campos de contexto temporal
            salesman_copy['month'] = month_str
            salesman_copy['year'] = year
            salesman_copy['monthNumber'] = month
            salesman_copy['monthName'] = month_name
            salesman_copy['insertedAt'] = datetime.utcnow().isoformat()
            
            # Guardar datos originales completos
            salesman_copy['rawData'] = salesman
            
            # Verificar si ya existe
            existing = collection.find_one({
                'month': month_str,
                'salesmanId': salesman_copy['salesmanId']
            })
            
            if existing:
                if skip_existing:
                    print(f"  ⊘ Omitiendo vendedor existente: {salesman_copy['salesmanName']} ({month_str})")
                    continue
                else:
                    # Actualizar documento existente
                    collection.update_one(
                        {'_id': existing['_id']},
                        {'$set': salesman_copy}
                    )
                    print(f"  ↻ Actualizado: {salesman_copy['salesmanName']} ({month_str})")
            else:
                # Insertar nuevo documento
                collection.insert_one(salesman_copy)
                print(f"  ✓ Insertado: {salesman_copy['salesmanName']} ({month_str})")
                inserted_count += 1
        
        return inserted_count


def parse_arguments():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Obtener facturas por vendedor de Laudus API y guardar en MongoDB'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        required=True,
        help='Año inicial (ej: 2024)'
    )
    parser.add_argument(
        '--start-month',
        type=int,
        required=True,
        choices=range(1, 13),
        help='Mes inicial (1-12)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        required=True,
        help='Año final (ej: 2024)'
    )
    parser.add_argument(
        '--end-month',
        type=int,
        required=True,
        choices=range(1, 13),
        help='Mes final (1-12)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Omitir documentos que ya existen en MongoDB'
    )
    
    return parser.parse_args()


def generate_month_ranges(start_year: int, start_month: int, end_year: int, end_month: int):
    """
    Generar rangos de fechas para cada mes entre start y end
    
    Yields:
        Tuplas de (year, month, date_from, date_to)
    """
    current_year = start_year
    current_month = start_month
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        # Primer día del mes
        first_day = datetime(current_year, current_month, 1)
        
        # Último día del mes
        last_day_num = calendar.monthrange(current_year, current_month)[1]
        last_day = datetime(current_year, current_month, last_day_num)
        
        # Formato ISO para las fechas
        date_from = first_day.strftime('%Y-%m-%d')
        date_to = last_day.strftime('%Y-%m-%d')
        
        yield (current_year, current_month, date_from, date_to)
        
        # Avanzar al siguiente mes
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1


def main():
    """Función principal"""
    # Parsear argumentos
    args = parse_arguments()
    
    # Obtener credenciales de MongoDB desde variables de entorno
    mongodb_uri = os.getenv('MONGODB_URI')
    mongodb_database = os.getenv('MONGODB_DATABASE')
    
    if not mongodb_uri or not mongodb_database:
        print("✗ Error: Variables de entorno MONGODB_URI y MONGODB_DATABASE requeridas")
        sys.exit(1)
    
    print("=" * 80)
    print("LAUDUS - FACTURAS POR VENDEDOR")
    print("=" * 80)
    print(f"Período: {MONTH_NAMES[args.start_month]} {args.start_year} → {MONTH_NAMES[args.end_month]} {args.end_year}")
    print(f"Omitir existentes: {'Sí' if args.skip_existing else 'No'}")
    print("=" * 80)
    
    # Inicializar cliente de API
    api_client = LaudusAPIClient(
        LAUDUS_API_BASE,
        LAUDUS_USERNAME,
        LAUDUS_PASSWORD,
        LAUDUS_COMPANY_VAT_ID
    )
    
    # Autenticar
    if not api_client.authenticate():
        sys.exit(1)
    
    # Conectar a MongoDB
    db_handler = MongoDBHandler(mongodb_uri, mongodb_database)
    if not db_handler.connect():
        sys.exit(1)
    
    # Procesar cada mes
    total_inserted = 0
    total_months = 0
    
    try:
        for year, month, date_from, date_to in generate_month_ranges(
            args.start_year, args.start_month, args.end_year, args.end_month
        ):
            print(f"\n📅 Procesando {MONTH_NAMES[month]} {year}")
            print("-" * 80)
            
            # Obtener datos de la API
            salesmen_data = api_client.get_invoices_by_salesman(date_from, date_to)
            
            if salesmen_data is None:
                print(f"  ⚠ Saltando {MONTH_NAMES[month]} {year} - error en API")
                continue
            
            if len(salesmen_data) == 0:
                print(f"  ⚠ No hay datos para {MONTH_NAMES[month]} {year}")
                continue
            
            # Guardar en MongoDB
            inserted = db_handler.save_salesman_invoices(
                salesmen_data,
                year,
                month,
                args.skip_existing
            )
            
            total_inserted += inserted
            total_months += 1
            
            print(f"  📊 Resumen: {inserted} vendedores nuevos insertados")
    
    except KeyboardInterrupt:
        print("\n\n⚠ Proceso interrumpido por usuario")
    
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cerrar conexiones
        db_handler.close()
        
        # Resumen final
        print("\n" + "=" * 80)
        print("RESUMEN FINAL")
        print("=" * 80)
        print(f"Meses procesados: {total_months}")
        print(f"Vendedores insertados: {total_inserted}")
        print("=" * 80)


if __name__ == "__main__":
    main()
