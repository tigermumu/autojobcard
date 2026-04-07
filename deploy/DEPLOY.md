# 飞机方案处理系统 - 服务器部署指南

## 服务器信息

- **IP 地址**: 45.152.66.70
- **SSH 端口**: 9296
- **用户名**: root

## 部署前准备

### 1. 本地环境

- 已安装 Docker
- 已安装 rsync（Mac/Linux 通常已自带）
- 可 SSH 连接到服务器

### 2. 配置 SSH 免密登录（推荐）

```bash
# 生成密钥（如已有可跳过）
ssh-keygen -t rsa -b 4096

# 复制公钥到服务器（端口 9296）
ssh-copy-id -p 9296 root@45.152.66.70
```

### 3. 服务器环境

部署脚本会在服务器上自动安装 Docker（如未安装）。若需手动安装：

```bash
# 以 root 身份 SSH 登录
ssh -p 9296 root@45.152.66.70

# 安装 Docker（Ubuntu/Debian）
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 4. 配置文件

确保 `backend/.env` 中存在以下关键配置：

```env
# 数据库（Docker 内使用 SQLite，无需修改）
DATABASE_URL=sqlite:///./aircraft_workcard.db

# Redis（Docker 内自动指向 redis 服务，无需修改）
REDIS_URL=redis://localhost:6379

# Qwen API（必填）
QWEN_API_KEY=你的API密钥
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 生产环境建议修改
SECRET_KEY=请替换为随机安全密钥
```

## 部署步骤

### 方式一：使用部署脚本（推荐）

```bash
# 在项目根目录执行
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

首次连接会提示输入服务器密码。

### 方式二：手动部署

```bash
# 1. 将项目上传到服务器
scp -P 9296 -r . root@45.152.66.70:/opt/autojobcard/

# 2. SSH 登录服务器
ssh -p 9296 root@45.152.66.70

# 3. 进入项目目录并启动
cd /opt/autojobcard
docker compose build --no-cache
docker compose up -d
```

## 访问地址

部署成功后：

| 服务       | 地址                      |
|------------|---------------------------|
| 前端界面   | http://45.152.66.70       |
| API 文档   | http://45.152.66.70/api/v1/docs |
| 健康检查   | http://45.152.66.70/health      |

## 常用运维命令

```bash
# 查看所有容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 仅查看后端日志
docker compose logs -f backend

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新部署（重新拉取代码后）
docker compose build --no-cache && docker compose up -d
```

## 防火墙配置

确保服务器防火墙开放 **80 端口**（HTTP）：

```bash
# Ubuntu/Debian (ufw)
ufw allow 80
ufw reload

# CentOS/RHEL (firewalld)
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --reload
```

## 数据持久化

以下数据通过 Docker Volume 持久化：

- `backend_data`: SQLite 数据库
- `backend_storage`: 导入日志等文件
- `redis_data`: Redis 数据

如需备份数据库：

```bash
docker compose exec backend cp /app/data/aircraft_workcard.db /app/storage/backup.db
# 然后从 host 复制
docker cp autojobcard-backend:/app/storage/backup.db ./
```

## 故障排查

### 无法访问页面

1. 检查容器是否运行：`docker compose ps`
2. 检查 80 端口：`netstat -tlnp | grep 80`
3. 检查防火墙是否开放 80 端口

### 后端报错 Redis 连接失败

确认 redis 容器已启动：`docker compose ps`，应看到 redis 在运行。

### 前端无法调用 API

检查 CORS 配置，确保 `BACKEND_CORS_ORIGINS` 包含 `http://45.152.66.70`。
