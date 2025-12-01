@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd backend

echo ====================================
echo 启动后端服务（SQLite 版本）
echo ====================================
echo.

REM 检查 .env 文件
if not exist .env (
    echo [提示] 创建 .env 文件...
    if exist env.example (
        copy env.example .env >nul
        echo [提示] 已从 env.example 创建 .env 文件
        echo [重要] 请编辑 .env 文件，配置以下内容：
        echo   1. QWEN_API_KEY=你的API密钥
        echo   2. DATABASE_URL=sqlite:///./aircraft_workcard.db
        echo.
        timeout /t 3 >nul
    ) else (
        echo [错误] env.example 文件不存在
        pause
        exit /b 1
    )
)

REM 检查并设置 SQLite 数据库 URL
findstr /C:"DATABASE_URL" .env >nul
if errorlevel 1 (
    echo [提示] 添加 SQLite 数据库配置...
    echo DATABASE_URL=sqlite:///./aircraft_workcard.db >> .env
)

REM 创建虚拟环境（如果不存在）
if not exist venv (
    echo [提示] 创建 Python 虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
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
    echo [提示] 安装 Python 依赖（这可能需要几分钟）...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        echo 请检查网络连接或使用国内镜像源
        pause
        exit /b 1
    )
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
echo API地址: http://localhost:8000
echo API文档: http://localhost:8000/api/v1/docs
echo 健康检查: http://localhost:8000/health
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




