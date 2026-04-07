#!/bin/bash
# 飞机方案处理系统 - 服务器部署脚本
# 用法: ./deploy/deploy.sh

set -e

# ============ 配置（请根据实际情况修改）============
SERVER_IP="45.152.66.70"
SERVER_USER="root"
SSH_PORT="9296"
REMOTE_DIR="/opt/autojobcard"
# ==================================================

# 通用 SSH 选项（不含端口）
SSH_BASE_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
# ssh 使用 -p 指定端口
SSH_OPTS="$SSH_BASE_OPTS -p $SSH_PORT"
# scp 使用 -P 指定端口（注意大小写）
SCP_OPTS="$SSH_BASE_OPTS -P $SSH_PORT"

echo "=========================================="
echo "  飞机方案处理系统 - 部署到服务器"
echo "  目标: $SERVER_USER@$SERVER_IP:$SSH_PORT"
echo "=========================================="

HAS_SSH=0
HAS_RSYN=0
HAS_SCP=0
HAS_TAR=0
command -v ssh >/dev/null 2>&1 && HAS_SSH=1
command -v rsync >/dev/null 2>&1 && HAS_RSYN=1
command -v scp >/dev/null 2>&1 && HAS_SCP=1
command -v tar >/dev/null 2>&1 && HAS_TAR=1

if [ "$HAS_SSH" -ne 1 ] || [ "$HAS_SCP" -ne 1 ]; then
  echo "[错误] 未找到 ssh 或 scp，请先安装。"
  exit 1
fi
if [ "$HAS_RSYN" -ne 1 ] && [ "$HAS_TAR" -ne 1 ]; then
  echo "[错误] 未找到 rsync 或 tar，请先安装其中之一。"
  exit 1
fi

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "[1/6] 检查服务器 SSH 连接..."
if ! ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "echo OK" &>/dev/null; then
    echo "[错误] 无法连接到服务器。请检查："
    echo "  - IP 地址: $SERVER_IP"
    echo "  - SSH 端口: $SSH_PORT"
    echo "  - 用户名: $SERVER_USER"
    echo "  - 如使用密码，请确保已配置 ssh-copy-id 或手动输入密码"
    exit 1
fi
echo "  连接成功"

echo ""
echo "[2/6] 在服务器上创建目录..."
ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "mkdir -p $REMOTE_DIR"

echo ""
echo "[3/6] 上传项目文件..."
if [ "$HAS_RSYN" -eq 1 ]; then
  # rsync 通过 -e 传入 ssh 命令，这里沿用 SSH_OPTS（包含 -p 端口）
  rsync -avz --progress -e "ssh $SSH_OPTS" \
    --exclude 'node_modules' \
    --exclude 'backend/venv' \
    --exclude 'backend/__pycache__' \
    --exclude 'backend/app/**/__pycache__' \
    --exclude 'backend/*.db' \
    --exclude '.git' \
    --exclude 'frontend/dist' \
    --exclude '.env' \
    "$PROJECT_ROOT/" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/"
else
  # 生成打包文件到源目录之外，避免被打包进归档导致 "file changed as we read it"
  if [ -d "/tmp" ]; then
    PKG="$(mktemp -u /tmp/autojobcard_deploy_XXXXXX.tgz)"
  else
    PKG="$PROJECT_ROOT/../autojobcard_deploy.tgz"
  fi
  echo "  使用 tar+scp 方式打包上传..."
  tar -czf "$PKG" \
    --exclude 'node_modules' \
    --exclude 'backend/venv' \
    --exclude 'backend/__pycache__' \
    --exclude 'backend/app/**/__pycache__' \
    --exclude 'backend/*.db' \
    --exclude '.git' \
    --exclude 'frontend/dist' \
    --exclude '.env' \
    --exclude 'autojobcard_deploy*.tgz' \
    -C "$PROJECT_ROOT" .
  # 这里必须使用 scp 的 -P 端口选项，不能直接复用带 -p 的 SSH_OPTS
  scp $SCP_OPTS "$PKG" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/.deploy_package.tgz"
  ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && tar -xzf .deploy_package.tgz && rm -f .deploy_package.tgz"
  rm -f "$PKG"
fi

# 上传 .env（如果存在）
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
  echo "  上传 .env 配置文件..."
  scp $SCP_OPTS "$PROJECT_ROOT/backend/.env" "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/backend/"
else
  echo "[警告] 未找到 backend/.env，请确保服务器上已有正确的 .env 配置"
fi

echo ""
echo "[4/6] 清理旧容器和镜像..."
ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && \
  if docker compose version >/dev/null 2>&1; then \
    echo '[远程] docker compose down + prune ...'; \
    docker compose down --remove-orphans || true; \
    docker image prune -af || true; \
    docker builder prune -af || true; \
  elif command -v docker-compose >/dev/null 2>&1; then \
    echo '[远程] docker-compose down + prune ...'; \
    docker-compose down --remove-orphans || true; \
    docker image prune -af || true; \
    docker builder prune -af || true; \
  else \
    echo '[远程错误] 未找到 docker compose 或 docker-compose，请先在服务器上安装 Docker Compose。'; \
    exit 1; \
  fi"

echo ""
echo "[5/6] 在服务器上构建并启动服务..."
ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && \
  if docker compose version >/dev/null 2>&1; then \
    echo '[远程] 使用 docker compose ...'; \
    docker compose up -d --build; \
  elif command -v docker-compose >/dev/null 2>&1; then \
    echo '[远程] 使用 docker-compose ...'; \
    docker-compose up -d --build; \
  else \
    echo '[远程错误] 未找到 docker compose 或 docker-compose，请先在服务器上安装 Docker Compose。'; \
    exit 1; \
  fi"

echo ""
echo "[6/6] 等待服务启动..."
sleep 5

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://$SERVER_IP"
echo "  API 文档: http://$SERVER_IP/api/v1/docs"
echo ""
echo "  常用命令:"
echo "    查看日志: ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP 'cd $REMOTE_DIR && docker compose logs -f'"
echo "    停止服务: ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP 'cd $REMOTE_DIR && docker compose down'"
echo "    重启服务: ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP 'cd $REMOTE_DIR && docker compose restart'"
echo ""
