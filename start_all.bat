@echo off
set "drive=%~d0"
title Aircraft Workcard System - Full Stack Startup
echo =======================================================
echo      Starting Aircraft Workcard System (Portable)
echo =======================================================

:: 1. Start Redis
echo [1/3] Checking Redis...
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo    - Redis is already running
) else (
    if exist "%drive%\Redis-x64-3.0.504\redis-server.exe" (
        echo    - Starting Redis from %drive%\Redis-x64-3.0.504...
        start "Redis Server" /MIN "%drive%\Redis-x64-3.0.504\redis-server.exe" "%drive%\Redis-x64-3.0.504\redis.windows.conf"
    ) else (
        if exist "redis\redis-server.exe" (
            echo    - Starting built-in portable Redis...
            start "Redis Server" /MIN "redis\redis-server.exe" redis.windows.conf
        ) else (
            echo    - [WARNING] Redis not found!
            echo    - Please ensure Redis is running at localhost:6379
        )
    )
)

:: 2. Start Backend
echo [2/3] Starting Backend Service...

set "FOUND_PYTHON=0"

if exist "%drive%\WPy64-31150\python-3.11.5.amd64\python.exe" (
    echo    - Using Python environment: %drive%\WPy64-31150\python-3.11.5.amd64
    set "PYTHON_EXE=%drive%\WPy64-31150\python-3.11.5.amd64\python.exe"
    set "FOUND_PYTHON=1"
    goto :python_found
)

if exist "backend\venv\Scripts\python.exe" (
    echo    - Using built-in virtual environment: backend\venv
    set "PYTHON_EXE=backend\venv\Scripts\python.exe"
    set "FOUND_PYTHON=1"
    goto :python_found
)

if "%FOUND_PYTHON%"=="0" (
    echo    - [ERROR] Python environment not found!
    echo    - Please confirm %drive%\WPy64-31150\python-3.11.5.amd64\python.exe exists.
    pause
    exit /b 1
)

:python_found
cd backend
set "DATABASE_URL=sqlite:///./aircraft_workcard.db"
echo    - Using DATABASE_URL=%DATABASE_URL%
echo    - Validating SQLite database file...
call "%PYTHON_EXE%" scripts\validate_sqlite.py
echo    - Checking database migrations...
:: Try running alembic, ignore if command not found (non-fatal)
call "%PYTHON_EXE%" -m alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo    - [WARNING] Database migration failed, attempting to stamp current head...
    call "%PYTHON_EXE%" -m alembic stamp head
)

echo    - Starting API Service (Port 8000)...
start "Backend API" /MIN "%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd ..

:: 3. Start Frontend
echo [3/3] Starting Frontend Service...
:: Set Node.js environment variables
set "PATH=%drive%\nodejs;%PATH%"

cd frontend
echo    - Node.js Version:
call node -v
echo    - NPM Version:
call npm -v

if not exist "node_modules" (
    echo    - [INFO] First time startup, installing frontend dependencies -this may take a few minutes-...
    call npm install --registry=https://registry.npmmirror.com
)

echo    - Starting Frontend Development Server...
:: Use cmd /k to keep window open for error inspection
start "Frontend" cmd /k "npm run dev"

echo =======================================================
echo    System Startup Complete!
echo    Backend API: http://localhost:8000/docs
echo    Frontend: http://localhost:5173 (Wait for browser to open automatically)
echo =======================================================
pause
