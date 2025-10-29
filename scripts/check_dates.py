#!/usr/bin/env python3
"""
Script para verificar las fechas disponibles en MongoDB
"""
import os
from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict

# Configuración
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = 'laudus_data'

def main():
    # Conectar a MongoDB
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    
    # Colecciones a revisar
    collections = ['balance_totals', 'balance_standard', 'balance_8columns']
    
    print("=" * 80)
    print("FECHAS DISPONIBLES EN MONGODB - LAUDUS DATA")
    print("=" * 80)
    print()
    
    # Diccionario para agrupar fechas
    all_dates = defaultdict(lambda: {'totals': False, 'standard': False, '8columns': False})
    
    # Revisar cada colección
    for collection_name in collections:
        collection = db[collection_name]
        
        # Obtener todas las fechas únicas
        dates = collection.distinct('date')
        dates.sort()
        
        # Mapear nombre de colección
        key_name = collection_name.replace('balance_', '')
        
        # Marcar fechas disponibles
        for date in dates:
            all_dates[date][key_name] = True
    
    # Ordenar fechas
    sorted_dates = sorted(all_dates.keys())
    
    if not sorted_dates:
        print("⚠️  No hay fechas disponibles en la base de datos")
        return
    
    # Imprimir tabla
    print(f"Total de fechas únicas: {len(sorted_dates)}")
    print(f"Rango: {sorted_dates[0]} → {sorted_dates[-1]}")
    print()
    print("┌────────────┬─────────┬──────────┬───────────┬────────┐")
    print("│   Fecha    │ Totals  │ Standard │ 8 Columns │ Status │")
    print("├────────────┼─────────┼──────────┼───────────┼────────┤")
    
    for date in sorted_dates:
        totals = '✓' if all_dates[date]['totals'] else '✗'
        standard = '✓' if all_dates[date]['standard'] else '✗'
        columns8 = '✓' if all_dates[date]['8columns'] else '✗'
        
        # Status: Completo si tiene los 3, Parcial si tiene algunos, Vacío si no tiene ninguno
        count = sum([all_dates[date]['totals'], all_dates[date]['standard'], all_dates[date]['8columns']])
        if count == 3:
            status = '✅'
        elif count > 0:
            status = '⚠️ '
        else:
            status = '❌'
        
        print(f"│ {date} │    {totals}    │    {standard}     │     {columns8}     │   {status}   │")
    
    print("└────────────┴─────────┴──────────┴───────────┴────────┘")
    print()
    
    # Estadísticas
    complete = sum(1 for date in all_dates.values() if all(date.values()))
    partial = sum(1 for date in all_dates.values() if any(date.values()) and not all(date.values()))
    
    print("RESUMEN:")
    print(f"  ✅ Fechas completas (3/3 colecciones): {complete}")
    print(f"  ⚠️  Fechas parciales (1-2 colecciones): {partial}")
    print(f"  📊 Total de fechas: {len(sorted_dates)}")
    print()
    
    # Detectar gaps (fechas faltantes)
    if len(sorted_dates) >= 2:
        from datetime import datetime, timedelta
        
        start_date = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
        end_date = datetime.strptime(sorted_dates[-1], '%Y-%m-%d')
        
        expected_dates = []
        current = start_date
        while current <= end_date:
            expected_dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        missing_dates = set(expected_dates) - set(sorted_dates)
        
        if missing_dates:
            missing_sorted = sorted(missing_dates)
            print(f"⚠️  GAPS DETECTADOS: {len(missing_dates)} fechas faltantes")
            print(f"   Primera faltante: {missing_sorted[0]}")
            print(f"   Última faltante: {missing_sorted[-1]}")
        else:
            print("✅ No hay gaps - Todas las fechas están presentes en el rango")
    
    print()
    print("=" * 80)
    
    client.close()

if __name__ == '__main__':
    main()
