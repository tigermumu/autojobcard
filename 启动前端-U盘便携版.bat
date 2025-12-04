@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd frontend

echo ====================================
echo 启动前端服务（U盘便携版）
echo ====================================
echo.

REM 检测 U 盘盘符
set USB_DRIVE=%~d0
echo [提示] U 盘盘符: %USB_DRIVE%
echo [提示] 项目目录: %~dp0
echo.

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js
    echo.
    echo 请确保：
    echo 1. 已安装 Node.js 16+ 并添加到 PATH
    echo 2. 或使用便携版 Node.js（修改 配置环境.bat）
    echo.
    pause
    exit /b 1
)

REM 检查后端是否运行
echo [提示] 检查后端服务...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [警告] 后端服务可能未启动
    echo 请确保已运行"启动后端-U盘便携版.bat"
    echo.
    timeout /t 3 >nul
)

REM 安装依赖（如果未安装）
if not exist node_modules (
    echo [提示] 安装 Node.js 依赖（首次运行，可能需要 5-10 分钟）...
    echo [提示] 如果网络较慢，可以使用国内镜像：
    echo   npm install --registry=https://registry.npmmirror.com
    echo.
    call npm install --registry=https://registry.npmmirror.com
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        echo.
        echo 尝试使用默认源...
        call npm install
        if errorlevel 1 (
            echo [错误] 依赖安装失败，请检查网络连接
            pause
            exit /b 1
        )
    )
    echo [提示] 依赖安装完成！
)

echo.
echo ====================================
echo 启动前端开发服务器...
echo ====================================
echo.
echo U 盘盘符: %USB_DRIVE%
echo 前端地址: http://localhost:3000
echo 后端 API: http://localhost:8000
echo.
echo [重要] 确保后端服务已启动
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.

call npm run dev

if errorlevel 1 (
    echo.
    echo [错误] 服务器启动失败
    echo.
    echo 可能的原因：
    echo 1. 端口 3000 被占用
    echo 2. 依赖未正确安装
    echo 3. Node.js 版本不兼容
    echo.
    pause
)






