@echo off
REM 配置环境.bat

REM 设置 U 盘内环境的根目录（假设相对于当前脚本的路径）
REM 如果您有特定的目录结构，请修改这里
set "ENV_ROOT=%~dp0env_runtime"

REM 设置 Python 路径 (U 盘绝对路径)
set "PYTHON_HOME=F:\WPy64-31150\python-3.11.5.amd64"

REM 设置 Node.js 路径 (U 盘绝对路径，如果需要)
set "NODE_HOME=%ENV_ROOT%\node"

REM ========================================================
REM 将 U 盘环境添加到 PATH 的最前面，强制优先使用
REM ========================================================

REM 1. 添加 Python
if exist "%PYTHON_HOME%\python.exe" (
    echo [环境] 发现 U 盘 Python: %PYTHON_HOME%
    set "PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%PATH%"
    set "PYTHONPATH=%~dp0backend"
) else (
    echo [注意] 未找到 U 盘 Python，将使用系统 Python
)

REM 2. 添加 Node.js
if exist "%NODE_HOME%\node.exe" (
    echo [环境] 发现 U 盘 Node.js: %NODE_HOME%
    set "PATH=%NODE_HOME%;%PATH%"
)

REM 3. 清理可能干扰的系统变量 (可选)
REM set PYTHONHOME=
REM set PYTHONPATH=
