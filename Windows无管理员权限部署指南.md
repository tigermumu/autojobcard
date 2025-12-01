# Windows 无管理员权限部署指南

## 📋 方案概述

在没有管理员权限的 Windows 系统上，我们使用以下策略：

1. **SQLite 替代 PostgreSQL** - 无需安装，零配置
2. **Redis 可选** - 如果 Celery 未使用，可以跳过
3. **Python 便携版** - 解压即用，无需安装
4. **Node.js 便携版** - 解压即用，无需安装
5. **所有文件放在用户目录** - 不需要系统目录权限

---

## 🎯 方案1：SQLite + 便携版 Python/Node.js（推荐 ⭐⭐⭐⭐⭐）

### 优点
- ✅ 完全不需要管理员权限
- ✅ 不需要安装任何软件
- ✅ 所有文件都在用户目录
- ✅ 快速启动，零配置

### 第一步：准备便携版软件

#### 1.1 下载 Python 便携版

1. **下载 Python 嵌入版（Embeddable Package）**
   - 访问：https://www.python.org/downloads/windows/
   - 选择 "Windows embeddable package (64-bit)"
   - 下载 Python 3.9+ 版本（如 `python-3.11.7-embed-amd64.zip`）

2. **解压到用户目录**
   ```bash
   # 创建目录（例如在 D:\Tools）
   mkdir D:\Tools\Python311
   
   # 解压 python-3.11.7-embed-amd64.zip 到 D:\Tools\Python311
   ```

3. **配置 Python**
   ```bash
   cd D:\Tools\Python311
   
   # 创建 python311._pth 文件（如果不存在）
   # 编辑 python311._pth，添加以下内容：
   # python311.zip
   # .
   # import site
   ```

#### 1.2 下载 Node.js 便携版

1. **下载 Node.js 便携版**
   - 访问：https://nodejs.org/dist/
   - 选择版本（如 v18.19.0）
   - 下载 `node-v18.19.0-win-x64.zip`

2. **解压到用户目录**
   ```bash
   # 解压到 D:\Tools\nodejs
   ```

#### 1.3 下载 Redis 便携版（可选）

如果确实需要 Redis（虽然 Celery 已注释，可能不需要）：

1. **下载 Redis for Windows**
   - 访问：https://github.com/microsoftarchive/redis/releases
   - 下载最新版本的 ZIP 文件
   - 解压到 `D:\Tools\redis`

---

### 第二步：获取项目代码

```bash
# 在用户目录创建项目文件夹
cd D:\Projects

# 克隆代码（如果有 Git）
git clone https://gitee.com/bomingaviation_liugw_4779/workshop.git

# 或直接复制项目文件夹
```

---

### 第三步：配置 SQLite 数据库

#### 3.1 修改数据库配置

编辑 `backend/app/core/config.py`，添加 SQLite 支持：

```python
# 在 config.py 中添加
import os
from pathlib import Path

# 数据库配置 - 支持 SQLite
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{Path(__file__).parent.parent.parent / 'aircraft_workcard.db'}"
)
```

或者更简单的方法：直接修改 `backend/.env` 文件：

```bash
# 使用 SQLite（相对路径）
DATABASE_URL=sqlite:///./aircraft_workcard.db

# 或使用绝对路径
DATABASE_URL=sqlite:///D:/Projects/workshop/backend/aircraft_workcard.db
```

#### 3.2 修改 requirements.txt（可选）

SQLite 是 Python 内置的，不需要额外安装。但如果需要，可以确保安装了 `sqlalchemy`（已包含）。

---

### 第四步：创建启动脚本

#### 4.1 创建环境配置脚本 `配置环境.bat`

```batch
@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 配置环境变量
echo ====================================
echo.

REM 设置 Python 路径（根据实际路径修改）
set PYTHON_HOME=D:\Tools\Python311
set PATH=%PYTHON_HOME%;%PATH%

REM 设置 Node.js 路径（根据实际路径修改）
set NODE_HOME=D:\Tools\nodejs
set PATH=%NODE_HOME%;%PATH%

REM 验证
echo 检查 Python...
python --version
if errorlevel 1 (
    echo [错误] Python 未找到，请检查 PYTHON_HOME 路径
    pause
    exit /b 1
)

echo 检查 Node.js...
node --version
if errorlevel 1 (
    echo [错误] Node.js 未找到，请检查 NODE_HOME 路径
    pause
    exit /b 1
)

echo.
echo 环境配置完成！
echo ====================================
```

#### 4.2 创建后端启动脚本 `启动后端-便携版.bat`

```batch
@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd backend

echo ====================================
echo 启动后端服务（SQLite 版本）
echo ====================================
echo.

REM 检查 .env 文件
if not exist .env (
    echo 创建 .env 文件...
    copy env.example .env >nul
    echo [提示] 请编辑 .env 文件，配置 QWEN_API_KEY
    echo [提示] DATABASE_URL 已设置为 SQLite
    echo.
)

REM 创建虚拟环境（如果不存在）
if not exist venv (
    echo 创建 Python 虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖（如果未安装）
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 安装 Python 依赖...
    pip install -r requirements.txt
)

REM 运行数据库迁移（SQLite）
echo 运行数据库迁移...
python -m alembic upgrade head

echo.
echo ====================================
echo 启动后端 API 服务器...
echo ====================================
echo API: http://localhost:8000
echo 文档: http://localhost:8000/api/v1/docs
echo.
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
```

#### 4.3 创建前端启动脚本 `启动前端-便携版.bat`

```batch
@echo off
chcp 65001
cd /d %~dp0

REM 加载环境配置
call 配置环境.bat

cd frontend

echo ====================================
echo 启动前端服务
echo ====================================
echo.

REM 安装依赖（如果未安装）
if not exist node_modules (
    echo 安装 Node.js 依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

REM 检查 API 配置
echo 检查 API 配置...
findstr /C:"localhost:8000" src\services\api.ts >nul
if errorlevel 1 (
    echo [提示] 前端 API 地址可能需要配置
)

echo.
echo ====================================
echo 启动前端开发服务器...
echo ====================================
echo URL: http://localhost:3000
echo API: http://localhost:8000
echo.
echo 确保后端服务已启动
echo 按 Ctrl+C 停止服务器
echo ====================================
echo.

call npm run dev

pause
```

---

## 🎯 方案2：使用云数据库（最简单 ⭐⭐⭐⭐⭐）

如果可以使用云服务，这是最简单的方案：

### 使用免费的云数据库服务

1. **Supabase（PostgreSQL）**
   - 免费额度：500MB 数据库
   - 访问：https://supabase.com
   - 创建项目后获取连接字符串

2. **Railway（PostgreSQL + Redis）**
   - 免费额度：每月 $5 额度
   - 访问：https://railway.app
   - 可以同时部署数据库和 Redis

3. **Render（PostgreSQL）**
   - 免费额度：90 天免费试用
   - 访问：https://render.com

### 配置步骤

1. **创建云数据库**
   - 在 Supabase/Railway 创建 PostgreSQL 数据库
   - 获取连接字符串（类似：`postgresql://user:pass@host:5432/dbname`）

2. **修改环境变量**
   ```bash
   # backend/.env
   DATABASE_URL=postgresql://你的云数据库连接字符串
   REDIS_URL=redis://你的云Redis连接字符串（如果需要）
   ```

3. **使用便携版 Python/Node.js 启动**
   - 按照方案1的步骤4启动后端和前端
   - 数据库迁移会自动连接到云数据库

---

## 🎯 方案3：使用 WSL2（如果可用）

如果系统已安装 WSL2（不需要管理员权限启动），可以使用：

### 步骤

1. **在 WSL2 中安装 Docker（用户级）**
   ```bash
   # 在 WSL2 Ubuntu 中
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # 将当前用户添加到 docker 组（不需要 sudo）
   # 注意：需要重启 WSL2 才能生效
   ```

2. **按照 Linux 部署步骤操作**
   - 参考 `腾讯云部署指南.md`
   - 所有操作都在 WSL2 中完成

---

## 📝 快速开始（推荐：方案1）

### 完整流程

1. **下载便携版软件**
   - Python 嵌入版：解压到 `D:\Tools\Python311`
   - Node.js 便携版：解压到 `D:\Tools\nodejs`

2. **获取项目代码**
   ```bash
   cd D:\Projects
   git clone https://gitee.com/bomingaviation_liugw_4779/workshop.git
   ```

3. **配置环境变量**
   ```bash
   # 编辑 backend/.env
   DATABASE_URL=sqlite:///./aircraft_workcard.db
   QWEN_API_KEY=你的API密钥
   ```

4. **修改配置环境.bat**
   - 更新 `PYTHON_HOME` 和 `NODE_HOME` 路径

5. **启动服务**
   ```bash
   # 双击运行
   启动后端-便携版.bat
   
   # 在另一个窗口
   启动前端-便携版.bat
   ```

6. **访问应用**
   - 前端：http://localhost:3000
   - API文档：http://localhost:8000/api/v1/docs

---

## 🔧 SQLite 迁移配置

### 修改 Alembic 配置

编辑 `backend/alembic.ini`：

```ini
# 修改数据库 URL（使用环境变量）
# sqlalchemy.url = postgresql://postgres:password@localhost:5432/aircraft_workcard
# 改为：
sqlalchemy.url = sqlite:///./aircraft_workcard.db
```

或者确保 `backend/migrations/env.py` 从环境变量读取（已配置）。

---

## ⚠️ 注意事项

### SQLite 限制

1. **并发写入**：SQLite 不支持高并发写入
2. **数据类型**：某些 PostgreSQL 特性可能不支持
3. **性能**：大数据量时性能不如 PostgreSQL

### 适用场景

- ✅ 试用/演示环境
- ✅ 单用户开发
- ✅ 小数据量测试
- ❌ 生产环境（建议使用 PostgreSQL）

---

## 🛠️ 故障排查

### 问题1：Python 找不到模块

**解决方法**：
```bash
# 确保 python311._pth 文件包含：
python311.zip
.
import site
```

### 问题2：Node.js 命令找不到

**解决方法**：
- 检查 `配置环境.bat` 中的 `NODE_HOME` 路径
- 确保 Node.js 便携版已解压

### 问题3：数据库迁移失败

**解决方法**：
```bash
# 删除旧的数据库文件
del backend\aircraft_workcard.db

# 重新运行迁移
python -m alembic upgrade head
```

### 问题4：端口被占用

**解决方法**：
```bash
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 停止进程（不需要管理员权限）
taskkill /PID <进程ID> /F
```

---

## 📦 便携版软件下载地址汇总

| 软件 | 下载地址 | 说明 |
|------|---------|------|
| Python 嵌入版 | https://www.python.org/downloads/windows/ | 选择 "Windows embeddable package" |
| Node.js 便携版 | https://nodejs.org/dist/ | 下载 `win-x64.zip` 版本 |
| Redis Windows | https://github.com/microsoftarchive/redis/releases | 可选，如果不需要 Celery 可以跳过 |

---

## ✅ 部署检查清单

- [ ] Python 便携版已下载并解压
- [ ] Node.js 便携版已下载并解压
- [ ] 项目代码已获取
- [ ] `配置环境.bat` 路径已更新
- [ ] `backend/.env` 已配置（SQLite + QWEN_API_KEY）
- [ ] 后端可以启动
- [ ] 前端可以启动
- [ ] 数据库迁移已执行
- [ ] 应用可以正常访问

---

完成以上步骤后，你就可以在没有管理员权限的 Windows 系统上运行应用了！

**推荐方案**：使用 SQLite + 便携版 Python/Node.js，这是最简单且完全不需要管理员权限的方案。




