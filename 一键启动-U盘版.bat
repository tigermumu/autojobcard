@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 飞机方案处理系统 - U盘便携版
echo ====================================
echo.

REM 检测 U 盘盘符
set USB_DRIVE=%~d0
echo [提示] U 盘盘符: %USB_DRIVE%
echo [提示] 项目目录: %~dp0
echo.

REM 检查 Python 和 Node.js
echo [提示] 检查运行环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先安装 Python 3.9+ 或配置便携版
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js
    echo 请先安装 Node.js 16+ 或配置便携版
    pause
    exit /b 1
)

echo [OK] 运行环境检查通过
echo.

REM 启动后端（新窗口）
echo [提示] 启动后端服务...
start "后端服务 - U盘便携版" cmd /k "%~dp0启动后端-U盘便携版.bat"

REM 等待后端启动
echo [提示] 等待后端服务启动（10秒）...
timeout /t 10 /nobreak >nul

REM 启动前端（新窗口）
echo [提示] 启动前端服务...
start "前端服务 - U盘便携版" cmd /k "%~dp0启动前端-U盘便携版.bat"

echo.
echo ====================================
echo 启动完成！
echo ====================================
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:3000
echo.
echo [提示] 两个服务窗口已打开
echo [提示] 关闭窗口即可停止服务
echo.
echo [重要] 数据完全存储在 U 盘
echo 数据库文件: %~dp0backend\aircraft_workcard.db
echo.
echo 按任意键退出此窗口（服务将继续运行）
pause >nul






