@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 验证 U 盘环境配置
echo ====================================
echo.

set ERRORS=0

REM 检测 U 盘盘符
set USB_DRIVE=%~d0
echo [1] U 盘盘符: %USB_DRIVE%
echo [1] 项目目录: %~dp0
echo.

REM 检查 Python
echo [2] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未找到
    set /a ERRORS+=1
) else (
    python --version
    echo [OK] Python 已找到
)
echo.

REM 检查 Node.js
echo [3] 检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Node.js 未找到
    set /a ERRORS+=1
) else (
    node --version
    echo [OK] Node.js 已找到
)
echo.

REM 检查后端目录
echo [4] 检查后端目录...
if not exist backend\app (
    echo [错误] backend\app 目录不存在
    set /a ERRORS+=1
) else (
    echo [OK] backend\app 目录存在
)

if not exist backend\requirements.txt (
    echo [错误] backend\requirements.txt 不存在
    set /a ERRORS+=1
) else (
    echo [OK] backend\requirements.txt 存在
)
echo.

REM 检查前端目录
echo [5] 检查前端目录...
if not exist frontend\src (
    echo [错误] frontend\src 目录不存在
    set /a ERRORS+=1
) else (
    echo [OK] frontend\src 目录存在
)

if not exist frontend\package.json (
    echo [错误] frontend\package.json 不存在
    set /a ERRORS+=1
) else (
    echo [OK] frontend\package.json 存在
)
echo.

REM 检查配置文件
echo [6] 检查配置文件...
if not exist backend\.env (
    echo [警告] backend\.env 不存在，将从 env.example 创建
    if exist backend\env.example (
        copy backend\env.example backend\.env >nul
        echo [提示] 已创建 .env 文件
    )
) else (
    echo [OK] backend\.env 存在
)

REM 检查 .env 中的数据库配置
findstr /C:"sqlite://" backend\.env >nul 2>&1
if errorlevel 1 (
    echo [警告] .env 中未配置 SQLite，正在修复...
    powershell -Command "(Get-Content backend\.env) -replace 'DATABASE_URL=.*', 'DATABASE_URL=sqlite:///./aircraft_workcard.db' | Set-Content backend\.env.tmp; Move-Item -Force backend\.env.tmp backend\.env" >nul 2>&1
    echo [提示] 已配置为 SQLite
) else (
    echo [OK] 数据库配置为 SQLite
)
echo.

REM 检查启动脚本
echo [7] 检查启动脚本...
if not exist "一键启动-U盘版.bat" (
    echo [错误] 一键启动-U盘版.bat 不存在
    set /a ERRORS+=1
) else (
    echo [OK] 一键启动-U盘版.bat 存在
)

if not exist "启动后端-U盘便携版.bat" (
    echo [错误] 启动后端-U盘便携版.bat 不存在
    set /a ERRORS+=1
) else (
    echo [OK] 启动后端-U盘便携版.bat 存在
)

if not exist "启动前端-U盘便携版.bat" (
    echo [错误] 启动前端-U盘便携版.bat 不存在
    set /a ERRORS+=1
) else (
    echo [OK] 启动前端-U盘便携版.bat 存在
)
echo.

REM 检查必要目录
echo [8] 检查必要目录...
if not exist backend\storage\import_logs (
    echo [提示] 创建 backend\storage\import_logs 目录...
    mkdir backend\storage\import_logs 2>nul
)

if not exist backend\uploads\index_files (
    echo [提示] 创建 backend\uploads\index_files 目录...
    mkdir backend\uploads\index_files 2>nul
)

echo [OK] 必要目录已创建
echo.

REM 总结
echo ====================================
echo 验证结果
echo ====================================
if %ERRORS%==0 (
    echo.
    echo [成功] 所有配置检查通过！
    echo.
    echo 可以运行: 一键启动-U盘版.bat
    echo.
) else (
    echo.
    echo [警告] 发现 %ERRORS% 个错误
    echo 请根据上述提示修复问题
    echo.
)

pause

