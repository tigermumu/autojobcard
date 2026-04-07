#!/bin/bash
# 在目标服务器上运行此脚本，安装 Docker 和 Docker Compose
# 用法: 先 scp 到服务器，再 ssh 执行
#   scp -P 9296 deploy/server-setup.sh root@45.152.66.70:/tmp/
#   ssh -p 9296 root@45.152.66.70 'bash /tmp/server-setup.sh'

set -e
echo "正在安装 Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
echo "Docker 安装完成: $(docker --version)"
echo "Docker Compose: $(docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo '未找到')"
