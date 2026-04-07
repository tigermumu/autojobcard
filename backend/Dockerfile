FROM python:3.9-slim

WORKDIR /app

# 配置 pip 使用清华大学镜像源（国内服务器加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（使用国内镜像源）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令：创建目录、补充依赖、运行迁移、启动服务
CMD mkdir -p /app/data /app/storage/import_logs && \
    pip install -q beautifulsoup4 && \
    (alembic upgrade head 2>/dev/null || true) && \
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
