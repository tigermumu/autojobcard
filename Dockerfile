FROM node:18-alpine AS frontend-builder
WORKDIR /app
RUN npm config set registry https://registry.npmmirror.com
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci || npm install
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM python:3.9-slim
WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN apt-get update && apt-get install -y nginx gcc g++ && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir beautifulsoup4
COPY backend/ ./
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
COPY deploy/nginx.conf /tmp/nginx.conf
RUN sed 's|http://backend:8000|http://127.0.0.1:8000|g' /tmp/nginx.conf | sed 's|listen 80;|listen \\$PORT;|g' > /etc/nginx/conf.d/default.conf.template && rm /tmp/nginx.conf
RUN rm -f /etc/nginx/sites-enabled/default
ENV DATABASE_URL=sqlite:///./data/aircraft_workcard.db
EXPOSE 80
CMD ["sh","-c","mkdir -p /app/data /app/storage/import_logs /app/uploads && export PORT=${PORT:-80} && envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && (alembic upgrade head 2>/dev/null || true) && (uvicorn app.main:app --host 0.0.0.0 --port 8000 &) && nginx -g 'daemon off;'"]
