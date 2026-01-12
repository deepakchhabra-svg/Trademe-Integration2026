# Multi-stage Dockerfile - API + UI Combined
# Stage 1: Build Next.js UI
FROM node:20-alpine AS ui-builder

WORKDIR /ui
COPY services/web/package*.json ./
RUN npm ci

COPY services/web/ ./
RUN npm run build && npm prune --production

# Stage 2: Python API + Serve UI
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Node.js for serving UI
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
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

# Copy built Next.js UI from builder stage
COPY --from=ui-builder /ui/.next ./services/web/.next
COPY --from=ui-builder /ui/public ./services/web/public
COPY --from=ui-builder /ui/package*.json ./services/web/
COPY --from=ui-builder /ui/node_modules ./services/web/node_modules
COPY services/web/next.config.ts ./services/web/

# Create data directory
RUN mkdir -p /app/data

# Expose ports (Railway will use PORT env var)
EXPOSE 8000 3000

# Health check (API)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Create startup script to run both API and UI
RUN echo '#!/bin/bash\n\
    set -e\n\
    # Start API in background\n\
    python -m uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000} &\n\
    API_PID=$!\n\
    # Start Next.js UI\n\
    cd /app/services/web && npm start -- -p ${UI_PORT:-3000} &\n\
    UI_PID=$!\n\
    # Wait for both processes\n\
    wait $API_PID $UI_PID\n\
    ' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
