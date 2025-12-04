@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 配置环境变量（U盘便携版 - 自动检测）
echo ====================================
echo.

REM ============================================
REM 自动检测 Python 和 Node.js
REM ============================================

REM 检测 Python（优先使用系统安装的）
echo [提示] 检测 Python...
where python >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到系统 Python
    echo [提示] 请确保已安装 Python 3.9+
    echo.
    echo 如果已安装但未添加到 PATH，请手动添加到环境变量
    echo 或使用便携版 Python（需要修改此脚本中的路径）
    echo.
    set PYTHON_FOUND=0
) else (
    python --version
    echo [OK] Python 已找到
    set PYTHON_FOUND=1
)

REM 检测 Node.js（优先使用系统安装的）
echo.
echo [提示] 检测 Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到系统 Node.js
    echo [提示] 请确保已安装 Node.js 16+
    echo.
    echo 如果已安装但未添加到 PATH，请手动添加到环境变量
    echo 或使用便携版 Node.js（需要修改此脚本中的路径）
    echo.
    set NODE_FOUND=0
) else (
    node --version
    echo [OK] Node.js 已找到
    set NODE_FOUND=1
)

REM 如果都找到了，直接返回
if %PYTHON_FOUND%==1 if %NODE_FOUND%==1 (
    echo.
    echo ====================================
    echo 环境配置完成！
    echo ====================================
    echo.
    goto :end
)

REM 如果没找到，提供便携版配置选项
echo.
echo ====================================
echo 便携版配置（可选）
echo ====================================
echo.
echo 如果系统未安装 Python/Node.js，可以使用便携版：
echo.
echo 1. 下载 Python 便携版：
echo    https://www.python.org/downloads/
echo    解压到 U 盘，例如: %~d0\Tools\Python311
echo.
echo 2. 下载 Node.js 便携版：
echo    https://nodejs.org/download/
echo    解压到 U 盘，例如: %~d0\Tools\nodejs
echo.
echo 3. 修改此脚本，取消注释以下行并设置路径：
echo    set PYTHON_HOME=%~d0\Tools\Python311
echo    set NODE_HOME=%~d0\Tools\nodejs
echo.

REM 便携版路径配置（默认注释，需要时取消注释）
REM set PYTHON_HOME=%~d0\Tools\Python311
REM set NODE_HOME=%~d0\Tools\nodejs
REM if exist "%PYTHON_HOME%\python.exe" set PATH=%PYTHON_HOME%;%PATH%
REM if exist "%NODE_HOME%\node.exe" set PATH=%NODE_HOME%;%PATH%

:end
echo.






