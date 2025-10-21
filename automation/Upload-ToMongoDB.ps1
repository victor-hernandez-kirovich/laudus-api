# Upload-ToMongoDB.ps1
# Script para subir datos JSON a MongoDB Atlas usando pymongo

param(
    [Parameter(Mandatory=$true)]
    [string]$JsonFile,
    
    [Parameter(Mandatory=$true)]
    [string]$Collection
)

$config = Get-Content "$PSScriptRoot\config.json" | ConvertFrom-Json

# Convertir a ruta absoluta y escapar backslashes
$JsonFileAbsolute = (Resolve-Path $JsonFile).Path -replace '\\', '\\'

# Verificar si Python esta instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python detectado: $pythonVersion" -ForegroundColor Green
    
    # Crear script Python temporal
    $pythonScript = @"
import json
import sys
from pymongo import MongoClient

try:
    # Conectar a MongoDB
    client = MongoClient('$($config.mongodb.connectionString)')
    db = client['$($config.mongodb.database)']
    collection = db['$Collection']
    
    # Leer archivo JSON (con manejo de BOM)
    with open(r'$JsonFileAbsolute', 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    # Insertar documento (replace si existe)
    result = collection.replace_one(
        {'_id': data['_id']},
        data,
        upsert=True
    )
    
    print(f'SUCCESS: Documento insertado/actualizado en {collection.name}')
    print(f'ID: {data["_id"]}')
    print(f'Registros: {data["recordCount"]}')
    
except ImportError:
    print('ERROR: pymongo no instalado. Ejecutar: pip install pymongo')
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {str(e)}')
    sys.exit(1)
"@

    $tempPyFile = [System.IO.Path]::GetTempFileName() + ".py"
    $pythonScript | Out-File -FilePath $tempPyFile -Encoding UTF8
    
    # Ejecutar script Python
    Write-Host "Subiendo a MongoDB..." -ForegroundColor Yellow
    $result = python $tempPyFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $result -ForegroundColor Green
    } else {
        Write-Host $result -ForegroundColor Red
        
        if ($result -like "*pymongo no instalado*") {
            Write-Host ""
            Write-Host "Para instalar pymongo, ejecuta:" -ForegroundColor Yellow
            Write-Host "  pip install pymongo" -ForegroundColor White
        }
    }
    
    Remove-Item $tempPyFile -Force
}
catch {
    Write-Host "Python no esta instalado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Opciones:" -ForegroundColor Yellow
    Write-Host "1. Instalar Python: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "2. Instalar MongoDB Tools: https://www.mongodb.com/try/download/database-tools" -ForegroundColor White
    Write-Host "3. Subir manualmente usando MongoDB Compass o mongosh" -ForegroundColor White
}
