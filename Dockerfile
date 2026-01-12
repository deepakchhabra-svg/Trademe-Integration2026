# Multi-stage build for API + Worker + Web UI

# ============================================
# Stage 1: Build Next.js Frontend
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY services/web/package*.json ./
RUN npm ci
COPY services/web/ ./
RUN npm run build

# ============================================
# Stage 2: Final Image with Python + Node + Nginx
# ============================================
FROM python:3.12-slim

WORKDIR /app

# Install Node.js, Chromium, Nginx, and Supervisor
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    chromium \
    chromium-driver \
    supervisor \
    nginx \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Environment Variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application code
COPY retail_os/ ./retail_os/
COPY services/api/ ./services/api/
COPY scripts/ ./scripts/
COPY imports/ ./imports/

# Copy built Next.js frontend
COPY --from=frontend-builder /frontend/.next ./services/web/.next
COPY --from=frontend-builder /frontend/node_modules ./services/web/node_modules
COPY --from=frontend-builder /frontend/package.json ./services/web/package.json
COPY --from=frontend-builder /frontend/public ./services/web/public

# Create data directory
RUN mkdir -p /app/data

# Nginx configuration - single port, routes to API and Web
RUN cat > /etc/nginx/sites-available/default << 'NGINXCONF'
server {
    listen 8080;
    
    # API routes
    location /health { proxy_pass http://127.0.0.1:8000; }
    location /metrics { proxy_pass http://127.0.0.1:8000; }
    location /suppliers { proxy_pass http://127.0.0.1:8000; }
    location /products { proxy_pass http://127.0.0.1:8000; }
    location /listings { proxy_pass http://127.0.0.1:8000; }
    location /orders { proxy_pass http://127.0.0.1:8000; }
    location /commands { proxy_pass http://127.0.0.1:8000; }
    location /vaults { proxy_pass http://127.0.0.1:8000; }
    location /ops { proxy_pass http://127.0.0.1:8000; }
    location /enrichment { proxy_pass http://127.0.0.1:8000; }
    location /trademe { proxy_pass http://127.0.0.1:8000; }
    location /validate { proxy_pass http://127.0.0.1:8000; }
    location /audit { proxy_pass http://127.0.0.1:8000; }
    location /docs { proxy_pass http://127.0.0.1:8000; }
    location /openapi.json { proxy_pass http://127.0.0.1:8000; }
    
    # Everything else goes to Next.js
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINXCONF

# Supervisor configuration
RUN mkdir -p /var/log/supervisor
RUN cat > /etc/supervisor/conf.d/services.conf << 'SUPCONF'
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:api]
command=python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:worker]
command=python retail_os/trademe/worker.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:web]
command=npm start
directory=/app/services/web
environment=PORT="3000",API_BASE_URL="http://127.0.0.1:8000",NEXT_PUBLIC_API_BASE_URL=""
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
SUPCONF

# Expose single port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s \
    CMD curl -f http://localhost:8080/health || exit 1

# Run supervisor (manages all services)
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
