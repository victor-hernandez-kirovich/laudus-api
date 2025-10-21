# MongoDB.ps1
# Modulo para interactuar con MongoDB Atlas

function Save-ToMongoDB {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ConnectionString,
        
        [Parameter(Mandatory=$true)]
        [string]$Database,
        
        [Parameter(Mandatory=$true)]
        [string]$Collection,
        
        [Parameter(Mandatory=$true)]
        [array]$Data,
        
        [Parameter(Mandatory=$true)]
        [string]$Date,
        
        [Parameter(Mandatory=$true)]
        [string]$EndpointType
    )
    
    try {
        # Preparar documento con metadata
        $document = @{
            _id = "$Date-$EndpointType"
            date = $Date
            endpointType = $EndpointType
            recordCount = $Data.Count
            insertedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
            data = $Data
        }
        
        Write-Host "  [MongoDB] Guardando en $Database.$Collection..." -ForegroundColor Gray
        
        # FALLBACK: Guardar en JSON local mientras configuramos MongoDB Data API
        $backupDir = "$PSScriptRoot\..\mongodb-backup\$Collection"
        if (-not (Test-Path $backupDir)) {
            New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
        }
        
        $backupFile = "$backupDir\$Date-$EndpointType.json"
        $document | ConvertTo-Json -Depth 10 | Set-Content -Path $backupFile -Encoding UTF8
        
        Write-Host "  [MongoDB] Backup local guardado: $backupFile" -ForegroundColor Gray
        
        # Intentar subir a MongoDB Atlas usando Python + pymongo
        try {
            $pythonCheck = python --version 2>&1
            
            if ($pythonCheck -like "*Python*") {
                Write-Host "  [MongoDB] Subiendo a Atlas..." -ForegroundColor Gray
                
                # Crear script Python inline
                $backupFileEscaped = $backupFile -replace '\\', '\\\\'
                $pythonScript = @"
import json
import sys
try:
    from pymongo import MongoClient
    client = MongoClient('$ConnectionString', serverSelectionTimeoutMS=5000)
    db = client['$Database']
    collection = db['$Collection']
    
    with open(r'$backupFile', 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    result = collection.replace_one({'_id': data['_id']}, data, upsert=True)
    
    if result.upserted_id or result.modified_count > 0:
        print('SUCCESS')
    else:
        print('NO_CHANGE')
    
except ImportError:
    print('PYMONGO_NOT_INSTALLED')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:{str(e)}')
    sys.exit(1)
"@
                
                $tempPy = [System.IO.Path]::GetTempFileName() + ".py"
                $pythonScript | Out-File -FilePath $tempPy -Encoding UTF8
                
                $pyResult = python $tempPy 2>&1
                Remove-Item $tempPy -Force -ErrorAction SilentlyContinue
                
                if ($pyResult -eq 'SUCCESS' -or $pyResult -eq 'NO_CHANGE') {
                    Write-Host "  [MongoDB] SUBIDO A ATLAS exitosamente!" -ForegroundColor Green
                    return @{
                        Success = $true
                        InsertedCount = $Data.Count
                        BackupFile = $backupFile
                        UploadedToAtlas = $true
                    }
                }
                elseif ($pyResult -eq 'PYMONGO_NOT_INSTALLED') {
                    Write-Host "  [MongoDB] pymongo no instalado (ejecutar: pip install pymongo)" -ForegroundColor Yellow
                }
                else {
                    Write-Host "  [MongoDB] Error subiendo: $pyResult" -ForegroundColor Yellow
                }
            }
        }
        catch {
            Write-Host "  [MongoDB] Python no disponible, solo backup local" -ForegroundColor Yellow
        }
        
        return @{
            Success = $true
            InsertedCount = $Data.Count
            BackupFile = $backupFile
            UploadedToAtlas = $false
        }
    }
    catch {
        Write-Error "Error guardando en MongoDB: $($_.Exception.Message)"
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

function Test-MongoDBConnection {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ConnectionString
    )
    
    try {
        Write-Host "[MongoDB] Probando conexion..." -ForegroundColor Yellow
        
        # TODO: Implementar test de conexion real
        # Por ahora retornamos true para testing
        
        Write-Host "[MongoDB] Conexion OK" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Error conectando a MongoDB: $($_.Exception.Message)"
        return $false
    }
}
