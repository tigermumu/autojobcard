@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 配置环境变量（便携版）
echo ====================================
echo.

REM ============================================
REM 请根据实际路径修改以下配置
REM ============================================

REM Python 便携版路径（根据实际路径修改）
set PYTHON_HOME=D:\Tools\Python311
REM 如果 Python 在其他位置，请修改上面的路径

REM Node.js 便携版路径（根据实际路径修改）
set NODE_HOME=D:\Tools\nodejs
REM 如果 Node.js 在其他位置，请修改上面的路径

REM ============================================
REM 自动添加到 PATH
REM ============================================
set PATH=%PYTHON_HOME%;%NODE_HOME%;%PATH%

REM 验证 Python
echo 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未找到！
    echo 当前路径: %PYTHON_HOME%
    echo.
    echo 请检查：
    echo 1. Python 便携版是否已解压到指定目录
    echo 2. 路径是否正确
    echo 3. 是否包含 python.exe 文件
    echo.
    echo 如果路径不同，请编辑此文件修改 PYTHON_HOME
    pause
    exit /b 1
) else (
    python --version
    echo [OK] Python 已找到
)

REM 验证 Node.js
echo.
echo 检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Node.js 未找到！
    echo 当前路径: %NODE_HOME%
    echo.
    echo 请检查：
    echo 1. Node.js 便携版是否已解压到指定目录
    echo 2. 路径是否正确
    echo 3. 是否包含 node.exe 文件
    echo.
    echo 如果路径不同，请编辑此文件修改 NODE_HOME
    pause
    exit /b 1
) else (
    node --version
    echo [OK] Node.js 已找到
)

echo.
echo ====================================
echo 环境配置完成！
echo ====================================
echo.




