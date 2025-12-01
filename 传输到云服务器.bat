@echo off
chcp 65001 >nul
echo ========================================
echo 构型数据传输到云服务器
echo ========================================

set SERVER=ubuntu@43.136.73.97
set REMOTE_PATH=/opt/workshop/backend/exports
set LOCAL_DIR=backend\exports\configurations_20251124_191930

echo.
echo 服务器: %SERVER%
echo 远程路径: %REMOTE_PATH%
echo 本地目录: %LOCAL_DIR%
echo.

echo 步骤1: 检查远程目录权限...
ssh %SERVER% "ls -ld %REMOTE_PATH% && echo '目录存在' || echo '目录不存在'"

echo.
echo 步骤2: 传输文件（尝试不带末尾斜杠）...
scp -r %LOCAL_DIR% %SERVER%:%REMOTE_PATH%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✓ 传输成功！
    echo ========================================
    echo.
    echo 下一步：在云服务器上运行导入命令
    echo ssh %SERVER%
    echo cd /opt/workshop/backend
    echo python3 scripts/import_configurations.py --use-python --export-dir exports/configurations_20251124_191930
    pause
    exit /b 0
)

echo.
echo ✗ 第一次尝试失败，尝试修复权限后重试...
ssh %SERVER% "chmod 755 %REMOTE_PATH% && chown -R ubuntu:ubuntu %REMOTE_PATH% 2>/dev/null || true"

echo.
echo 步骤3: 重新传输文件...
scp -r %LOCAL_DIR% %SERVER%:%REMOTE_PATH%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✓ 传输成功！
    echo ========================================
) else (
    echo.
    echo ✗ 传输仍然失败
    echo.
    echo 建议手动操作：
    echo 1. 在服务器上检查目录权限: ls -ld %REMOTE_PATH%
    echo 2. 或者直接在服务器上操作（如果已经在服务器上）
    echo.
    echo 如果已经在服务器上，可以：
    echo - 使用 rsync 从本地同步
    echo - 或者直接在服务器上解压传输的压缩包
)

pause
