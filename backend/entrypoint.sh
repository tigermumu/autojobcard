#!/bin/bash
set -e

# 创建数据目录
mkdir -p /app/data
mkdir -p /app/storage/import_logs

# 运行数据库迁移
cd /app && alembic upgrade head 2>/dev/null || true

# 启动应用
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
