@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 飞机方案处理系统 - 停止服务
echo ====================================
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装或未启动
    pause
    exit /b 1
)

echo 正在停止所有服务...
docker-compose down

echo.
echo ====================================
echo 服务已停止
echo ====================================
echo.
echo 注意: 数据库数据已保留
echo 如需删除数据，请运行: docker-compose down -v
echo ====================================
echo.

pause




