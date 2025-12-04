@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd backend

echo ====================================
echo 启动后端服务（U盘 SQLite 版本）
echo ====================================
echo.

REM 检测 U 盘盘符
set USB_DRIVE=%~d0
echo [提示] U 盘盘符: %USB_DRIVE%
echo [提示] 项目目录: %~dp0
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo.
    echo 请确保：
    echo 1. 已安装 Python 3.9+ 并添加到 PATH
    echo 2. 或使用便携版 Python（修改 配置环境.bat）
    echo.
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist .env (
    echo [提示] 创建 .env 文件...
    if exist env.example (
        copy env.example .env >nul
        echo [提示] 已从 env.example 创建 .env 文件
    ) else (
        echo [错误] env.example 文件不存在
        pause
        exit /b 1
    )
)

REM 确保使用 SQLite（相对路径）
echo [提示] 配置 SQLite 数据库...
powershell -Command "(Get-Content .env) -replace 'DATABASE_URL=.*', 'DATABASE_URL=sqlite:///./aircraft_workcard.db' | Set-Content .env.tmp; Move-Item -Force .env.tmp .env" >nul 2>&1
findstr /C:"DATABASE_URL" .env >nul
if errorlevel 1 (
    echo DATABASE_URL=sqlite:///./aircraft_workcard.db >> .env
)

REM 创建虚拟环境（如果不存在）
if not exist venv (
    echo [提示] 创建 Python 虚拟环境（首次运行，可能需要几分钟）...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        echo.
        echo 可能的原因：
        echo 1. Python 版本过低（需要 3.9+）
        echo 2. 磁盘空间不足
        echo 3. U 盘权限问题
        echo.
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

REM 安装依赖（如果未安装）
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [提示] 安装 Python 依赖（首次运行，可能需要 5-10 分钟）...
    echo [提示] 如果网络较慢，可以使用国内镜像：
    echo   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        echo.
        echo 尝试使用默认源...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [错误] 依赖安装失败，请检查网络连接
            pause
            exit /b 1
        )
    )
    echo [提示] 依赖安装完成！
)

REM 运行数据库迁移（SQLite）
echo.
echo [提示] 运行数据库迁移...
python -m alembic upgrade head
if errorlevel 1 (
    echo [警告] 数据库迁移可能失败，但继续启动...
    echo 如果是首次运行，这是正常的
)

echo.
echo ====================================
echo 启动后端 API 服务器...
echo ====================================
echo.
echo U 盘盘符: %USB_DRIVE%
echo 数据库文件: %~dp0backend\aircraft_workcard.db
echo.
echo API地址: http://localhost:8000
echo API文档: http://localhost:8000/api/v1/docs
echo 健康检查: http://localhost:8000/health
echo.
echo [重要] 数据完全存储在 U 盘，可随时带走
echo.
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo [错误] 服务器启动失败
    echo.
    echo 可能的原因：
    echo 1. 端口 8000 被占用
    echo 2. 数据库连接失败
    echo 3. 环境变量配置错误
    echo.
    pause
)






