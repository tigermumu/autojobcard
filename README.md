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
