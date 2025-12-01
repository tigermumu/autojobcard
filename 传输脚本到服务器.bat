@echo off
chcp 65001 >nul
echo ========================================
echo 传输导入导出脚本到云服务器
echo ========================================

set SERVER=ubuntu@43.136.73.97
set REMOTE_SCRIPTS=/opt/workshop/backend/scripts

echo.
echo 服务器: %SERVER%
echo 远程路径: %REMOTE_SCRIPTS%
echo.

echo 步骤1: 创建远程scripts目录并设置权限...
ssh %SERVER% "sudo mkdir -p %REMOTE_SCRIPTS% && sudo chown -R ubuntu:ubuntu %REMOTE_SCRIPTS% && sudo chmod -R 755 %REMOTE_SCRIPTS%"

echo.
echo 步骤2: 传输导入脚本...
scp backend\scripts\import_configurations.py %SERVER%:%REMOTE_SCRIPTS%/

echo.
echo 步骤3: 传输导出脚本...
scp backend\scripts\export_configurations.py %SERVER%:%REMOTE_SCRIPTS%/

echo.
echo 步骤4: 传输验证脚本...
scp backend\scripts\verify_configurations.py %SERVER%:%REMOTE_SCRIPTS%/

echo.
echo 步骤5: 设置执行权限...
ssh %SERVER% "chmod +x %REMOTE_SCRIPTS%/*.py && chmod +x %REMOTE_SCRIPTS%/*.sh 2>/dev/null || true"

echo.
echo ========================================
echo ✓ 传输完成！
echo ========================================
echo.
echo 下一步：在服务器上运行导入命令
echo ssh %SERVER%
echo cd /opt/workshop/backend
echo python3 scripts/import_configurations.py --use-python --export-dir exports/configurations_20251124_191930

pause

