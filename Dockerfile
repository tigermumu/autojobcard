FROM python:3.9-slim

WORKDIR /app/backend

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD mkdir -p /app/backend/data /app/backend/storage/import_logs /app/backend/uploads && \
    pip install -q beautifulsoup4 && \
    (alembic upgrade head 2>/dev/null || true) && \
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
