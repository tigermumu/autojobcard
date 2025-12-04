# U盘部署说明文档

## 📋 部署方案对比

### 方案一：SQLite 便携版（推荐）⭐
- ✅ **完全便携**：无需 Docker，无需安装数据库
- ✅ **体积小**：约 500MB-1GB
- ✅ **启动快**：无需启动 Docker 容器
- ⚠️ **性能限制**：SQLite 并发性能较低，适合单用户或小规模使用
- 📁 **使用脚本**：`启动后端-便携版.bat`

### 方案二：Docker + PostgreSQL（U盘版）
- ✅ **功能完整**：与生产环境一致
- ✅ **数据持久化**：数据存储在 U 盘
- ⚠️ **需要 Docker**：目标机器需安装 Docker Desktop（一次性，约5-10分钟）
- ⚠️ **性能较低**：U 盘读写速度限制 PostgreSQL 性能
- ⚠️ **体积较大**：Docker 镜像约 500MB+（首次下载）
- 📁 **使用脚本**：`启动后端-U盘版.bat`

**重要说明**：
- ❌ Docker Desktop **程序本身**不能运行在 U 盘（需要系统安装）
- ✅ Docker **数据**可以存储在 U 盘（已实现）
- ✅ 项目**配置**可以在 U 盘（已实现）
- ✅ 实现**"半便携"**：Docker 需安装，但数据和配置在 U 盘

### 方案三：Docker + PostgreSQL（本地数据卷）
- ✅ **性能最佳**：数据存储在本地磁盘
- ✅ **功能完整**：与生产环境一致
- ❌ **不够便携**：数据不在 U 盘，换电脑需重新初始化
- 📁 **使用脚本**：`启动后端.bat`

## 🚀 U盘部署步骤（Docker + PostgreSQL）

### 前置要求

1. **Docker Desktop**（需要系统安装，不能完全便携）
   - 下载：https://www.docker.com/products/docker-desktop
   - Windows 需要 WSL2 支持
   - 首次安装需要重启电脑
   - ⚠️ **注意**：Docker Desktop 必须安装在系统上，不能运行在 U 盘
   - ✅ **但**：项目数据和配置都在 U 盘，可以带走

2. **Python 3.9+**
   - 确保已安装 Python

3. **Node.js 16+**（前端需要）
   - 确保已安装 Node.js

### 部署步骤

1. **复制项目到 U 盘**
   ```
   将整个项目文件夹复制到 U 盘根目录
   例如：E:\demo3\
   ```

2. **首次运行**
   ```bash
   # 双击运行
   启动后端-U盘版.bat
   ```
   
   首次运行会：
   - 下载 Docker 镜像（PostgreSQL + Redis，约 300MB+）
   - 创建数据目录 `docker_data/`
   - 安装 Python 依赖
   - 运行数据库迁移

3. **启动前端**
   ```bash
   启动前端-便携版.bat
   ```

### 数据存储位置

使用 Docker + PostgreSQL 方案时，数据存储在：
```
U盘盘符:\demo3\docker_data\
├── postgres\    # PostgreSQL 数据文件
└── redis\       # Redis 数据文件
```

**重要提示**：
- 数据文件会随着使用增长，建议定期备份
- U 盘拔出前，建议先停止 Docker 容器
- 可以使用 `docker-compose -f docker-compose.usb.yml down` 停止服务

## ⚙️ 性能优化建议

### U盘选择
- ✅ 使用 **USB 3.0+** U 盘（读写速度 > 100MB/s）
- ✅ 使用 **SSD 移动硬盘**（性能最佳）
- ❌ 避免使用 USB 2.0 U 盘（速度太慢）

### PostgreSQL 性能优化
已配置的性能优化（在 `docker-compose.usb.yml` 中）：
```yaml
command: postgres -c fsync=off -c synchronous_commit=off
```
⚠️ **注意**：这会略微降低数据安全性，但大幅提升 U 盘性能

### 数据备份
建议定期备份 `docker_data` 目录：
```bash
# 停止容器
docker-compose -f docker-compose.usb.yml down

# 备份数据目录
xcopy docker_data backup\docker_data_%date:~0,4%%date:~5,2%%date:~8,2% /E /I
```

## 🔧 故障排查

### Docker 容器无法启动
```bash
# 检查 Docker 是否运行
docker ps

# 查看容器日志
docker-compose -f docker-compose.usb.yml logs postgres

# 检查端口占用
netstat -ano | findstr "5432"
netstat -ano | findstr "6379"
```

### 数据库连接失败
1. 检查容器是否运行：`docker ps`
2. 检查 `.env` 文件中的 `DATABASE_URL`
3. 确保使用：`postgresql://postgres:Pk26605164@localhost:5432/aircraft_workcard`

### U盘权限问题
- 确保 U 盘有写入权限
- 某些企业环境可能限制 U 盘写入，需要管理员权限

### 性能问题
- U 盘速度慢是正常现象
- 考虑使用 SSD 移动硬盘
- 或者使用 SQLite 版本（性能更好但功能受限）

## 📊 方案选择建议

| 使用场景 | 推荐方案 |
|---------|---------|
| 单用户演示/测试 | SQLite 便携版 |
| 多用户/生产环境 | Docker + PostgreSQL（本地数据卷） |
| 离线环境/多电脑切换 | Docker + PostgreSQL（U盘版） |
| 性能要求高 | Docker + PostgreSQL（本地数据卷） |
| 完全便携 | SQLite 便携版 |

## 🔄 数据迁移

### 从 SQLite 迁移到 PostgreSQL
```bash
# 1. 导出 SQLite 数据
# 2. 启动 PostgreSQL 版本
# 3. 导入数据（需要编写迁移脚本）
```

### 从 PostgreSQL 迁移到 SQLite
```bash
# 1. 导出 PostgreSQL 数据
pg_dump -h localhost -U postgres aircraft_workcard > backup.sql
# 2. 转换为 SQLite 格式（需要工具）
# 3. 导入 SQLite
```

## 📝 注意事项

1. **Docker 便携性限制**：
   - ❌ Docker Desktop **程序**不能运行在 U 盘（需要系统安装）
   - ✅ Docker **数据**可以存储在 U 盘（已实现）
   - ✅ 换电脑时：只需安装 Docker Desktop（首次），然后使用 U 盘数据
   - 📖 详细说明：查看 `Docker便携化说明.md`

2. **U盘盘符变化**：不同电脑 U 盘盘符可能不同，脚本会自动检测

3. **数据安全**：U 盘易丢失，建议定期备份重要数据

4. **网络要求**：首次运行需要网络下载 Docker 镜像

5. **Docker 版本**：确保 Docker Desktop 版本较新（支持 WSL2）

6. **完全便携方案**：如果不想安装 Docker，使用 SQLite 版本（`启动后端-便携版.bat`）

