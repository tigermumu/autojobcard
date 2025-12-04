@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 启动后端服务（U盘 Docker + PostgreSQL 版本）
echo ====================================
echo.

REM 检测U盘盘符（当前脚本所在盘符）
set USB_DRIVE=%~d0
echo [提示] 检测到U盘盘符: %USB_DRIVE%
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker
    echo.
    echo ====================================
    echo Docker 安装说明
    echo ====================================
    echo.
    echo Docker Desktop 需要安装在系统上（不能完全便携）
    echo 但项目数据和配置都在 U 盘，可以带走！
    echo.
    echo 安装步骤：
    echo 1. 下载 Docker Desktop:
    echo    https://www.docker.com/products/docker-desktop
    echo.
    echo 2. 安装 Docker Desktop（需要管理员权限）
    echo    安装时间：约 5-10 分钟
    echo.
    echo 3. 安装完成后，重启电脑（首次安装需要）
    echo.
    echo 4. 启动 Docker Desktop，然后重新运行此脚本
    echo.
    echo ====================================
    echo.
    echo [提示] 如果不想安装 Docker，可以使用 SQLite 版本：
    echo   运行: 启动后端-便携版.bat
    echo.
    pause
    exit /b 1
)

echo [提示] Docker 已安装
docker --version
echo.

REM 创建数据目录（如果不存在）
if not exist docker_data\postgres (
    echo [提示] 创建 PostgreSQL 数据目录...
    mkdir docker_data\postgres 2>nul
)
if not exist docker_data\redis (
    echo [提示] 创建 Redis 数据目录...
    mkdir docker_data\redis 2>nul
)

REM 检查并拉取镜像（如果需要）
echo [提示] 检查 Docker 镜像...
docker images postgres:13 | findstr "postgres" >nul 2>&1
if errorlevel 1 (
    echo [提示] 首次运行，需要下载 PostgreSQL 镜像（约300MB）...
    echo 这可能需要几分钟，请耐心等待...
    docker pull postgres:13
    if errorlevel 1 (
        echo [错误] 镜像下载失败，请检查网络连接
        pause
        exit /b 1
    )
)

docker images redis:6-alpine | findstr "redis" >nul 2>&1
if errorlevel 1 (
    echo [提示] 下载 Redis 镜像...
    docker pull redis:6-alpine
    if errorlevel 1 (
        echo [错误] 镜像下载失败，请检查网络连接
        pause
        exit /b 1
    )
)

REM 停止可能存在的旧容器
echo [提示] 停止旧容器（如果存在）...
docker-compose -f docker-compose.usb.yml down 2>nul

REM 启动数据库服务
echo.
echo [提示] 启动 PostgreSQL 和 Redis...
docker-compose -f docker-compose.usb.yml up -d postgres redis

if errorlevel 1 (
    echo [错误] Docker 容器启动失败
    echo.
    echo 可能的原因：
    echo 1. 端口 5432 或 6379 被占用
    echo 2. U盘权限不足
    echo 3. Docker 服务未启动
    echo.
    pause
    exit /b 1
)

REM 等待数据库就绪
echo [提示] 等待数据库就绪（10秒）...
timeout /t 10 /nobreak >nul

REM 检查容器状态
docker ps --filter "name=postgres" --format "{{.Names}}" | findstr "postgres" >nul 2>&1
if errorlevel 1 (
    echo [警告] PostgreSQL 容器可能未正常启动
    echo 请检查: docker ps -a
    echo.
)

REM 切换到后端目录
cd backend

REM 检查 .env 文件
if not exist .env (
    echo [提示] 创建 .env 文件...
    if exist env.example (
        copy env.example .env >nul
        echo [提示] 已从 env.example 创建 .env 文件
        echo [重要] 请编辑 .env 文件，配置 QWEN_API_KEY
        timeout /t 3 >nul
    )
)

REM 检查并设置 PostgreSQL 数据库 URL
findstr /C:"DATABASE_URL" .env >nul
if errorlevel 1 (
    echo [提示] 添加 PostgreSQL 数据库配置...
    echo DATABASE_URL=postgresql://postgres:Pk26605164@localhost:5432/aircraft_workcard >> .env
) else (
    REM 确保使用PostgreSQL（不是SQLite）
    powershell -Command "(Get-Content .env) -replace 'sqlite://', 'postgresql://postgres:Pk26605164@localhost:5432/aircraft_workcard' | Set-Content .env"
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

REM 运行数据库迁移
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
echo PostgreSQL: localhost:5432
echo Redis: localhost:6379
echo.
echo [重要] 数据存储在: %USB_DRIVE%\docker_data\
echo.
echo ====================================
echo 关于 Docker 便携性的说明
echo ====================================
echo Docker Desktop 需要安装在系统上（不能完全便携）
echo 但项目数据、配置、镜像都在 U 盘，可以带走！
echo.
echo 换电脑时：
echo 1. 安装 Docker Desktop（首次，约5-10分钟）
echo 2. 运行此脚本即可（数据从 U 盘加载）
echo.
echo 如果追求完全便携，请使用 SQLite 版本：
echo   启动后端-便携版.bat
echo ====================================
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
    echo 2. 数据库连接失败（检查Docker容器是否运行）
    echo 3. 环境变量配置错误
    echo.
    echo 检查Docker容器: docker ps
    echo.
    pause
)

REM 清理：停止Docker容器（可选）
REM echo.
REM echo [提示] 是否停止 Docker 容器？(Y/N)
REM set /p STOP_DOCKER=
REM if /i "%STOP_DOCKER%"=="Y" (
REM     cd ..
REM     docker-compose -f docker-compose.usb.yml down
REM )

