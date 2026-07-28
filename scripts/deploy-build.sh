#!/usr/bin/env bash
set -euo pipefail

# 基于脚本位置定位项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[deploy-build] 安装 Python 依赖..."

# 使用清华镜像源加速
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true

# 先安装 pydantic-core（强制重新编译）
pip install --no-cache-dir --force-reinstall pydantic-core

# 安装其他依赖
pip install --no-cache-dir -r backend/requirements.txt

echo "[deploy-build] 依赖安装完成"
