# Multi-stage Dockerfile with nginx reverse proxy
# Stage 1: Build Next.js UI
FROM node:20-alpine AS ui-builder

WORKDIR /ui
COPY services/web/package*.json ./
RUN npm ci

COPY services/web/ ./
RUN npm run build

# Stage 2: Final image with Python API + Node.js + nginx
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Node.js and nginx
RUN apt-get update && apt-get install -y \
    curl \
    nginx \
    supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Environment
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

# Copy built Next.js app
COPY --from=ui-builder /ui/.next/standalone ./ui-standalone
COPY --from=ui-builder /ui/.next/static ./ui-standalone/.next/static
COPY --from=ui-builder /ui/public ./ui-standalone/public
COPY --from=ui-builder /ui/package.json ./ui-standalone/

# Create data directory
RUN mkdir -p /app/data

# Create nginx config template
RUN echo 'server {\n\
    listen 8080;\n\
    server_name _;\n\
    \n\
    # Serve Next.js UI at root\n\
    location / {\n\
    proxy_pass http://localhost:3000;\n\
    proxy_http_version 1.1;\n\
    proxy_set_header Upgrade $http_upgrade;\n\
    proxy_set_header Connection "upgrade";\n\
    proxy_set_header Host $host;\n\
    proxy_cache_bypass $http_upgrade;\n\
    }\n\
    \n\
    # API endpoints\n\
    location /api {\n\
    proxy_pass http://localhost:8000;\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    location /docs {\n\
    proxy_pass http://localhost:8000/docs;\n\
    }\n\
    \n\
    location /openapi.json {\n\
    proxy_pass http://localhost:8000/openapi.json;\n\
    }\n\
    \n\
    location /health {\n\
    proxy_pass http://localhost:8000/health;\n\
    }\n\
    \n\
    location /metrics {\n\
    proxy_pass http://localhost:8000/metrics;\n\
    }\n\
    }\n\
    ' > /etc/nginx/sites-available/default

# Configure supervisor
RUN echo '[supervisord]\n\
    nodaemon=true\n\
    user=root\n\
    \n\
    [program:api]\n\
    command=python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000\n\
    directory=/app\n\
    autostart=true\n\
    autorestart=true\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n\
    \n\
    [program:ui]\n\
    command=node ui-standalone/server.js\n\
    directory=/app\n\
    autostart=true\n\
    autorestart=true\n\
    environment=PORT="3000"\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n\
    \n\
    [program:nginx]\n\
    command=nginx -g "daemon off;"\n\
    autostart=true\n\
    autorestart=true\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n\
    ' > /etc/supervisor/conf.d/supervisord.conf

# Expose port (Railway will set PORT env var, but we use 8080 internally)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8080/health || exit 1

# Start script to handle Railway's PORT variable
RUN echo '#!/bin/bash\n\
    set -e\n\
    # Railway provides PORT, but we use 8080 internally for nginx\n\
    # Update nginx to listen on Railway PORT if provided\n\
    if [ ! -z "$PORT" ]; then\n\
    sed -i "s/listen 8080;/listen $PORT;/" /etc/nginx/sites-available/default\n\
    fi\n\
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
    ' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
