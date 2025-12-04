@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 飞机方案处理系统 - 一键启动
echo ====================================
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装或未启动
    echo 请先安装并启动 Docker Desktop
    echo.
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查 docker-compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo [错误] Docker Compose 未安装
        echo 请确保 Docker Desktop 已正确安装
        pause
        exit /b 1
    )
)

echo [1/5] 检查环境变量配置...
if not exist backend\.env (
    echo [警告] backend\.env 文件不存在
    echo 正在从 env.example 创建...
    if exist backend\env.example (
        copy backend\env.example backend\.env >nul
        echo [提示] 请编辑 backend\.env 文件，配置 QWEN_API_KEY 等参数
    ) else (
        echo [错误] backend\env.example 文件不存在
        pause
        exit /b 1
    )
)

echo [2/5] 启动数据库和 Redis...
docker-compose up -d postgres redis
if errorlevel 1 (
    echo [错误] 启动数据库失败
    pause
    exit /b 1
)

echo [3/5] 等待数据库启动...
timeout /t 10 /nobreak >nul

echo [4/5] 运行数据库迁移...
docker-compose run --rm backend python -m alembic upgrade head
if errorlevel 1 (
    echo [警告] 数据库迁移可能失败，但继续启动服务...
)

echo [5/5] 启动所有服务...
docker-compose up -d --build
if errorlevel 1 (
    echo [错误] 启动服务失败
    pause
    exit /b 1
)

echo.
echo ====================================
echo 启动完成！
echo ====================================
echo.
echo 前端应用: http://localhost:3000
echo API文档:   http://localhost:8000/api/v1/docs
echo 健康检查: http://localhost:8000/health
echo.
echo 常用命令:
echo   查看日志: docker-compose logs -f
echo   查看状态: docker-compose ps
echo   停止服务: docker-compose down
echo ====================================
echo.

REM 等待几秒让服务完全启动
timeout /t 3 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose ps

echo.
echo 按任意键退出...
pause >nul










