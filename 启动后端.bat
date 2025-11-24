@echo off
chcp 65001
cd /d %~dp0backend

echo ====================================
echo Aircraft Workcard System Backend
echo ====================================
echo.

docker-compose up -d postgres redis

REM Check Docker containers
docker ps --filter "name=demo3-postgres-1" --format "{{.Names}}" | findstr "demo3-postgres-1" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Database container not running
    echo Please run: docker-compose up -d postgres redis
    echo.
)

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM Check/create venv
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate venv
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install dependencies
echo Checking dependencies...
pip show uvicorn >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Check .env file
if not exist .env (
    echo Creating .env file...
    copy env.example .env >nul
)

echo.
echo ====================================
echo Starting Backend API Server...
echo ====================================
echo API: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ====================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo ERROR: Server failed to start
    echo Check: 1. Database running?  2. Port 8000 in use?
    pause
)

