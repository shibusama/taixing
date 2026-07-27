FROM python:3.13-slim

# 切换 apt 源为阿里云镜像（国内服务器加速）
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list

# Install Nginx + supervisor (to manage both Nginx and FastAPI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/nginx/sites-enabled/default

# Copy Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 切换 pip 源为清华镜像（国内服务器加速）
# Install all Python dependencies (backend + crawlers)
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy all project files
COPY . .

# Expose port
EXPOSE 8080

# Start supervisor (Nginx + FastAPI)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
