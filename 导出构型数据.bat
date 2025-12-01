@echo off
chcp 65001 >nul
echo ========================================
echo 构型数据导出工具
echo ========================================
echo.
echo 提示: 如果遇到 pg_dump 未找到的错误，
echo      脚本会自动切换到Python导出方式
echo.

cd backend
python scripts\export_configurations.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 导出成功！
    pause
) else (
    echo.
    echo 导出失败，请检查错误信息
    echo.
    echo 如果是因为 pg_dump 未找到，可以尝试：
    echo python scripts\export_configurations.py --use-python
    pause
)

