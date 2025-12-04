@echo off
cd /d %~dp0

REM ========================================================
REM CONFIG: Force use of USB Python Interpreter
REM ========================================================
set "USB_PYTHON=F:\WPy64-31150\python-3.11.5.amd64\python.exe"
set "USB_PYTHON_DIR=F:\WPy64-31150\python-3.11.5.amd64"

REM Validate interpreter existence
if not exist "%USB_PYTHON%" (
    echo [ERROR] USB Python environment not found
    echo Path: %USB_PYTHON%
    echo Please confirm python.exe exists at this path.
    pause
    exit /b 1
)

echo [INFO] Using USB Python environment: %USB_PYTHON%

REM Start Redis Server
if exist "%~dp0redis\redis-server.exe" (
    echo [INFO] Starting Redis Server...
    pushd "%~dp0redis"
    start "Redis" redis-server.exe redis.windows.conf
    popd
) else (
    echo [WARNING] Redis server not found in %~dp0redis
)

REM Set temporary PATH to ensure pip and other tools use this environment
set "PATH=%USB_PYTHON_DIR%;%USB_PYTHON_DIR%\Scripts;%PATH%"

cd backend

echo ====================================
echo Starting Backend Service (USB Portable)
echo ====================================
echo.

REM Detect USB Drive Letter
set USB_DRIVE=%~d0
echo [INFO] USB Drive: %USB_DRIVE%
echo [INFO] Project Dir: %~dp0
echo.

REM Check .env file
if not exist .env (
    echo [INFO] Creating .env file...
    if exist env.example (
        copy env.example .env >nul
        echo [INFO] Created .env from env.example
    ) else (
        echo [ERROR] env.example file not found
        pause
        exit /b 1
    )
)

REM Ensure SQLite usage (relative path)
echo [INFO] Configuring SQLite database...
REM Use USB Python to modify .env
"%USB_PYTHON%" -c "import re; c=open('.env',encoding='utf-8').read(); c=re.sub(r'DATABASE_URL=.*', 'DATABASE_URL=sqlite:///./aircraft_workcard.db', c); open('.env','w',encoding='utf-8').write(c)"

REM Install dependencies (if not installed)
"%USB_PYTHON%" -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing Python dependencies...
    echo   pip install -r requirements.txt
    "%USB_PYTHON%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed
        pause
        exit /b 1
    )
)

REM Run Database Migrations
echo.
echo [INFO] Running database migrations...
"%USB_PYTHON%" -m alembic upgrade head

echo.
echo ====================================
echo Starting Backend API Server...
echo ====================================
echo.
echo API URL: http://localhost:8000
echo.
echo [IMPORTANT] Data is stored on USB stick, portable.
echo.
echo Press Ctrl+C to stop server
echo ====================================
echo.

REM Start using uvicorn via Python script
"%USB_PYTHON%" -c "import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=True)"

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start
    pause
)
