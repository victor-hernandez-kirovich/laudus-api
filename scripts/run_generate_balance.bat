@echo off
REM Script para ejecutar la generación del Balance General
REM Uso: run_generate_balance.bat YYYY-MM-DD

if "%1"=="" (
    echo Error: Debe proporcionar una fecha en formato YYYY-MM-DD
    echo Ejemplo: run_generate_balance.bat 2025-07-31
    exit /b 1
)

REM Cargar variables de entorno desde el archivo .env del dashboard
REM (que contiene MONGODB_URI)
set ENV_FILE=..\..\laudus-dashboard\.env.local

if not exist "%ENV_FILE%" (
    echo Error: No se encuentra el archivo .env.local en laudus-dashboard
    echo Asegurate de que exista y contenga MONGODB_URI
    exit /b 1
)

REM Leer MONGODB_URI del archivo .env.local
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    if "%%a"=="MONGODB_URI" set MONGODB_URI=%%b
    if "%%a"=="MONGODB_DATABASE" set MONGODB_DATABASE=%%b
)

if "%MONGODB_URI%"=="" (
    echo Error: MONGODB_URI no encontrado en .env.local
    exit /b 1
)

echo Generando Balance General para fecha: %1
echo.
python generate_balance_general.py --date %1
