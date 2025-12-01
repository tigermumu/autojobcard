# Windows 系统部署指南（试用版）

## 📋 部署方案对比

### 方案1：Docker Desktop（推荐 ⭐⭐⭐⭐⭐）

**优点**：
- ✅ 环境隔离，不污染系统
- ✅ 与 Linux 生产环境一致
- ✅ 一键启动，简单快捷
- ✅ 数据库和 Redis 自动管理

**缺点**：
- ❌ 需要安装 Docker Desktop（约 500MB）
- ❌ 需要启用 WSL2 或 Hyper-V

**适用场景**：推荐用于试用和开发环境

### 方案2：直接运行（原生 Windows）⭐⭐⭐

**优点**：
- ✅ 不需要 Docker
- ✅ 启动速度快
- ✅ 资源占用少

**缺点**：
- ❌ 需要手动安装 Python、Node.js、PostgreSQL、Redis
- ❌ 环境配置复杂
- ❌ 与生产环境差异大

**适用场景**：已有完整开发环境的开发者

### 方案3：WSL2 + Docker（Linux 环境）⭐⭐⭐⭐

**优点**：
- ✅ 与生产环境完全一致
- ✅ 可以使用 Linux 命令

**缺点**：
- ❌ 需要安装 WSL2
- ❌ 需要配置 WSL2 网络

**适用场景**：熟悉 Linux 的开发者

---

## 🚀 推荐方案：Docker Desktop（方案1）

### 前置要求

1. **Windows 10/11**（64位）
2. **至少 8GB 内存**（推荐 16GB）
3. **至少 20GB 可用磁盘空间**

### 第一步：安装 Docker Desktop

1. **下载 Docker Desktop**
   - 访问：https://www.docker.com/products/docker-desktop
   - 下载 Windows 版本
   - 文件大小约 500MB

2. **安装 Docker Desktop**
   - 双击安装包，按提示完成安装
   - 安装过程中会提示启用 WSL2，选择"是"
   - 如果系统没有 WSL2，会自动安装

3. **启动 Docker Desktop**
   - 安装完成后，启动 Docker Desktop
   - 等待 Docker 引擎启动（右下角图标变绿）
   - 首次启动可能需要几分钟

4. **验证安装**
   ```bash
   # 打开 PowerShell 或 CMD
   docker --version
   docker-compose --version
   # 或
   docker compose version
   ```

### 第二步：获取项目代码

**方法1：从 Gitee 克隆（推荐）**

```bash
# 打开 PowerShell 或 Git Bash
cd D:\Projects  # 或你想要的目录

# 克隆代码
git clone https://gitee.com/bomingaviation_liugw_4779/workshop.git

# 进入项目目录
cd workshop
```

**方法2：直接复制项目文件夹**

- 将整个项目文件夹复制到目标 Windows 系统
- 确保保留所有文件（包括 `.git` 文件夹）

### 第三步：配置环境变量

1. **创建后端环境变量文件**

```bash
# 进入后端目录
cd backend

# 复制示例文件
copy env.example .env

# 编辑 .env 文件（使用记事本或 VS Code）
notepad .env
```

2. **配置必要的环境变量**

打开 `backend/.env` 文件，至少配置以下内容：

```bash
# 数据库配置（使用 Docker Compose 中的 postgres 服务）
DATABASE_URL=postgresql://postgres:Pk26605164@localhost:5432/aircraft_workcard

# Redis配置（使用 Docker Compose 中的 redis 服务）
REDIS_URL=redis://localhost:6379

# Qwen API配置（必须填写真实的 API Key）
QWEN_API_KEY=你的Qwen_API_Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

# 其他配置可以使用默认值
```

3. **创建 Docker Compose 环境变量文件（可选）**

在项目根目录创建 `.env` 文件：

```bash
# 返回项目根目录
cd ..

# 创建 .env 文件
notepad .env
```

内容：
```bash
QWEN_API_KEY=你的Qwen_API_Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

### 第四步：启动服务

#### 方式1：使用 Docker Compose（推荐）

**一键启动所有服务**：

```bash
# 在项目根目录执行
docker-compose up -d --build
```

**或者分步启动**：

```bash
# 1. 启动数据库和 Redis
docker-compose up -d postgres redis

# 等待几秒让数据库启动
timeout /t 10

# 2. 运行数据库迁移
docker-compose run --rm backend python -m alembic upgrade head

# 3. 启动所有服务
docker-compose up -d
```

**查看服务状态**：

```bash
docker-compose ps
```

应该看到所有服务都是 `Up` 状态：
- postgres
- redis
- backend
- frontend

**查看日志**：

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### 方式2：使用批处理脚本（如果已存在）

如果项目中已有 `启动后端.bat` 和 `启动前端.bat`：

1. **先启动数据库和 Redis**：
   ```bash
   docker-compose up -d postgres redis
   ```

2. **运行数据库迁移**：
   ```bash
   docker-compose run --rm backend python -m alembic upgrade head
   ```

3. **双击运行 `启动后端.bat`**（会启动后端服务）

4. **双击运行 `启动前端.bat`**（会启动前端服务）

### 第五步：访问应用

启动成功后，在浏览器中访问：

- **前端应用**：http://localhost:3000
- **后端 API 文档**：http://localhost:8000/api/v1/docs
- **后端健康检查**：http://localhost:8000/health

### 第六步：停止服务

**停止所有服务**：

```bash
docker-compose down
```

**停止并删除数据卷**（注意：会删除数据库数据）：

```bash
docker-compose down -v
```

---

## 🔧 方案2：直接运行（原生 Windows）

### 前置要求

需要安装以下软件：

1. **Python 3.9+**
   - 下载：https://www.python.org/downloads/
   - 安装时勾选 "Add Python to PATH"

2. **Node.js 16+**
   - 下载：https://nodejs.org/
   - 选择 LTS 版本

3. **PostgreSQL 13+**
   - 下载：https://www.postgresql.org/download/windows/
   - 记住安装时设置的 postgres 用户密码

4. **Redis for Windows**
   - 下载：https://github.com/microsoftarchive/redis/releases
   - 或使用 WSL2 中的 Redis

### 安装步骤

1. **启动 PostgreSQL 和 Redis**

   - PostgreSQL：通过 Windows 服务启动
   - Redis：运行 `redis-server.exe`

2. **配置后端**

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制 env.example 为 .env 并修改）
copy env.example .env
notepad .env

# 修改 DATABASE_URL（使用本地 PostgreSQL）
# DATABASE_URL=postgresql://postgres:你的密码@localhost:5432/aircraft_workcard
```

3. **运行数据库迁移**

```bash
# 在虚拟环境中执行
python -m alembic upgrade head
```

4. **启动后端**

```bash
# 使用批处理脚本
启动后端.bat

# 或直接运行
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **配置前端**

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 修改 API 地址（如果需要）
# 编辑 src/services/api.ts
# const API_BASE_URL = 'http://localhost:8000/api/v1'
```

6. **启动前端**

```bash
# 使用批处理脚本
启动前端.bat

# 或直接运行
npm run dev
```

---

## 🐧 方案3：WSL2 + Docker

### 前置要求

1. **启用 WSL2**
   ```powershell
   # 在 PowerShell（管理员）中执行
   wsl --install
   ```

2. **安装 Ubuntu**
   - 从 Microsoft Store 安装 Ubuntu
   - 设置用户名和密码

3. **在 WSL2 中安装 Docker**

   ```bash
   # 在 WSL2 Ubuntu 中执行
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

### 部署步骤

在 WSL2 Ubuntu 中，按照 Linux 部署步骤操作（参考 `腾讯云部署指南.md`）。

---

## 📝 试用版简化配置

### 简化版 docker-compose.yml（仅数据库和 Redis）

如果只想快速启动数据库和 Redis，可以使用以下简化配置：

```yaml
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: aircraft_workcard
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: Pk26605164
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

然后使用批处理脚本启动后端和前端。

---

## 🛠️ 常见问题排查

### 问题1：Docker Desktop 启动失败

**错误**：WSL 2 installation is incomplete

**解决方法**：
1. 确保已启用 WSL2
2. 更新 WSL2：`wsl --update`
3. 重启计算机

### 问题2：端口被占用

**错误**：port is already allocated

**解决方法**：
```bash
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 停止占用端口的进程
taskkill /PID <进程ID> /F
```

### 问题3：数据库连接失败

**检查**：
1. PostgreSQL 容器是否运行：`docker-compose ps postgres`
2. 端口是否正确：`netstat -ano | findstr :5432`
3. 密码是否正确：检查 `docker-compose.yml` 和 `.env` 文件

### 问题4：前端无法访问后端 API

**检查**：
1. 后端是否运行：访问 http://localhost:8000/health
2. API 地址配置：检查 `frontend/src/services/api.ts`
3. CORS 配置：检查 `backend/app/main.py` 中的 CORS 设置

### 问题5：内存不足

**Docker Desktop 设置**：
1. 打开 Docker Desktop
2. Settings → Resources
3. 调整 Memory 限制（建议至少 4GB）

---

## 📦 一键启动脚本（Windows）

创建 `一键启动.bat`：

```batch
@echo off
chcp 65001
cd /d %~dp0

echo ====================================
echo 飞机方案处理系统 - 一键启动
echo ====================================
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装或未启动
    echo 请先安装并启动 Docker Desktop
    pause
    exit /b 1
)

echo [1/4] 启动数据库和 Redis...
docker-compose up -d postgres redis

echo [2/4] 等待数据库启动...
timeout /t 10 /nobreak >nul

echo [3/4] 运行数据库迁移...
docker-compose run --rm backend python -m alembic upgrade head

echo [4/4] 启动所有服务...
docker-compose up -d --build

echo.
echo ====================================
echo 启动完成！
echo ====================================
echo 前端: http://localhost:3000
echo API文档: http://localhost:8000/api/v1/docs
echo.
echo 查看日志: docker-compose logs -f
echo 停止服务: docker-compose down
echo ====================================
echo.

pause
```

---

## 🎯 快速开始（推荐流程）

1. **安装 Docker Desktop**
   - 下载并安装 Docker Desktop
   - 启动 Docker Desktop

2. **获取代码**
   ```bash
   git clone https://gitee.com/bomingaviation_liugw_4779/workshop.git
   cd workshop
   ```

3. **配置环境变量**
   ```bash
   cd backend
   copy env.example .env
   notepad .env  # 修改 QWEN_API_KEY 等配置
   ```

4. **一键启动**
   ```bash
   cd ..
   docker-compose up -d --build
   docker-compose run --rm backend python -m alembic upgrade head
   ```

5. **访问应用**
   - 前端：http://localhost:3000
   - API文档：http://localhost:8000/api/v1/docs

---

## 📚 与生产环境的差异

| 项目 | 试用版（Windows） | 生产版（Linux） |
|------|------------------|---------------|
| 操作系统 | Windows 10/11 | Ubuntu 20.04+ |
| 容器化 | Docker Desktop | Docker + Docker Compose |
| 反向代理 | 无（直接访问） | Nginx |
| SSL | 无 | Let's Encrypt |
| 端口 | 直接暴露 | 仅本地 + Nginx 代理 |
| 开机自启 | 手动启动 | systemd 服务 |

---

## ✅ 部署检查清单

- [ ] Docker Desktop 已安装并运行
- [ ] 项目代码已获取
- [ ] 环境变量已配置（backend/.env）
- [ ] 数据库和 Redis 已启动
- [ ] 数据库迁移已执行
- [ ] 所有服务正常运行
- [ ] 前端可以访问
- [ ] 后端 API 可以访问

---

完成以上步骤后，你的试用版应该已经成功运行在 Windows 系统上了！

如有问题，请参考"常见问题排查"部分。




