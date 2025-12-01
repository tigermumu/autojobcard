@echo off
chcp 65001 >nul
echo ========================================
echo 构型数据验证工具
echo ========================================
echo.

cd backend
python scripts\verify_configurations.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 验证通过！
    pause
) else (
    echo.
    echo 验证发现问题，请检查上述输出
    pause
)






