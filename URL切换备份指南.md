# URL切换备份指南

本文档说明如何在进行URL从VPN版本切换到内网直连版本之前，做好完整的代码备份。

## 📋 备份方案概述

推荐使用**多重备份策略**，确保代码安全：
1. **Git分支备份**（推荐）- 创建功能分支保存当前VPN版本
2. **Git标签备份**（强烈推荐）- 创建版本标签作为里程碑
3. **代码快照备份**（可选）- 创建完整项目副本

---

## 方案一：Git分支备份（推荐）

### 优点
- ✅ 可以随时切换回VPN版本
- ✅ 保留完整的提交历史
- ✅ 可以对比两个版本的差异
- ✅ 支持合并和回滚

### 操作步骤

#### 1. 提交当前所有更改
```powershell
# 进入项目目录
cd C:\AI\demo3

# 查看当前状态
git status

# 添加所有更改（包括未跟踪的文件）
git add .

# 提交更改，使用描述性的提交信息
git commit -m "备份：保存VPN版本代码，准备切换到内网直连版本"
```

#### 2. 创建VPN版本备份分支
```powershell
# 创建并切换到新分支
git checkout -b backup/vpn-version

# 或者只创建分支不切换（保持在master）
git branch backup/vpn-version

# 查看所有分支
git branch -a
```

#### 3. 推送分支到远程仓库（可选但推荐）
```powershell
# 推送备份分支到远程
git push origin backup/vpn-version

# 或者设置上游分支
git push -u origin backup/vpn-version
```

#### 4. 切换回主分支进行修改
```powershell
# 切换回master分支
git checkout master
```

---

## 方案二：Git标签备份（强烈推荐）

### 优点
- ✅ 标记重要的代码版本点
- ✅ 可以随时通过标签恢复代码
- ✅ 不会影响当前分支
- ✅ 适合作为版本里程碑

### 操作步骤

#### 1. 确保当前代码已提交
```powershell
# 查看状态，确保没有未提交的更改
git status

# 如果有未提交的更改，先提交
git add .
git commit -m "备份：保存VPN版本代码"
```

#### 2. 创建版本标签
```powershell
# 创建带注释的标签（推荐）
git tag -a v1.0-vpn-version -m "VPN版本备份：所有URL使用VPN访问方式"

# 或者创建轻量标签
git tag v1.0-vpn-version

# 查看所有标签
git tag -l
```

#### 3. 推送标签到远程仓库
```powershell
# 推送单个标签
git push origin v1.0-vpn-version

# 或者推送所有标签
git push origin --tags
```

#### 4. 验证标签创建成功
```powershell
# 查看标签详情
git show v1.0-vpn-version

# 查看标签列表
git tag -l
```

#### 5. 如果需要恢复到这个版本
```powershell
# 方法1：创建新分支指向标签
git checkout -b restore-vpn-version v1.0-vpn-version

# 方法2：直接切换到标签（会处于detached HEAD状态）
git checkout v1.0-vpn-version
```

---

## 方案三：代码快照备份（额外保障）

### 优点
- ✅ 完全独立的备份
- ✅ 不依赖Git
- ✅ 可以压缩保存

### 操作步骤

#### 1. 创建备份目录
```powershell
# 在项目上级目录创建备份文件夹
cd C:\AI
mkdir demo3-backup-vpn-version
```

#### 2. 复制项目文件（排除不必要的文件）
```powershell
# 使用robocopy复制（Windows推荐）
robocopy C:\AI\demo3 C:\AI\demo3-backup-vpn-version /E /XD node_modules venv __pycache__ .git /XF *.pyc *.log

# 或者使用PowerShell复制
Copy-Item -Path "C:\AI\demo3\*" -Destination "C:\AI\demo3-backup-vpn-version\" -Recurse -Exclude "node_modules","venv","__pycache__",".git","*.pyc","*.log"
```

#### 3. 压缩备份（可选）
```powershell
# 使用PowerShell压缩
Compress-Archive -Path "C:\AI\demo3-backup-vpn-version" -DestinationPath "C:\AI\demo3-backup-vpn-version-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip" -Force
```

---

## 📝 完整备份流程（推荐执行顺序）

### 步骤1：检查Git状态
```powershell
cd C:\AI\demo3
git status
```

### 步骤2：提交所有更改
```powershell
# 添加所有文件
git add .

# 提交更改
git commit -m "备份：保存VPN版本代码，准备切换到内网直连版本 - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
```

### 步骤3：创建Git标签（最重要）
```powershell
# 创建带注释的标签
git tag -a v1.0-vpn-version -m "VPN版本备份：所有URL使用VPN访问方式，备份时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# 查看标签
git tag -l
```

### 步骤4：创建备份分支
```powershell
# 创建备份分支
git branch backup/vpn-version

# 查看分支
git branch -a
```

### 步骤5：推送到远程（如果有远程仓库）
```powershell
# 推送标签
git push origin v1.0-vpn-version

# 推送分支
git push origin backup/vpn-version
```

### 步骤6：创建代码快照（可选但推荐）
```powershell
# 创建备份目录
New-Item -ItemType Directory -Path "C:\AI\demo3-backup-vpn-version" -Force

# 复制文件（排除不必要的内容）
robocopy C:\AI\demo3 C:\AI\demo3-backup-vpn-version /E /XD node_modules venv __pycache__ .git exports storage /XF *.pyc *.log *.tmp
```

### 步骤7：验证备份
```powershell
# 验证标签
git show v1.0-vpn-version --stat

# 验证分支
git log backup/vpn-version --oneline -5

# 验证快照
Test-Path "C:\AI\demo3-backup-vpn-version"
```

---

## 🔄 恢复备份的方法

### 从Git标签恢复
```powershell
# 创建新分支从标签恢复
git checkout -b restore-vpn-version v1.0-vpn-version

# 或者直接切换到标签
git checkout v1.0-vpn-version
```

### 从Git分支恢复
```powershell
# 切换到备份分支
git checkout backup/vpn-version

# 或者合并备份分支到当前分支
git merge backup/vpn-version
```

### 从代码快照恢复
```powershell
# 直接复制备份文件回项目目录
robocopy C:\AI\demo3-backup-vpn-version C:\AI\demo3 /E /XD node_modules venv __pycache__ .git
```

---

## ⚠️ 重要注意事项

### 1. 备份前检查清单
- [ ] 确认所有代码更改已保存
- [ ] 确认没有未提交的重要更改
- [ ] 确认Git仓库状态正常
- [ ] 确认有足够的磁盘空间

### 2. 需要备份的关键文件
根据之前的分析，以下文件包含VPN URL配置，需要重点备份：

**核心配置文件**:
- `backend/app/core/config.py` - 包含 `WORKCARD_IMPORT_BASE_URL` 配置
- `backend/env.example` - 环境变量示例文件

**服务文件**:
- `backend/app/services/workcard_import_service.py` - 包含所有VPN URL请求

**独立脚本**:
- `NRC R.py` - 包含内网直连URL（可能需要保留）

**文档文件**:
- `内网请求URL清单.md` - 刚创建的URL清单文档

### 3. 备份验证
备份完成后，建议验证：
```powershell
# 检查标签是否存在
git tag -l | Select-String "vpn"

# 检查分支是否存在
git branch -a | Select-String "backup"

# 检查快照目录
Get-ChildItem "C:\AI\demo3-backup-vpn-version" -Recurse | Measure-Object | Select-Object Count
```

---

## 📊 备份方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| Git标签 | 标记版本点，不影响分支 | 需要手动切换 | ⭐⭐⭐⭐⭐ |
| Git分支 | 可以随时切换，保留历史 | 需要管理分支 | ⭐⭐⭐⭐ |
| 代码快照 | 完全独立，不依赖Git | 占用磁盘空间 | ⭐⭐⭐ |

**推荐组合**：Git标签 + Git分支 + 代码快照（三重保障）

---

## 🚀 快速备份脚本

可以创建一个批处理脚本自动执行备份：

```batch
@echo off
chcp 65001 >nul
echo ========================================
echo URL切换备份脚本
echo ========================================
echo.

cd /d C:\AI\demo3

echo [1/5] 检查Git状态...
git status
echo.

echo [2/5] 提交所有更改...
git add .
git commit -m "备份：保存VPN版本代码，准备切换到内网直连版本"
echo.

echo [3/5] 创建Git标签...
git tag -a v1.0-vpn-version -m "VPN版本备份"
echo.

echo [4/5] 创建备份分支...
git branch backup/vpn-version
echo.

echo [5/5] 创建代码快照...
if not exist "C:\AI\demo3-backup-vpn-version" mkdir "C:\AI\demo3-backup-vpn-version"
robocopy C:\AI\demo3 C:\AI\demo3-backup-vpn-version /E /XD node_modules venv __pycache__ .git exports storage /XF *.pyc *.log *.tmp
echo.

echo ========================================
echo 备份完成！
echo ========================================
echo 标签: v1.0-vpn-version
echo 分支: backup/vpn-version
echo 快照: C:\AI\demo3-backup-vpn-version
echo.
pause
```

---

## 📌 下一步操作

完成备份后，您可以：

1. **验证备份成功**：按照"验证备份"部分检查
2. **开始URL切换**：在确认备份无误后，开始修改代码
3. **记录修改日志**：记录所有URL变更的详细信息

---

## 💡 提示

- 建议在备份完成后，先在一个测试分支上进行URL切换，验证无误后再合并到主分支
- 如果使用远程Git仓库（如Gitee），记得推送标签和分支
- 代码快照可以定期更新，但Git标签和分支是永久保存的

---

**备份完成后，请确认所有备份都已成功创建，然后再进行URL切换操作！**

