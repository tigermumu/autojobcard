# 构型数据导入导出工具使用说明

## 概述

这套工具用于导出和导入构型数据表（configurations、index_data、index_files）以及相关的索引文件，方便在新部署的云服务器上快速恢复构型数据，省去手动编辑录入的过程。

## 工具组成

1. **export_configurations.py** - 导出脚本
2. **import_configurations.py** - 导入脚本
3. **verify_configurations.py** - 验证脚本

## 前置要求

### 1. PostgreSQL 客户端工具

确保已安装 PostgreSQL 客户端工具，并且 `pg_dump` 和 `psql` 命令在系统 PATH 中。

**Windows 用户：**
- 安装 PostgreSQL 时会自动安装客户端工具
- 确保 PostgreSQL 的 `bin` 目录在系统 PATH 中
- 默认路径：`C:\Program Files\PostgreSQL\<version>\bin`

**Linux/Mac 用户：**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# Mac
brew install postgresql
```

### 2. Python 环境

确保已安装项目所需的 Python 依赖：
```bash
cd backend
pip install -r requirements.txt
```

### 3. 数据库配置

确保 `.env` 文件中的 `DATABASE_URL` 配置正确。

## 使用方法

### Windows 用户（推荐）

#### 方法1：使用批处理文件（最简单）

1. **导出数据**
   - 双击运行 `导出构型数据.bat`
   - 导出文件将保存在 `backend/exports/configurations_YYYYMMDD_HHMMSS/` 目录

2. **导入数据**
   - 将导出目录复制到新服务器
   - 双击运行 `导入构型数据.bat`
   - 按提示确认操作

3. **验证数据**
   - 双击运行 `验证构型数据.bat`
   - 查看验证结果

#### 方法2：使用命令行

```bash
# 导出
cd backend
python scripts\export_configurations.py

# 导入
python scripts\import_configurations.py

# 验证
python scripts\verify_configurations.py
```

### Linux/Mac 用户

```bash
# 导出
cd backend
python scripts/export_configurations.py

# 导入
python scripts/import_configurations.py --export-dir /path/to/export/directory

# 验证
python scripts/verify_configurations.py
```

## 详细说明

### 1. 导出脚本 (export_configurations.py)

**功能：**
- 导出 `configurations` 表数据
- 导出 `index_files` 表数据
- 导出 `index_data` 表数据
- 打包 `uploads/index_files/` 目录下的所有文件

**输出：**
- `backend/exports/configurations_YYYYMMDD_HHMMSS/` 目录包含：
  - `configurations.sql` - 构型配置数据
  - `index_files.sql` - 索引文件记录
  - `index_data.sql` - 索引数据
  - `index_files_backup.tar.gz` - 索引文件压缩包
  - `export_info.txt` - 导出信息说明

**示例：**
```bash
python scripts/export_configurations.py
```

### 2. 导入脚本 (import_configurations.py)

**功能：**
- 按顺序导入数据库表（configurations → index_files → index_data）
- 重置数据库序列
- 解压并恢复索引文件
- 验证导入结果

**参数：**
- `--export-dir`: 指定导出目录路径（可选，默认使用最新的导出目录）
- `--skip-files`: 跳过文件导入
- `--skip-verify`: 跳过验证步骤

**示例：**
```bash
# 使用最新导出目录
python scripts/import_configurations.py

# 指定导出目录
python scripts/import_configurations.py --export-dir backend/exports/configurations_20240101_120000

# 跳过文件导入
python scripts/import_configurations.py --skip-files
```

**注意事项：**
- 导入前确保新服务器上已创建数据库并运行了迁移
- 导入时会提示确认，避免误操作
- 如果存在重复数据，会显示警告但继续执行

### 3. 验证脚本 (verify_configurations.py)

**功能：**
- 检查各表的记录数
- 验证外键关系完整性
- 检查数据分布情况
- 验证 field_mapping 字段格式
- 检查文件路径是否存在
- 检查数据质量（空值、重复数据等）

**示例：**
```bash
python scripts/verify_configurations.py
```

## 完整流程示例

### 在旧服务器上导出

```bash
# 1. 导出数据
cd backend
python scripts/export_configurations.py

# 2. 查看导出目录
# 输出：backend/exports/configurations_20240101_120000/
```

### 传输到新服务器

将整个导出目录复制到新服务器：
```bash
# 方式1：使用 scp（Linux/Mac）
scp -r backend/exports/configurations_20240101_120000 user@new-server:/path/to/backend/exports/

# 方式2：使用文件共享或FTP工具
# 将整个目录打包后传输
```

### 在新服务器上导入

```bash
# 1. 确保数据库已创建并运行迁移
cd backend
alembic upgrade head

# 2. 导入数据
python scripts/import_configurations.py --export-dir exports/configurations_20240101_120000

# 3. 验证数据
python scripts/verify_configurations.py
```

## 故障排除

### 1. pg_dump/psql 命令未找到

**错误：** `未找到 pg_dump 命令`

**解决：**
- Windows: 将 PostgreSQL bin 目录添加到系统 PATH
- Linux/Mac: 安装 postgresql-client 包

### 2. 数据库连接失败

**错误：** `连接数据库失败`

**解决：**
- 检查 `.env` 文件中的 `DATABASE_URL` 配置
- 确保数据库服务正在运行
- 检查网络连接和防火墙设置

### 3. 导入时外键约束错误

**错误：** `外键约束违反`

**解决：**
- 确保按顺序导入表（脚本已自动处理）
- 检查导出数据是否完整
- 如果仍有问题，可以手动调整导入顺序

### 4. 文件路径不存在

**警告：** `文件路径不存在`

**解决：**
- 检查 `uploads/index_files/` 目录权限
- 确保文件已正确解压
- 可以手动检查并修复文件路径

### 5. 序列重置失败

**警告：** `序列不存在`

**解决：**
- 这通常不是严重问题，序列会在下次插入时自动创建
- 可以手动创建序列（如果需要）

## 注意事项

1. **备份重要数据**：导入操作会修改数据库，建议先备份
2. **数据库版本兼容性**：确保新旧服务器的 PostgreSQL 版本兼容
3. **文件路径**：如果新旧服务器的文件系统路径不同，可能需要手动调整
4. **权限问题**：确保脚本有读写数据库和文件的权限
5. **ID 冲突**：如果新服务器已有数据，导入时可能会产生 ID 冲突，脚本会自动处理

## 最佳实践

1. **定期导出**：建议定期导出构型数据作为备份
2. **验证导入**：导入后务必运行验证脚本检查数据完整性
3. **测试环境**：先在测试环境验证导入流程，再在生产环境操作
4. **文档记录**：记录每次导出的时间和用途，便于追溯

## 技术支持

如遇到问题，请检查：
1. 脚本输出的错误信息
2. 数据库日志
3. 系统日志

或联系系统管理员。












