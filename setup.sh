#!/bin/bash
# ================================
# 钛星 一键部署脚本
# 用法: bash setup.sh
# ================================

set -e

echo "==== 1/4 安装 Docker（如已安装则跳过）===="
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker 安装完成，请重新登录后重新运行此脚本"
    exit 0
fi
echo "Docker 已安装 ✓"

echo ""
echo "==== 2/4 配置 Docker 国内镜像源（加速）===="
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
sudo systemctl restart docker
echo "镜像源配置完成 ✓"

echo ""
echo "==== 3/4 拉取代码 ===="
if [ -d taixing ]; then
    cd taixing && git pull
else
    git clone git@github.com:shibusama/taixing.git
    cd taixing
fi
echo "代码已拉取 ✓"

echo ""
echo "==== 4/4 构建并启动 ===="
docker compose up -d --build
echo "启动完成 ✓"

echo ""
echo "==================================="
echo "部署完成！"
echo "访问地址: http://$(hostname -I | awk '{print $1}'):8080"
echo "==================================="
