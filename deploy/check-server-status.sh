#!/bin/bash
# 检查服务器部署状态
# 用法: ./deploy/check-server-status.sh

SERVER_IP="45.152.66.70"
SERVER_USER="root"
SSH_PORT="9296"
REMOTE_DIR="/opt/autojobcard"

echo "=== 检查服务器部署状态 ==="
echo ""

# 使用 sshpass 如果可用
if command -v sshpass &>/dev/null; then
    SSHPASS="${SSHPASS:-}"
    if [ -z "$SSHPASS" ]; then
        echo "提示: 设置 SSHPASS 环境变量可免密执行，例如: export SSHPASS='您的密码'"
        SSH_CMD="ssh"
    else
        SSH_CMD="sshpass -e ssh"
    fi
else
    SSH_CMD="ssh"
fi

SSH_OPTS="-o StrictHostKeyChecking=no -p $SSH_PORT"

echo "1. 构建进度 (最后 20 行):"
$SSH_CMD $SSH_OPTS "$SERVER_USER@$SERVER_IP" "tail -20 /tmp/docker-build.log 2>/dev/null || echo '无构建日志'"
echo ""
echo "2. Docker 容器状态:"
$SSH_CMD $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && docker-compose ps 2>/dev/null || docker ps -a"
echo ""
echo "3. Docker 镜像:"
$SSH_CMD $SSH_OPTS "$SERVER_USER@$SERVER_IP" "docker images | grep -E 'autojobcard|REPOSITORY'"
echo ""
echo "4. 若构建完成，可执行以下命令启动服务:"
echo "   ssh -p $SSH_PORT $SERVER_USER@$SERVER_IP 'cd $REMOTE_DIR && docker-compose up -d'"
echo ""
echo "5. 访问地址: http://$SERVER_IP"
