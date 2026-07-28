#!/usr/bin/env bash
set -euo pipefail

# 基于脚本位置定位项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[deploy-run] 启动 Supervisor（管理 Nginx + FastAPI）..."

# 前台启动 Supervisor（保持进程存活）
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
