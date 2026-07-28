#!/usr/bin/env bash
set -euo pipefail

# 基于脚本位置定位项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[deploy-build] 安装系统依赖（Nginx + Supervisor）..."

# 安装 Nginx 和 Supervisor
apt-get update
apt-get install -y --no-install-recommends nginx supervisor
rm -rf /var/lib/apt/lists/*
rm -f /etc/nginx/sites-enabled/default

echo "[deploy-build] 安装 Python 依赖..."

# 使用清华镜像源加速
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true
pip install --no-cache-dir -r backend/requirements.txt

echo "[deploy-build] 配置 Nginx..."

# 生成 Nginx 配置（监听 5000 端口）
cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 5000;
    server_name localhost;
    root /workspace/projects;
    index index.html;

    charset utf-8;

    # API 反向代理到 FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Static files
    location / {
        try_files $uri $uri/ =404;
    }

    # Cache data JSON for 5 minutes
    location /data/ {
        expires 5m;
        add_header Cache-Control "public, max-age=300";
    }

    # CSS/JS immutably cached
    location ~* \.(css|js)$ {
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    # No cache for HTML (content updates frequently)
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-cache, must-revalidate";
    }
}
EOF

echo "[deploy-build] 配置 Supervisor..."

# 生成 Supervisor 配置
cat > /etc/supervisor/conf.d/supervisord.conf <<'EOF'
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0
user=root

[program:fastapi]
command=python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
directory=/workspace/projects
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

echo "[deploy-build] 依赖安装和配置完成"
