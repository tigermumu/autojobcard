@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd frontend

echo ====================================
echo 启动前端服务
echo ====================================
echo.

REM 检查后端是否运行
echo [提示] 检查后端服务...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [警告] 后端服务可能未启动
    echo 请确保已运行"启动后端-便携版.bat"
    echo.
    timeout /t 3 >nul
)

REM 安装依赖（如果未安装）
if not exist node_modules (
    echo [提示] 安装 Node.js 依赖（这可能需要几分钟）...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        echo.
        echo 如果网络较慢，可以尝试：
        echo npm install --registry=https://registry.npmmirror.com
        pause
        exit /b 1
    )
)

REM 检查 API 配置
echo [提示] 检查 API 配置...
findstr /C:"localhost:8000" src\services\api.ts >nul
if errorlevel 1 (
    echo [提示] 前端 API 地址可能需要配置
    echo 请检查 src\services\api.ts 中的 API_BASE_URL
)

echo.
echo ====================================
echo 启动前端开发服务器...
echo ====================================
echo.
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




