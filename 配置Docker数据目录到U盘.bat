@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 配置 Docker 数据目录到 U 盘
echo ====================================
echo.

REM 检测U盘盘符
set USB_DRIVE=%~d0
set USB_PATH=%USB_DRIVE%\docker_data

echo [提示] 检测到U盘盘符: %USB_DRIVE%
echo [提示] Docker 数据将存储在: %USB_PATH%
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker
    echo.
    echo 请先安装 Docker Desktop:
    echo https://www.docker.com/products/docker-desktop
    echo.
    echo 安装完成后，重新运行此脚本
    pause
    exit /b 1
)

echo [提示] Docker 已安装
docker --version
echo.

REM 检查Docker Desktop是否运行
docker ps >nul 2>&1
if errorlevel 1 (
    echo [警告] Docker Desktop 未运行
    echo 请先启动 Docker Desktop，然后重新运行此脚本
    pause
    exit /b 1
)

echo [提示] Docker Desktop 正在运行
echo.

REM 创建数据目录
if not exist "%USB_PATH%" (
    echo [提示] 创建数据目录: %USB_PATH%
    mkdir "%USB_PATH%" 2>nul
)

echo ====================================
echo 配置说明
echo ====================================
echo.
echo Docker Desktop 的数据目录配置需要手动设置：
echo.
echo 方法一：使用 Docker Desktop GUI（推荐）
echo   1. 打开 Docker Desktop
echo   2. 点击 Settings（设置）
echo   3. 选择 Resources → Advanced
echo   4. 修改 "Disk image location" 为: %USB_PATH%
echo   5. 点击 Apply & Restart
echo.
echo 方法二：使用项目级数据卷（已实现，推荐）
echo   使用 docker-compose.usb.yml，数据会自动存储在:
echo   %USB_DRIVE%\demo3\docker_data\
echo.
echo   优点：
echo   - 不影响其他 Docker 项目
echo   - 数据完全在 U 盘
echo   - 配置简单
echo.
echo ====================================
echo.

REM 检查 docker-compose.usb.yml 是否存在
if exist docker-compose.usb.yml (
    echo [提示] 检测到 docker-compose.usb.yml
    echo [提示] 项目数据将自动存储在 U 盘
    echo.
    echo 使用方法：
    echo   运行: 启动后端-U盘版.bat
    echo.
) else (
    echo [警告] 未找到 docker-compose.usb.yml
    echo 请确保已创建 U 盘部署配置文件
)

echo.
echo 按任意键退出...
pause >nul






