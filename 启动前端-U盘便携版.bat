@echo off
cd /d %~dp0

REM ========================================================
REM CONFIG: Force use of USB Node.js path
REM ========================================================
set "USB_NODE=F:\nodejs\node.exe"
set "USB_NODE_DIR=F:\nodejs"

REM Validate Node.js existence
if not exist "%USB_NODE%" (
    echo [ERROR] USB Node.js environment not found
    echo Path: %USB_NODE%
    echo Please confirm node.exe exists at this path.
    pause
    exit /b 1
)

echo [INFO] Using USB Node.js environment: %USB_NODE%

REM Set temporary PATH to ensure npm and other tools use this environment
set "PATH=%USB_NODE_DIR%;%PATH%"

cd frontend

echo ====================================
echo Starting Frontend Service (USB Portable)
echo ====================================
echo.

REM Detect USB Drive Letter
set USB_DRIVE=%~d0
echo [INFO] USB Drive: %USB_DRIVE%
echo [INFO] Project Dir: %~dp0
echo.

REM Check if backend is running skipped


REM Install dependencies (if not installed)
if not exist node_modules (
    echo [INFO] Installing Node.js dependencies - First run, may take 5-10 mins...
    echo [INFO] Using registry mirror if slow:
    echo   npm install --registry=https://registry.npmmirror.com
    echo.
    call npm install --registry=https://registry.npmmirror.com
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed
        echo.
        echo Trying default registry...
        call npm install
        if errorlevel 1 (
            echo [ERROR] Dependency installation failed, check network.
            pause
            exit /b 1
        )
    )
    echo [INFO] Dependencies installed!
)

echo.
echo ====================================
echo Starting Frontend Development Server...
echo ====================================
echo.
echo USB Drive: %USB_DRIVE%
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo.
echo [IMPORTANT] Ensure backend is running
echo Press Ctrl+C to stop server
echo ====================================
echo.

REM Start using npm run dev
call npm run dev

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start
    echo.
    echo Possible reasons:
    echo 1. Port 3000 is occupied
    echo 2. Dependencies not installed correctly
    echo 3. Node.js version incompatible
    echo.
    pause
)
