@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo URL切换备份脚本
echo ========================================
echo.
echo 此脚本将创建以下备份：
echo   1. Git标签: v1.0-vpn-version
echo   2. Git分支: backup/vpn-version
echo   3. 代码快照: C:\AI\demo3-backup-vpn-version
echo.
echo 按任意键继续，或按Ctrl+C取消...
pause >nul
echo.

cd /d C:\AI\demo3
if errorlevel 1 (
    echo 错误：无法进入项目目录 C:\AI\demo3
    pause
    exit /b 1
)

echo [1/6] 检查Git状态...
git status
if errorlevel 1 (
    echo 警告：Git命令执行失败，请检查Git是否已安装
    pause
    exit /b 1
)
echo.

echo [2/6] 检查是否有未提交的更改...
git diff --quiet
if errorlevel 1 (
    echo 发现未提交的更改，正在添加...
    git add .
    echo.
    echo 请输入提交信息（直接回车使用默认信息）：
    set /p commit_msg="提交信息: "
    if "!commit_msg!"=="" set commit_msg=备份：保存VPN版本代码，准备切换到内网直连版本
    git commit -m "!commit_msg!"
    if errorlevel 1 (
        echo 错误：提交失败
        pause
        exit /b 1
    )
    echo 提交成功！
) else (
    echo 没有未提交的更改，跳过提交步骤
)
echo.

echo [3/6] 创建Git标签 v1.0-vpn-version...
git tag -a v1.0-vpn-version -m "VPN版本备份：所有URL使用VPN访问方式"
if errorlevel 1 (
    echo 警告：标签可能已存在，尝试删除后重新创建...
    git tag -d v1.0-vpn-version 2>nul
    git tag -a v1.0-vpn-version -m "VPN版本备份：所有URL使用VPN访问方式"
)
echo 标签创建成功！
git tag -l | findstr "v1.0-vpn-version"
echo.

echo [4/6] 创建备份分支 backup/vpn-version...
git branch backup/vpn-version 2>nul
if errorlevel 1 (
    echo 警告：分支可能已存在
) else (
    echo 分支创建成功！
)
git branch -a | findstr "backup/vpn-version"
echo.

echo [5/6] 创建代码快照...
set backup_dir=C:\AI\demo3-backup-vpn-version
if exist "!backup_dir!" (
    echo 备份目录已存在，是否删除后重新创建？(Y/N)
    set /p confirm="确认: "
    if /i "!confirm!"=="Y" (
        rmdir /s /q "!backup_dir!" 2>nul
        echo 已删除旧备份目录
    ) else (
        echo 跳过代码快照创建
        goto :skip_snapshot
    )
)

mkdir "!backup_dir!" 2>nul
if errorlevel 1 (
    echo 错误：无法创建备份目录
    pause
    exit /b 1
)

echo 正在复制文件（这可能需要一些时间）...
robocopy C:\AI\demo3 "!backup_dir!" /E /XD node_modules venv __pycache__ .git exports storage /XF *.pyc *.log *.tmp /NFL /NDL /NP /NJH /NJS
if errorlevel 8 (
    echo 警告：robocopy执行完成，但可能有部分文件复制失败
) else (
    echo 代码快照创建成功！
)
:skip_snapshot
echo.

echo [6/6] 验证备份...
echo.
echo 检查Git标签:
git tag -l | findstr "vpn-version"
if errorlevel 1 (
    echo    ✗ 标签未找到
) else (
    echo    ✓ 标签存在
)
echo.

echo 检查Git分支:
git branch -a | findstr "backup/vpn-version"
if errorlevel 1 (
    echo    ✗ 分支未找到
) else (
    echo    ✓ 分支存在
)
echo.

echo 检查代码快照:
if exist "!backup_dir!" (
    echo    ✓ 快照目录存在: !backup_dir!
    dir "!backup_dir!" /b | find /c /v "" >nul
    echo    快照文件数量: 
    for /f %%i in ('dir "!backup_dir!" /s /b /a-d ^| find /c /v ""') do echo    %%i 个文件
) else (
    echo    ✗ 快照目录不存在
)
echo.

echo ========================================
echo 备份完成！
echo ========================================
echo.
echo 备份位置：
echo   标签: v1.0-vpn-version
echo   分支: backup/vpn-version
echo   快照: !backup_dir!
echo.
echo 如果需要推送到远程仓库，请执行：
echo   git push origin v1.0-vpn-version
echo   git push origin backup/vpn-version
echo.
echo 如果需要恢复备份，请查看 "URL切换备份指南.md"
echo.
pause

