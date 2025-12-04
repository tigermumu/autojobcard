# 飞机方案处理系统 - U盘便携版

## 📦 完全便携部署方案

本项目已配置为**完全便携版本**，可以完全依靠 U 盘独立运行，无需安装任何数据库或 Docker。

## ✨ 特性

- ✅ **完全便携**：插上 U 盘即可运行
- ✅ **无需 Docker**：不需要 Docker Desktop
- ✅ **无需数据库安装**：使用 SQLite，无需安装 PostgreSQL
- ✅ **数据在 U 盘**：所有数据存储在 U 盘，可随时带走
- ✅ **即插即用**：在任何 Windows 电脑上运行

## 📋 系统要求

### 必需（系统需安装）

1. **Python 3.9+**
   - 下载：https://www.python.org/downloads/
   - 安装时勾选 "Add Python to PATH"

2. **Node.js 16+**
   - 下载：https://nodejs.org/
   - 安装时自动添加到 PATH

### 可选（便携版）

如果不想在系统安装，可以使用便携版：
- Python 便携版：解压到 `U盘:\Tools\Python311`
- Node.js 便携版：解压到 `U盘:\Tools\nodejs`
- 然后修改 `配置环境.bat` 中的路径

## 🚀 快速开始

### 方法一：一键启动（推荐）

1. **双击运行**：`一键启动-U盘版.bat`
2. **等待启动**：首次运行需要安装依赖（5-10分钟）
3. **访问系统**：
   - 前端：http://localhost:3000
   - 后端 API：http://localhost:8000
   - API 文档：http://localhost:8000/api/v1/docs

### 方法二：分别启动

1. **启动后端**：双击 `启动后端-U盘便携版.bat`
2. **启动前端**：双击 `启动前端-U盘便携版.bat`

## 📁 目录结构

```
F:\autojobcard\
├── backend\              # 后端代码
│   ├── app\              # 应用代码
│   ├── venv\             # Python 虚拟环境（首次运行后创建）
│   ├── aircraft_workcard.db  # SQLite 数据库文件（运行后创建）
│   └── requirements.txt  # Python 依赖
├── frontend\             # 前端代码
│   ├── src\              # 源代码
│   ├── node_modules\    # Node.js 依赖（首次运行后创建）
│   └── package.json      # Node.js 依赖配置
├── 一键启动-U盘版.bat    # 一键启动脚本
├── 启动后端-U盘便携版.bat # 后端启动脚本
├── 启动前端-U盘便携版.bat # 前端启动脚本
└── 配置环境.bat          # 环境配置脚本
```

## 🔧 配置说明

### 数据库配置

使用 SQLite，数据库文件位置：
```
backend\aircraft_workcard.db
```

配置文件：`backend\.env`
```env
DATABASE_URL=sqlite:///./aircraft_workcard.db
QWEN_API_KEY=你的API密钥
```

### 首次运行

首次运行会自动：
1. ✅ 创建 Python 虚拟环境
2. ✅ 安装 Python 依赖
3. ✅ 安装 Node.js 依赖
4. ✅ 创建数据库并运行迁移
5. ✅ 启动服务

**注意**：首次运行需要网络连接下载依赖。

## 💾 数据管理

### 数据库文件

- **位置**：`backend\aircraft_workcard.db`
- **备份**：直接复制此文件即可备份
- **迁移**：将文件复制到其他 U 盘即可迁移数据

### 数据目录

- **上传文件**：`backend\uploads\`
- **导入日志**：`backend\storage\import_logs\`

## 🔄 更新项目

1. **备份数据**：复制 `backend\aircraft_workcard.db`
2. **更新代码**：替换项目文件
3. **运行迁移**：启动时会自动运行数据库迁移

## ⚠️ 注意事项

1. **U 盘性能**：
   - 建议使用 USB 3.0+ U 盘
   - 首次启动可能较慢（安装依赖）
   - 后续启动会快很多

2. **数据安全**：
   - U 盘易丢失，建议定期备份数据库文件
   - 重要数据建议同步到其他位置

3. **端口占用**：
   - 后端使用端口：8000
   - 前端使用端口：3000
   - 如果被占用，需要修改配置

4. **网络要求**：
   - 首次运行需要网络（下载依赖）
   - 后续运行可以离线（除了 API 调用）

## 🐛 故障排查

### Python 未找到

```
[错误] 未找到 Python
```

**解决**：
1. 检查是否安装 Python 3.9+
2. 检查是否添加到 PATH
3. 或使用便携版 Python（修改 `配置环境.bat`）

### Node.js 未找到

```
[错误] 未找到 Node.js
```

**解决**：
1. 检查是否安装 Node.js 16+
2. 检查是否添加到 PATH
3. 或使用便携版 Node.js（修改 `配置环境.bat`）

### 端口被占用

```
[错误] 端口 8000 被占用
```

**解决**：
1. 关闭占用端口的程序
2. 或修改 `启动后端-U盘便携版.bat` 中的端口号

### 依赖安装失败

**解决**：
1. 检查网络连接
2. 使用国内镜像源（脚本已配置）
3. 手动运行：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 📞 技术支持

如有问题，请检查：
1. Python 和 Node.js 版本是否正确
2. 网络连接是否正常
3. U 盘是否有足够空间（建议至少 2GB）
4. 查看错误日志

## 📝 版本信息

- **数据库**：SQLite（完全便携）
- **后端框架**：FastAPI
- **前端框架**：React + TypeScript
- **部署方式**：U盘便携版

---

**享受便携部署的便利！** 🎉






