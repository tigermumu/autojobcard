@echo off
chcp 65001 >nul
echo ========================================
echo 构型数据导入工具
echo ========================================
echo.
echo 警告: 此操作将导入数据到当前数据库
echo.
echo 提示: 如果遇到 psql 未找到的错误，
echo      脚本会自动切换到Python导入方式
echo.
pause

cd backend
python scripts\import_configurations.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 导入成功！
    pause
) else (
    echo.
    echo 导入失败，请检查错误信息
    echo.
    echo 如果是因为 psql 未找到，可以尝试：
    echo python scripts\import_configurations.py --use-python
    pause
)

