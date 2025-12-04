@echo off
chcp 65001
setlocal enabledelayedexpansion

echo ====================================
echo 部署项目到 U 盘（完全便携版）
echo ====================================
echo.

REM 目标目录
set TARGET_DIR=F:\autojobcard
set SOURCE_DIR=%~dp0

echo [提示] 源目录: %SOURCE_DIR%
echo [提示] 目标目录: %TARGET_DIR%
echo.

REM 检查目标目录是否存在
if not exist "%TARGET_DIR%" (
    echo [提示] 创建目标目录...
    mkdir "%TARGET_DIR%" 2>nul
    if errorlevel 1 (
        echo [错误] 无法创建目标目录: %TARGET_DIR%
        echo 请检查 U 盘是否已插入，或手动创建目录
        pause
        exit /b 1
    )
)

echo [提示] 开始复制文件...
echo.

REM 复制后端文件（排除 venv 和 __pycache__）
echo [1/4] 复制后端文件...
if exist "%SOURCE_DIR%exclude.txt" (
    xcopy "%SOURCE_DIR%backend" "%TARGET_DIR%\backend" /E /I /Y /EXCLUDE:"%SOURCE_DIR%exclude.txt" >nul 2>&1
) else (
    xcopy "%SOURCE_DIR%backend" "%TARGET_DIR%\backend" /E /I /Y /EXCLUDE:exclude.txt >nul 2>&1
)
if errorlevel 1 (
    echo [警告] 部分文件可能复制失败，继续...
)

REM 复制前端文件（排除 node_modules）
echo [2/4] 复制前端文件...
if exist "%SOURCE_DIR%exclude.txt" (
    xcopy "%SOURCE_DIR%frontend" "%TARGET_DIR%\frontend" /E /I /Y /EXCLUDE:"%SOURCE_DIR%exclude.txt" >nul 2>&1
) else (
    xcopy "%SOURCE_DIR%frontend" "%TARGET_DIR%\frontend" /E /I /Y /EXCLUDE:exclude.txt >nul 2>&1
)
if errorlevel 1 (
    echo [警告] 部分文件可能复制失败，继续...
)

REM 复制启动脚本和配置文件
echo [3/4] 复制启动脚本和配置文件...
copy "%SOURCE_DIR%启动后端-U盘便携版.bat" "%TARGET_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%启动前端-U盘便携版.bat" "%TARGET_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%一键启动-U盘版.bat" "%TARGET_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%配置环境-U盘版.bat" "%TARGET_DIR%\配置环境.bat" >nul 2>&1
copy "%SOURCE_DIR%README-U盘版.md" "%TARGET_DIR%\README.md" >nul 2>&1
copy "%SOURCE_DIR%exclude.txt" "%TARGET_DIR%\" >nul 2>&1

REM 创建必要的目录
echo [4/4] 创建必要的目录...
if not exist "%TARGET_DIR%\backend\storage" mkdir "%TARGET_DIR%\backend\storage"
if not exist "%TARGET_DIR%\backend\storage\import_logs" mkdir "%TARGET_DIR%\backend\storage\import_logs"
if not exist "%TARGET_DIR%\backend\uploads" mkdir "%TARGET_DIR%\backend\uploads"
if not exist "%TARGET_DIR%\backend\uploads\index_files" mkdir "%TARGET_DIR%\backend\uploads\index_files"

echo.
echo ====================================
echo 部署完成！
echo ====================================
echo.
echo 项目已部署到: %TARGET_DIR%
echo.
echo 下一步：
echo 1. 进入 U 盘目录: %TARGET_DIR%
echo 2. 运行: 一键启动-U盘版.bat
echo.
echo 注意：
echo - 首次运行需要安装 Python 和 Node.js 依赖
echo - 确保系统已安装 Python 3.9+ 和 Node.js 16+
echo.
pause

