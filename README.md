<<<<<<< HEAD
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

=======
# 飞机方案处理系统

## 项目概述

本项目是一个智能化的飞机方案处理系统，通过引入Qwen大模型（LLM）技术对历史工卡数据进行高效清洗、分类，并实现用户提交的飞机缺陷清单与历史工卡数据的智能对比和匹配。

## 技术栈

### 后端
- **FastAPI** - 高性能Python Web框架
- **SQLAlchemy** - ORM框架
- **PostgreSQL** - 主数据库
- **Redis** - 缓存和任务队列
- **Celery** - 异步任务处理
- **Qwen API** - 大模型集成（阿里云通义千问）

### 前端
- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Ant Design** - UI组件库
- **React Query** - 数据状态管理
- **Vite** - 构建工具

## 项目结构

```
aircraft-workcard-system/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── migrations/         # 数据库迁移
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   └── types/          # TypeScript类型
│   └── package.json        # Node.js依赖
├── docker-compose.yml      # Docker编排
└── README.md              # 项目说明
```

## 核心功能模块

### 1. 历史工卡数据清洗与存储 (FR-DATA)
- 构型索引文件加载与选择
- 工卡数据分类选择
- AI辅助数据清洗和校验
- 清洗结果存储

### 2. 索引数据管理 (FR-INDEX)
- 9字段索引数据表管理
- 层级结构数据展示（主区域→主部件→一级子部件→二级子部件）
- 二级子部件高权重相似度匹配
- 批量导入和导出功能

### 3. 缺陷清单处理与工卡匹配 (FR-DEFECT)
- 缺陷清单提交与存储
- 核心工卡对比算法（支持索引数据增强匹配）
- 候选工卡清单推荐
- 用户选择与工卡录入交互
- 落选清单管理与导出

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Redis 6+
- Windows 10+ （建议使用批处理脚本）

### 安装步骤

#### Windows 用户（推荐）

**重要：首次运行前必须先启动数据库**

1. 启动数据库和Redis（必须）
```bash
docker-compose up -d postgres redis
```

验证数据库是否启动：
```bash
docker ps
```

应该看到 `demo3-postgres-1` 和 `demo3-redis-1` 容器正在运行。

2. 启动后端服务
双击运行 `启动后端.bat` 或在命令行执行：
```bash
启动后端.bat
```

3. 启动前端服务
双击运行 `启动前端.bat` 或在命令行执行：
```bash
启动前端.bat
```

#### Linux/Mac 用户

1. 启动数据库和Redis
```bash
docker-compose up -d postgres redis
```

2. 启动后端服务
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 启动前端服务
```bash
cd frontend
npm install
npm run dev
```

## API文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看自动生成的API文档。

## 索引数据表结构

系统新增了9字段索引数据表，用于增强相似度匹配算法：

| 字段名 | 类型 | 说明 | 权重 |
|--------|------|------|------|
| 主区域 | String | 飞机主要区域分类 | 10% |
| 主部件 | String | 主区域下的主要部件 | 15% |
| 一级子部件 | String | 主部件的一级子部件 | 20% |
| 二级子部件 | String | 一级子部件的二级子部件 | 35% |
| 方位 | String | 部件在飞机上的方位 | 5% |
| 缺陷主体 | String | 缺陷的具体主体 | 10% |
| 缺陷描述 | Text | 缺陷的详细描述 | 5% |
| 位置 | String | 具体位置信息 | - |
| 数量 | String | 缺陷数量 | - |

### 层级关系
- 主区域 → 主部件 → 一级子部件 → 二级子部件
- 二级子部件在相似度对比中具有最高权重（35%）
- 其他字段相互独立

## 许可证

MIT License
>>>>>>> 402c441e3fd253d1f69a17a4dd0efd6233d24c8b
