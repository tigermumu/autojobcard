@echo off
cd /d %~dp0frontend

echo ====================================
echo Aircraft Workcard System Frontend
echo ====================================
echo.

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js 16+
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist node_modules (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo ====================================
echo Starting Frontend Dev Server...
echo ====================================
echo URL: http://localhost:3000
echo API: http://localhost:8000
echo.
echo Make sure backend is running
echo Press Ctrl+C to stop the server
echo ====================================
echo.

call npm run dev

if errorlevel 1 (
    echo.
    echo ERROR: Server failed to start
    pause
)

