FROM python:3.13-slim

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

# Install all Python dependencies (backend + crawlers)
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy all project files
COPY . .

# Expose port
EXPOSE 8080

# Start supervisor (Nginx + FastAPI)
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
